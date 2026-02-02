from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Tuple
import math

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from .geo import build_distance_matrix_miles, miles_fp_to_miles
from .costs import CostModel


@dataclass
class Stop:
    location_id: str
    lat: float
    lng: float
    revenue: Decimal
    service_minutes: int


@dataclass
class OptimizeResultRouteStop:
    location_id: str
    order: int
    revenue: Decimal
    segment_miles: float
    segment_drive_minutes: int
    service_minutes: int


@dataclass
class OptimizeResultRoute:
    vehicle_index: int
    stops: List[OptimizeResultRouteStop]
    total_miles: float
    total_drive_minutes: int
    total_service_minutes: int
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal


def _drive_minutes_from_miles(miles: float, avg_speed_mph: float) -> int:
    if miles <= 0:
        return 0
    minutes = (miles / avg_speed_mph) * 60.0
    return int(math.ceil(minutes))


def solve_profit_vrp(
    depot: Tuple[float, float],
    stops: List[Stop],
    cost_model: CostModel,
    num_days: int,
    max_minutes_per_day: int = 8 * 60,
    time_limit_seconds: int = 15,
) -> List[OptimizeResultRoute]:
    """
    Prize-Collecting VRP:
      - Minimizes travel_cost + labor_cost + penalties for skipped stops (penalty = revenue)
      - Equivalent to maximizing (visited revenue - visited cost).
    """
    if num_days < 1:
        raise ValueError("num_days must be >= 1")

    # Node 0 is depot. Nodes 1..n are stops.
    coords = [depot] + [(s.lat, s.lng) for s in stops]
    dist_fp = build_distance_matrix_miles(coords)

    n_nodes = len(coords)
    n_vehicles = num_days
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    # ---- Cost model conversions ----
    # OR-Tools costs must be integers. We'll use:
    # travel_cost_cents = miles * cost_per_mile * 100
    cpm = float(cost_model.cost_per_mile())  # dollars per mile
    labor_per_min = float(cost_model.labor_cost_per_minute())  # dollars per minute
    avg_speed = float(cost_model.avg_speed_mph)

    def travel_cost_callback(from_index: int, to_index: int) -> int:
        a = manager.IndexToNode(from_index)
        b = manager.IndexToNode(to_index)
        miles = miles_fp_to_miles(dist_fp[a][b])

        # Travel cost only (labor handled via time dimension; we’ll add labor cost by converting time to cost using another dimension below)
        dollars = miles * cpm
        cents = int(round(dollars * 100))
        return cents

    travel_cost_cb = routing.RegisterTransitCallback(travel_cost_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_cost_cb)

    # ---- Time dimension (drive + service) ----
    # Transit time = drive_minutes(from->to) + service_minutes(at "to" node)
    service_minutes = [0] + [int(s.service_minutes) for s in stops]

    def time_callback(from_index: int, to_index: int) -> int:
        a = manager.IndexToNode(from_index)
        b = manager.IndexToNode(to_index)
        miles = miles_fp_to_miles(dist_fp[a][b])
        drive = _drive_minutes_from_miles(miles, avg_speed)
        return drive + service_minutes[b]

    time_cb = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_cb,
        30,  # slack
        max_minutes_per_day,
        True,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Optional: try to balance time between vehicles/days a bit
    time_dim.SetGlobalSpanCostCoefficient(10)

    # ---- Prize-collecting: allow skipping stops ----
    # Penalty is "lost revenue" in cents.
    # If a stop is skipped, we pay penalty = revenue (so solver wants to include profitable stops).
    for i, s in enumerate(stops, start=1):
        penalty_cents = int(round(float(s.revenue) * 100))
        routing.AddDisjunction([manager.NodeToIndex(i)], penalty_cents)

    # ---- Add labor cost via "Time" dimension cost ----
    # We can't directly maximize profit in OR-Tools, but we can convert labor minutes into cost.
    # This adds additional objective weight to total time.
    labor_cost_per_min_cents = int(round(labor_per_min * 100))
    time_dim.SetSpanCostCoefficient(labor_cost_per_min_cents)

    # ---- Search parameters ----
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.time_limit.FromSeconds(time_limit_seconds)
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return []

    results: List[OptimizeResultRoute] = []

    for vehicle_id in range(n_vehicles):
        index = routing.Start(vehicle_id)

        route_stops: List[OptimizeResultRouteStop] = []
        prev_node = manager.IndexToNode(index)

        total_miles = 0.0
        total_drive_minutes = 0
        total_service_minutes = 0
        total_revenue = Decimal("0.00")

        order = 0
        while not routing.IsEnd(index):
            next_index = solution.Value(routing.NextVar(index))
            node = manager.IndexToNode(next_index)

            # If node is 0 depot, that's end. Otherwise it's a stop.
            if node != 0:
                stop = stops[node - 1]
                seg_miles = miles_fp_to_miles(dist_fp[prev_node][node])
                seg_drive = _drive_minutes_from_miles(seg_miles, avg_speed)

                order += 1
                route_stops.append(
                    OptimizeResultRouteStop(
                        location_id=stop.location_id,
                        order=order,
                        revenue=stop.revenue,
                        segment_miles=seg_miles,
                        segment_drive_minutes=seg_drive,
                        service_minutes=stop.service_minutes,
                    )
                )

                total_miles += seg_miles
                total_drive_minutes += seg_drive
                total_service_minutes += stop.service_minutes
                total_revenue += stop.revenue

            prev_node = node
            index = next_index

        # Return to depot segment (last node -> depot)
        if prev_node != 0:
            seg_miles = miles_fp_to_miles(dist_fp[prev_node][0])
            seg_drive = _drive_minutes_from_miles(seg_miles, avg_speed)
            total_miles += seg_miles
            total_drive_minutes += seg_drive

        # Compute costs/profit
        travel_cost = Decimal(str(total_miles)) * cost_model.cost_per_mile()
        labor_cost = Decimal(str(total_drive_minutes + total_service_minutes)) * cost_model.labor_cost_per_minute()
        total_cost = travel_cost + labor_cost
        total_profit = total_revenue - total_cost

        results.append(
            OptimizeResultRoute(
                vehicle_index=vehicle_id,
                stops=route_stops,
                total_miles=round(total_miles, 3),
                total_drive_minutes=total_drive_minutes,
                total_service_minutes=total_service_minutes,
                total_revenue=total_revenue.quantize(Decimal("0.01")),
                total_cost=total_cost.quantize(Decimal("0.01")),
                total_profit=total_profit.quantize(Decimal("0.01")),
            )
        )

    # Sort routes by profit descending (optional)
    results.sort(key=lambda r: r.total_profit, reverse=True)
    return results

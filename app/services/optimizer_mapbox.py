from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Optional
import math

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.services.costs import CostModel
from app.services.mapbox_matrix import fetch_full_square_matrix_chunked, MatrixResult


@dataclass
class Stop:
    location_id: str
    lat: float
    lng: float
    revenue: Decimal
    service_minutes: int


@dataclass
class RouteStopOut:
    location_id: str
    order: int
    revenue: Decimal
    segment_miles: float
    segment_drive_minutes: int
    service_minutes: int


@dataclass
class RouteOut:
    vehicle_index: int
    stops: List[RouteStopOut]
    total_miles: float
    total_drive_minutes: int
    total_service_minutes: int
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal


def _meters_to_miles(m: float) -> float:
    return m / 1609.344


def _sec_to_min_ceil(s: float) -> int:
    return int(math.ceil(s / 60.0))


async def solve_profit_vrp_with_mapbox(
    depot: Tuple[float, float],
    stops: List[Stop],
    cost_model: CostModel,
    num_days: int,
    *,
    profile: str = "driving",
    max_minutes_per_day: int = 8 * 60,
    time_limit_seconds: int = 15,
    max_coords_per_request: int = 25,  # 10 if driving-traffic unless your account allows more. :contentReference[oaicite:9]{index=9}
) -> List[RouteOut]:
    """
    Profit VRP using Mapbox road-network matrix.

    Objective:
      minimize(travel_cost + labor_cost + penalties_for_skipped_stops)
    Where penalty_for_skipped_stop = revenue (in cents) => visits are chosen when profitable.
    """
    if num_days < 1:
        raise ValueError("num_days must be >= 1")

    coords = [depot] + [(s.lat, s.lng) for s in stops]
    matrix: MatrixResult = await fetch_full_square_matrix_chunked(
        coords,
        profile=profile,
        max_coords_per_request=max_coords_per_request,
        max_concurrent_requests=4,
    )

    # OR-Tools wants integer costs
    cpm = float(cost_model.cost_per_mile())
    labor_per_min = float(cost_model.labor_cost_per_minute())
    labor_per_min_cents = int(round(labor_per_min * 100))

    n_nodes = len(coords)
    n_vehicles = num_days
    depot_index = 0

    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, depot_index)
    routing = pywrapcp.RoutingModel(manager)

    # ---- Cost callback: travel cost in cents using Mapbox distance meters ----
    def travel_cost_cb(from_idx: int, to_idx: int) -> int:
        a = manager.IndexToNode(from_idx)
        b = manager.IndexToNode(to_idx)
        dist_m = matrix.distances[a][b] if matrix.distances else None
        if dist_m is None:
            # If Mapbox can't route, discourage heavily
            return 10**9
        miles = _meters_to_miles(float(dist_m))
        cents = int(round(miles * cpm * 100))
        return cents

    travel_cb_i = routing.RegisterTransitCallback(travel_cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(travel_cb_i)

    # ---- Time callback: drive minutes from Mapbox duration + service time at destination ----
    service_minutes = [0] + [int(s.service_minutes) for s in stops]

    def time_cb(from_idx: int, to_idx: int) -> int:
        a = manager.IndexToNode(from_idx)
        b = manager.IndexToNode(to_idx)
        dur_s = matrix.durations[a][b] if matrix.durations else None
        if dur_s is None:
            return 10**9
        drive_min = _sec_to_min_ceil(float(dur_s))
        return drive_min + service_minutes[b]

    time_cb_i = routing.RegisterTransitCallback(time_cb)
    routing.AddDimension(
        time_cb_i,
        30,
        max_minutes_per_day,
        True,
        "Time",
    )
    time_dim = routing.GetDimensionOrDie("Time")
    # Convert time usage into cost (labor) by penalizing time span
    time_dim.SetSpanCostCoefficient(labor_per_min_cents)

    # ---- Prize-collecting (skip unprofitable stops): penalty = revenue ----
    for node, stop in enumerate(stops, start=1):
        penalty_cents = int(round(float(stop.revenue) * 100))
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty_cents)

    # ---- Search parameters ----
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.time_limit.FromSeconds(time_limit_seconds)
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH

    # OR-Tools is CPU heavy; this function is async but still CPU inside routing.Solve.
    # Call it via to_thread from your worker to keep the event loop healthy.
    solution = routing.SolveWithParameters(params)
    if not solution:
        return []

    results: List[RouteOut] = []

    for v in range(n_vehicles):
        idx = routing.Start(v)
        prev_node = manager.IndexToNode(idx)

        order = 0
        total_miles = 0.0
        total_drive_minutes = 0
        total_service_minutes = 0
        total_revenue = Decimal("0.00")
        out_stops: List[RouteStopOut] = []

        while not routing.IsEnd(idx):
            nxt = solution.Value(routing.NextVar(idx))
            node = manager.IndexToNode(nxt)

            if node != 0:
                stop = stops[node - 1]
                dist_m = matrix.distances[prev_node][node]
                dur_s = matrix.durations[prev_node][node]

                seg_miles = _meters_to_miles(float(dist_m)) if dist_m is not None else 0.0
                seg_drive = _sec_to_min_ceil(float(dur_s)) if dur_s is not None else 0

                order += 1
                out_stops.append(
                    RouteStopOut(
                        location_id=stop.location_id,
                        order=order,
                        revenue=stop.revenue,
                        segment_miles=round(seg_miles, 3),
                        segment_drive_minutes=seg_drive,
                        service_minutes=stop.service_minutes,
                    )
                )

                total_miles += seg_miles
                total_drive_minutes += seg_drive
                total_service_minutes += stop.service_minutes
                total_revenue += stop.revenue

            prev_node = node
            idx = nxt

        # last leg back to depot
        if prev_node != 0:
            dist_m = matrix.distances[prev_node][0]
            dur_s = matrix.durations[prev_node][0]
            total_miles += _meters_to_miles(float(dist_m)) if dist_m is not None else 0.0
            total_drive_minutes += _sec_to_min_ceil(float(dur_s)) if dur_s is not None else 0

        travel_cost = Decimal(str(total_miles)) * cost_model.cost_per_mile()
        labor_cost = Decimal(str(total_drive_minutes + total_service_minutes)) * cost_model.labor_cost_per_minute()
        total_cost = travel_cost + labor_cost
        total_profit = total_revenue - total_cost

        results.append(
            RouteOut(
                vehicle_index=v,
                stops=out_stops,
                total_miles=round(total_miles, 3),
                total_drive_minutes=total_drive_minutes,
                total_service_minutes=total_service_minutes,
                total_revenue=total_revenue.quantize(Decimal("0.01")),
                total_cost=total_cost.quantize(Decimal("0.01")),
                total_profit=total_profit.quantize(Decimal("0.01")),
            )
        )

    results.sort(key=lambda r: r.total_profit, reverse=True)
    return results

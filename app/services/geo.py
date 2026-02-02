from __future__ import annotations
from math import radians, sin, cos, sqrt, atan2
from decimal import Decimal
from typing import List, Tuple


def haversine_miles(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    # Earth radius (miles)
    R = 3958.7613
    lat1, lon1 = a
    lat2, lon2 = b

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    rlat1 = radians(lat1)
    rlat2 = radians(lat2)

    h = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
    return 2 * R * atan2(sqrt(h), sqrt(1 - h))


def build_distance_matrix_miles(coords: List[Tuple[float, float]]) -> List[List[int]]:
    """
    Returns integer miles * 1000 (fixed point) for OR-Tools cost stability.
    """
    n = len(coords)
    mat = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                mat[i][j] = 0
            else:
                miles = haversine_miles(coords[i], coords[j])
                mat[i][j] = int(miles * 1000)  # fixed point
    return mat


def miles_fp_to_miles(miles_fp: int) -> float:
    return miles_fp / 1000.0

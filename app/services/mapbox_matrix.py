from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import httpx

from app.config import MAPBOX_ACCESS_TOKEN, MAPBOX_BASE_URL, MAPBOX_MATRIX_PROFILE


@dataclass(frozen=True)
class MatrixResult:
    # durations in seconds, distances in meters
    durations: List[List[Optional[float]]]
    distances: List[List[Optional[float]]]


class MapboxMatrixError(RuntimeError):
    pass


def _coord_str(coords: List[Tuple[float, float]]) -> str:
    # Mapbox expects "lon,lat;lon,lat;..."
    return ";".join([f"{lng:.6f},{lat:.6f}" for (lat, lng) in coords])


async def fetch_matrix(
    coords: List[Tuple[float, float]],
    profile: str = MAPBOX_MATRIX_PROFILE,
    *,
    annotations: str = "duration,distance",
    sources: Optional[List[int]] = None,
    destinations: Optional[List[int]] = None,
    timeout_s: float = 30.0,
    client: Optional[httpx.AsyncClient] = None,
) -> MatrixResult:
    """
    Calls Mapbox Matrix API (v1).
    - Returns durations (seconds) and distances (meters).
    - No geometry returned. :contentReference[oaicite:4]{index=4}

    coords: list of (lat, lng)
    sources/destinations: indices into coords (optional)
    """
    if not MAPBOX_ACCESS_TOKEN:
        raise MapboxMatrixError("MAPBOX_ACCESS_TOKEN is missing")

    owned_client = client is None
    if owned_client:
        client = httpx.AsyncClient(base_url=MAPBOX_BASE_URL, timeout=timeout_s)

    try:
        path = f"/directions-matrix/v1/mapbox/{profile}/{_coord_str(coords)}"
        params: Dict[str, Any] = {
            "access_token": MAPBOX_ACCESS_TOKEN,
            "annotations": annotations,  # duration,distance
        }
        if sources is not None:
            params["sources"] = ";".join(map(str, sources))
        if destinations is not None:
            params["destinations"] = ";".join(map(str, destinations))

        r = await client.get(path, params=params)
        if r.status_code != 200:
            raise MapboxMatrixError(f"Mapbox Matrix API error {r.status_code}: {r.text}")

        data = r.json()
        # docs: durations in seconds, distances in meters :contentReference[oaicite:5]{index=5}
        return MatrixResult(
            durations=data.get("durations"),
            distances=data.get("distances"),
        )
    finally:
        if owned_client:
            await client.aclose()


# ---------- Chunking helpers (for > 25 coords) ----------

async def fetch_full_square_matrix_chunked(
    coords: List[Tuple[float, float]],
    profile: str = MAPBOX_MATRIX_PROFILE,
    *,
    max_coords_per_request: int = 25,
    # Mapbox publishes per-minute limits; keep concurrency modest. :contentReference[oaicite:6]{index=6}
    max_concurrent_requests: int = 4,
) -> MatrixResult:
    """
    Build an NxN matrix even when N > max_coords_per_request by chunking.

    Strategy:
      - chunk destinations into blocks
      - for each origin-block, request matrix for that block vs destination-block using sources/destinations
      - stitch back into full NxN

    This keeps each API call <= max_coords_per_request by using a “union” coords list for the call.
    """
    n = len(coords)
    if n == 0:
        return MatrixResult(durations=[], distances=[])

    # Initialize full matrices
    durations: List[List[Optional[float]]] = [[None] * n for _ in range(n)]
    distances: List[List[Optional[float]]] = [[None] * n for _ in range(n)]

    sem = asyncio.Semaphore(max_concurrent_requests)

    async with httpx.AsyncClient(base_url=MAPBOX_BASE_URL, timeout=60.0) as client:

        async def _do_block(o_start: int, o_end: int, d_start: int, d_end: int):
            # Build a request with coords = origins_block + destinations_block (dedup if overlap)
            # Then sources are 0..(o_len-1), destinations are (o_len)..(o_len+d_len-1)
            async with sem:
                origins_block = coords[o_start:o_end]
                dest_block = coords[d_start:d_end]
                call_coords = origins_block + dest_block

                # Guard: must be <= max_coords_per_request
                if len(call_coords) > max_coords_per_request:
                    raise MapboxMatrixError(
                        f"Chunk too large: {len(call_coords)} coords > {max_coords_per_request}. "
                        f"Reduce block sizes."
                    )

                sources = list(range(0, len(origins_block)))
                destinations_idx = list(range(len(origins_block), len(origins_block) + len(dest_block)))

                res = await fetch_matrix(
                    call_coords,
                    profile=profile,
                    annotations="duration,distance",
                    sources=sources,
                    destinations=destinations_idx,
                    client=client,
                )

                # Stitch: res matrices are [origins_block][dest_block]
                for i, oi in enumerate(range(o_start, o_end)):
                    for j, dj in enumerate(range(d_start, d_end)):
                        durations[oi][dj] = res.durations[i][j] if res.durations else None
                        distances[oi][dj] = res.distances[i][j] if res.distances else None

        # Choose block size so origins_block + dest_block <= max_coords_per_request
        # simplest: split into half-ish blocks
        block = max(1, max_coords_per_request // 2)

        tasks = []
        for o in range(0, n, block):
            o_end = min(n, o + block)
            for d in range(0, n, block):
                d_end = min(n, d + block)
                tasks.append(_do_block(o, o_end, d, d_end))

        await asyncio.gather(*tasks)

    return MatrixResult(durations=durations, distances=distances)

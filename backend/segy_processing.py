import os
from typing import Dict, Any, List
import numpy as np

try:
    import segyio  # type: ignore
except ImportError:
    segyio = None

from fastapi import UploadFile


def save_and_parse_segy(file: UploadFile, data_dir: str) -> str:
    """
    Save uploaded SEGY to data_dir as latest.sgy and return path.
    """
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    saved_path = os.path.join(data_dir, "latest.sgy")
    with open(saved_path, "wb") as f:
        f.write(file.file.read())
    return saved_path


def get_segy_metadata(path: str) -> Dict[str, Any]:
    """
    Return basic SEGY metadata (inline/crossline count if possible).
    """
    if segyio is None:
        return {
            "library": "segyio not installed",
            "path": path,
            "message": "Install segyio in backend/requirements.txt environment to parse SEGY.",
        }

    meta: Dict[str, Any] = {"path": path}
    with segyio.open(path, "r", ignore_geometry=False) as segy:
        # Inline and crossline indexing can vary by survey. Attempt standard keys.
        ilines = segy.ilines if hasattr(segy, "ilines") else []
        xlines = segy.xlines if hasattr(segy, "xlines") else []
        meta["num_traces"] = segy.tracecount
        meta["num_inlines"] = len(ilines)
        meta["num_crosslines"] = len(xlines)
        meta["ilines"] = list(map(int, ilines))[:50]
        meta["xlines"] = list(map(int, xlines))[:50]
        meta["samples_per_trace"] = segy.samples.size
        meta["sample_rate_us"] = int(segy.samples[1] - segy.samples[0]) if segy.samples.size > 1 else None
    return meta


def normalize(arr: np.ndarray) -> np.ndarray:
    """
    Normalize amplitude to [0,1] with robust scaling.
    """
    if arr.size == 0:
        return arr
    p1, p99 = np.percentile(arr, [1, 99])
    span = (p99 - p1) if (p99 - p1) != 0 else 1.0
    arr = np.clip(arr, p1, p99)
    return (arr - p1) / span


def get_inline_slice(path: str, iline_id: int) -> List[List[float]]:
    """
    Return normalized inline slice as 2D list.
    """
    if segyio is None:
        raise RuntimeError("segyio not installed")

    with segyio.open(path, "r", ignore_geometry=False) as segy:
        if not hasattr(segy, "iline"):
            raise RuntimeError("SEGY has no inline accessor")
        arr = segy.iline[iline_id]  # shape: [num_samples, num_crosslines]
        arr = normalize(arr.astype(np.float32))
        return arr.tolist()


def get_crossline_slice(path: str, xline_id: int) -> List[List[float]]:
    """
    Return normalized crossline slice as 2D list.
    """
    if segyio is None:
        raise RuntimeError("segyio not installed")

    with segyio.open(path, "r", ignore_geometry=False) as segy:
        if not hasattr(segy, "xline"):
            raise RuntimeError("SEGY has no crossline accessor")
        arr = segy.xline[xline_id]  # shape: [num_samples, num_inlines]
        arr = normalize(arr.astype(np.float32))
        return arr.tolist()
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class OrtConfig:
    model_path: str
    providers: list[str] | None = None


class Dinov2Onnx:
    """ONNX Runtime backend for DINOv2 embeddings.

    Expects input tensor shaped (1,3,224,224) float32, already normalized.
    Returns embedding shaped (1, D) float32.

    This module is optional; if onnxruntime isn't installed or model is missing,
    caller should catch exceptions and fallback to CPU/numpy backend.
    """

    def __init__(self, cfg: OrtConfig):
        try:
            import onnxruntime as ort  # type: ignore
        except Exception as e:
            raise RuntimeError(f"onnxruntime not available: {e}")

        so = ort.SessionOptions()
        # Favor lower latency in most cases
        so.intra_op_num_threads = 0
        so.inter_op_num_threads = 0

        providers = cfg.providers or []
        if not providers:
            # Try best-effort providers in order (Windows): DML -> CUDA -> CPU
            # Note: provider must be installed via the corresponding package.
            providers = [
                "DmlExecutionProvider",
                "CUDAExecutionProvider",
                "CPUExecutionProvider",
            ]

        self.session = ort.InferenceSession(cfg.model_path, sess_options=so, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    @staticmethod
    def _as_f32(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> np.ndarray:
        x = self._as_f32(x)
        out = self.session.run([self.output_name], {self.input_name: x})[0]
        return self._as_f32(out)


def parse_providers(s: str | None) -> list[str] | None:
    if not s:
        return None
    # comma-separated providers
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts or None

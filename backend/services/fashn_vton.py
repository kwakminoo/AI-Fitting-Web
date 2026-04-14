"""
FASHN VTON v1.5 로컬 추론: 사전학습 가중치로 사람 + 의류 이미지 → 합성 PNG (data URL).
https://github.com/fashn-AI/fashn-vton-1.5
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from fashn_vton import TryOnPipeline

logger = logging.getLogger(__name__)

_pipeline: TryOnPipeline | None = None
_load_error: str | None = None
_weights_dir_resolved: Path | None = None

GarmentPhotoType = Literal["model", "flat-lay"]
FashnCategory = Literal["tops", "bottoms", "one-pieces"]


def _default_weights_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "weights"


def weights_dir_path() -> Path:
    raw = (os.environ.get("FASHN_WEIGHTS_DIR") or "").strip()
    return Path(raw).resolve() if raw else _default_weights_dir()


def resolve_fashn_category() -> FashnCategory:
    direct = (os.environ.get("FASHN_CATEGORY") or "").strip().lower()
    if direct in ("tops", "bottoms", "one-pieces"):
        return direct  # type: ignore[return-value]
    legacy = (os.environ.get("REPLICATE_CATEGORY") or "upper_body").strip().lower()
    legacy_map: dict[str, FashnCategory] = {
        "upper_body": "tops",
        "lower_body": "bottoms",
        "dresses": "one-pieces",
    }
    return legacy_map.get(legacy, "tops")


def _resolve_garment_photo_type() -> GarmentPhotoType:
    v = (os.environ.get("FASHN_GARMENT_PHOTO_TYPE") or "model").strip().lower()
    if v in ("model", "flat-lay"):
        return v  # type: ignore[return-value]
    return "model"


def startup_load_pipeline() -> None:
    """앱 기동 시 한 번 호출: TryOnPipeline 로드."""
    global _pipeline, _load_error, _weights_dir_resolved
    _load_error = None
    _weights_dir_resolved = weights_dir_path()
    wd = str(_weights_dir_resolved)
    device = (os.environ.get("FASHN_DEVICE") or "").strip() or None
    try:
        from fashn_vton import TryOnPipeline as _TryOnPipeline

        logger.info("FASHN: loading TryOnPipeline from weights_dir=%s", wd)
        _pipeline = _TryOnPipeline(weights_dir=wd, device=device)
        logger.info("FASHN: TryOnPipeline ready (device=%s)", _pipeline.device)
    except Exception as e:  # noqa: BLE001 — 기동 실패 시에도 서버는 뜨게 함
        _pipeline = None
        _load_error = str(e)
        logger.exception("FASHN: pipeline load failed: %s", e)


def fashn_health() -> dict[str, Any]:
    return {
        "fashn_ready": _pipeline is not None,
        "fashn_load_error": _load_error,
        "fashn_weights_dir": str(_weights_dir_resolved or weights_dir_path()),
    }


def _get_pipeline() -> TryOnPipeline:
    if _pipeline is None:
        hint = (
            f"가중치 경로: {weights_dir_path()}. "
            "프로젝트 루트에서 scripts/setup-fashn-weights.sh 를 실행하거나 "
            "FASHN_WEIGHTS_DIR 을 설정하세요."
        )
        msg = _load_error or "FASHN 파이프라인이 로드되지 않았습니다."
        raise RuntimeError(f"{msg} {hint}")
    return _pipeline


def _run_inference_sync(user_bytes: bytes, cloth_bytes: bytes) -> bytes:
    from PIL import Image

    pipeline = _get_pipeline()
    person = Image.open(io.BytesIO(user_bytes)).convert("RGB")
    garment = Image.open(io.BytesIO(cloth_bytes)).convert("RGB")
    category = resolve_fashn_category()
    garment_photo_type = _resolve_garment_photo_type()
    num_timesteps = int(os.environ.get("FASHN_NUM_TIMESTEPS", "30"))
    guidance_scale = float(os.environ.get("FASHN_GUIDANCE_SCALE", "1.5"))
    seed = int(os.environ.get("FASHN_SEED", "42"))

    out = pipeline(
        person,
        garment,
        category=category,
        garment_photo_type=garment_photo_type,
        num_timesteps=num_timesteps,
        guidance_scale=guidance_scale,
        seed=seed,
    )
    buf = io.BytesIO()
    out.images[0].save(buf, format="PNG")
    return buf.getvalue()


async def run_fashn_try_on(user_bytes: bytes, cloth_bytes: bytes) -> str:
    """합성 PNG를 data:image/png;base64,... URL 형태로 반환 (프론트 호환)."""
    png = await asyncio.to_thread(_run_inference_sync, user_bytes, cloth_bytes)
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"

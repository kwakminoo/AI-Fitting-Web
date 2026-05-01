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
from dataclasses import dataclass
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
SpeedPreset = Literal["fast", "default", "slow"]

# 실험(T1~T6 × 3×3) 후 확정: fast=T2, default=T3, slow=T5 — docs/experiments/EXPERIMENT_REPORT.md
SPEED_PRESET_STEPS_GUIDANCE: dict[SpeedPreset, tuple[int, float]] = {
    "fast": (22, 1.35),
    "default": (30, 1.50),
    "slow": (40, 1.80),
}

# T1~T6 실험용 (run_matrix 등)
TRIAL_PRESETS: list[tuple[str, int, float]] = [
    ("T1", 18, 1.20),
    ("T2", 22, 1.35),
    ("T3", 30, 1.50),
    ("T4", 34, 1.65),
    ("T5", 40, 1.80),
    ("T6", 46, 2.00),
]


@dataclass(frozen=True)
class TryOnParams:
    """요청 단위 FASHN 추론 파라미터."""

    category: FashnCategory
    garment_photo_type: GarmentPhotoType
    num_timesteps: int
    guidance_scale: float
    seed: int


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


def resolve_speed_preset(preset: str) -> tuple[int, float]:
    """빠름/기본/느림 → (num_timesteps, guidance_scale)."""
    key = preset.strip().lower()
    if key in SPEED_PRESET_STEPS_GUIDANCE:
        return SPEED_PRESET_STEPS_GUIDANCE[key]  # type: ignore[index]
    return SPEED_PRESET_STEPS_GUIDANCE["default"]


def default_try_on_params_from_env() -> TryOnParams:
    """환경 변수 기반 기본 파라미터(레거시 호환)."""
    return TryOnParams(
        category=resolve_fashn_category(),
        garment_photo_type=_resolve_garment_photo_type(),
        num_timesteps=int(os.environ.get("FASHN_NUM_TIMESTEPS", "30")),
        guidance_scale=float(os.environ.get("FASHN_GUIDANCE_SCALE", "1.5")),
        seed=int(os.environ.get("FASHN_SEED", "42")),
    )


def try_on_params_for_request(
    *,
    category: FashnCategory,
    speed_preset: SpeedPreset,
    garment_photo_type: GarmentPhotoType | None = None,
    seed: int | None = None,
) -> TryOnParams:
    steps, guidance = resolve_speed_preset(speed_preset)
    gpt = garment_photo_type if garment_photo_type is not None else _resolve_garment_photo_type()
    s = seed if seed is not None else int(os.environ.get("FASHN_SEED", "42"))
    return TryOnParams(
        category=category,
        garment_photo_type=gpt,
        num_timesteps=steps,
        guidance_scale=guidance,
        seed=s,
    )


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


def run_fashn_inference_sync(user_bytes: bytes, cloth_bytes: bytes, params: TryOnParams) -> bytes:
    """동기: 사람·의류 바이트 → 합성 PNG 바이트."""
    from PIL import Image

    pipeline = _get_pipeline()
    person = Image.open(io.BytesIO(user_bytes)).convert("RGB")
    garment = Image.open(io.BytesIO(cloth_bytes)).convert("RGB")

    out = pipeline(
        person,
        garment,
        category=params.category,
        garment_photo_type=params.garment_photo_type,
        num_timesteps=params.num_timesteps,
        guidance_scale=params.guidance_scale,
        seed=params.seed,
    )
    buf = io.BytesIO()
    out.images[0].save(buf, format="PNG")
    return buf.getvalue()


def png_bytes_to_data_url(png: bytes) -> str:
    b64 = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def run_fashn_try_on_bytes(
    user_bytes: bytes,
    cloth_bytes: bytes,
    params: TryOnParams | None = None,
) -> bytes:
    """비동기 스레드에서 PNG 바이트 반환."""
    p = params if params is not None else default_try_on_params_from_env()
    return await asyncio.to_thread(run_fashn_inference_sync, user_bytes, cloth_bytes, p)


async def run_fashn_try_on(
    user_bytes: bytes,
    cloth_bytes: bytes,
    params: TryOnParams | None = None,
) -> str:
    """합성 PNG를 data:image/png;base64,... URL 형태로 반환 (프론트 호환)."""
    png = await run_fashn_try_on_bytes(user_bytes, cloth_bytes, params)
    return png_bytes_to_data_url(png)

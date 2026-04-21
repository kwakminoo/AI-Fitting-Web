from __future__ import annotations

import logging
import os
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from statistics import mean, quantiles
from time import perf_counter
from typing import Final

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent
_env_file = _backend_dir / ".env"
load_dotenv(Path.cwd() / ".env", override=True)
load_dotenv(Path.cwd() / "backend" / ".env", override=True)
load_dotenv(_env_file, override=True, encoding="utf-8-sig")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.fashn_vton import fashn_health, run_fashn_try_on, startup_load_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not _env_file.is_file():
    logger.warning("backend/.env 파일이 없습니다: %s", _env_file)

ALLOWED_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"},
)
MAX_BYTES: Final[int] = int(os.environ.get("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))
METRICS_WINDOW_SIZE: Final[int] = int(os.environ.get("TRY_ON_METRICS_WINDOW_SIZE", "300"))


class TryOnMetrics:
    """/api/try-on 성능 지표(메모리 기반) 수집기."""

    def __init__(self, window_size: int = 300) -> None:
        self.window_size = max(10, window_size)
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.latencies_ms: deque[float] = deque(maxlen=self.window_size)

    def record(self, *, success: bool, latency_ms: float) -> None:
        self.total_requests += 1
        if success:
            self.success_requests += 1
        else:
            self.failed_requests += 1
        self.latencies_ms.append(latency_ms)

    def snapshot(self) -> dict[str, int | float]:
        latency_list = list(self.latencies_ms)
        if latency_list:
            if len(latency_list) >= 2:
                percentile_values = quantiles(latency_list, n=100, method="inclusive")
                p50 = percentile_values[49]
                p95 = percentile_values[94]
            else:
                p50 = latency_list[0]
                p95 = latency_list[0]
            avg_ms = mean(latency_list)
            min_ms = min(latency_list)
            max_ms = max(latency_list)
        else:
            p50 = 0.0
            p95 = 0.0
            avg_ms = 0.0
            min_ms = 0.0
            max_ms = 0.0

        success_rate = (
            (self.success_requests / self.total_requests) * 100.0 if self.total_requests else 0.0
        )
        return {
            "window_size": self.window_size,
            "total_requests": self.total_requests,
            "success_requests": self.success_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": round(success_rate, 2),
            "latency_avg_ms": round(avg_ms, 2),
            "latency_p50_ms": round(p50, 2),
            "latency_p95_ms": round(p95, 2),
            "latency_min_ms": round(min_ms, 2),
            "latency_max_ms": round(max_ms, 2),
        }


try_on_metrics = TryOnMetrics(window_size=METRICS_WINDOW_SIZE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_load_pipeline()
    info = fashn_health()
    if info.get("fashn_ready"):
        logger.info("FASHN VTON 준비됨 | weights_dir=%s", info.get("fashn_weights_dir"))
    else:
        logger.warning(
            "FASHN VTON 미로드(합성 시 오류): %s",
            info.get("fashn_load_error") or "unknown",
        )
    yield


app = FastAPI(
    title="AI Virtual Fitting Room API",
    version="0.2.0",
    lifespan=lifespan,
)

_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "AI Virtual Fitting Room API",
        "health": "/health",
        "docs": "/docs",
        "try_on": "POST /api/try-on",
    }


@app.get("/health")
async def health() -> dict[str, str | bool | None]:
    fh = fashn_health()
    return {
        "status": "ok",
        "service": "AI Virtual Fitting Room API",
        "backend_env_path": str(_env_file),
        "backend_env_exists": _env_file.is_file(),
        **fh,
    }


@app.get("/metrics", summary="가상 피팅 성능 지표")
async def metrics() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "AI Virtual Fitting Room API",
        "try_on": try_on_metrics.snapshot(),
        "fashn": fashn_health(),
    }


@app.post(
    "/api/try-on",
    summary="의상만 교체하는 가상 피팅 (FASHN VTON 로컬)",
    description=(
        "사용자 전신 사진의 인물·배경은 유지하고, 옷만 두 번째 이미지의 의상으로 바꾼 합성 이미지를 "
        "data:image/png;base64,... 형태의 result_url 로 반환합니다. "
        "로컬 FASHN VTON v1.5 사전학습 가중치를 사용합니다."
    ),
)
async def try_on(
    user_img: UploadFile = File(..., description="피팅될 사람(전신)"),
    cloth_img: UploadFile = File(..., description="입힐 옷 참고(단품·모델 착용 컷)"),
) -> dict[str, str]:
    start = perf_counter()

    if user_img.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="user_img는 image/jpeg, image/png, image/webp만 허용됩니다.",
        )
    if cloth_img.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="cloth_img는 image/jpeg, image/png, image/webp만 허용됩니다.",
        )

    user_bytes = await user_img.read()
    cloth_bytes = await cloth_img.read()

    if len(user_bytes) > MAX_BYTES or len(cloth_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"파일당 최대 {MAX_BYTES // (1024 * 1024)}MB까지 업로드할 수 있습니다.",
        )

    if not user_bytes or not cloth_bytes:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    if not fashn_health().get("fashn_ready"):
        raise HTTPException(
            status_code=503,
            detail=(
                "FASHN 파이프라인이 로드되지 않았습니다. "
                "가중치를 backend/weights 등에 받은 뒤 FASHN_WEIGHTS_DIR 을 확인하세요."
            ),
        )

    try:
        result_url = await run_fashn_try_on(user_bytes, cloth_bytes)
        elapsed_ms = (perf_counter() - start) * 1000.0
        try_on_metrics.record(success=True, latency_ms=elapsed_ms)
    except RuntimeError as e:
        elapsed_ms = (perf_counter() - start) * 1000.0
        try_on_metrics.record(success=False, latency_ms=elapsed_ms)
        logger.warning("try-on failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {"result_url": result_url}

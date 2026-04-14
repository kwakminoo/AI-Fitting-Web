from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
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

ALLOWED_TYPES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png"})
MAX_BYTES: Final[int] = int(os.environ.get("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))


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
    if user_img.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="user_img는 image/jpeg 또는 image/png만 허용됩니다.",
        )
    if cloth_img.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="cloth_img는 image/jpeg 또는 image/png만 허용됩니다.",
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
    except RuntimeError as e:
        logger.warning("try-on failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {"result_url": result_url}

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# .env는 반드시 idm_vton 등 서비스 모듈 임포트 전에 로드해야 함
# 순서: cwd의 .env 먼저, 마지막에 main.py와 같은 폴더(backend/.env)를 override로 적용.
# (루트 AI-Fitting/.env에 REPLICATE_API_TOKEN= 만 있으면 기존 순서에서는 백엔드 토큰이 덮어써짐)
_backend_dir = Path(__file__).resolve().parent
_env_file = _backend_dir / ".env"
load_dotenv(Path.cwd() / ".env", override=True)
load_dotenv(Path.cwd() / "backend" / ".env", override=True)
load_dotenv(_env_file, override=True, encoding="utf-8-sig")

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.idm_vton import run_idm_vton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not _env_file.is_file():
    logger.warning("backend/.env 파일이 없습니다: %s", _env_file)
elif not (os.environ.get("REPLICATE_API_TOKEN") or "").strip():
    logger.warning(
        "REPLICATE_API_TOKEN이 비어 있습니다. %s 내용과 OS 환경변수(빈 값)를 확인하세요.",
        _env_file,
    )

ALLOWED_TYPES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png"})
MAX_BYTES: Final[int] = int(os.environ.get("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024)))

app = FastAPI(title="AI Virtual Fitting Room API", version="0.1.0")

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
async def health() -> dict[str, str | bool]:
    token_ok = bool((os.environ.get("REPLICATE_API_TOKEN") or "").strip())
    return {
        "status": "ok",
        # 이 필드가 없으면 8000번에 예전/다른 앱이 떠 있는 것입니다. uvicorn을 끄고 이 프로젝트 backend에서 다시 실행하세요.
        "service": "AI Virtual Fitting Room API",
        "replicate_configured": token_ok,
        "backend_env_path": str(_env_file),
        "backend_env_exists": _env_file.is_file(),
    }


@app.on_event("startup")
async def _startup_log_replicate() -> None:
    ok = bool((os.environ.get("REPLICATE_API_TOKEN") or "").strip())
    logger.info(
        "Replicate: %s | backend/.env: %s",
        "토큰 로드됨" if ok else "토큰 없음(합성 시 오류)",
        "있음" if _env_file.is_file() else "파일 없음",
    )


@app.post(
    "/api/try-on",
    summary="의상만 교체하는 가상 피팅",
    description=(
        "사용자 전신 사진의 인물·배경은 유지하고, 옷만 두 번째 이미지의 의상으로 바꾼 합성 이미지 URL 1개를 반환합니다. "
        "배경 제거 등 별도 전처리는 하지 않습니다."
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

    user_mime = user_img.content_type or "image/jpeg"
    cloth_mime = cloth_img.content_type or "image/jpeg"

    try:
        result_url = await run_idm_vton(
            user_bytes,
            user_mime,
            cloth_bytes,
            cloth_mime,
        )
    except RuntimeError as e:
        logger.warning("try-on failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {"result_url": result_url}

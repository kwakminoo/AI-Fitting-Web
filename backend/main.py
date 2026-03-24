from __future__ import annotations

import logging
import os
from typing import Final

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from services.idm_vton import run_idm_vton

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/try-on")
async def try_on(
    user_img: UploadFile = File(..., description="전신 사용자 사진"),
    cloth_img: UploadFile = File(..., description="옷 이미지"),
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

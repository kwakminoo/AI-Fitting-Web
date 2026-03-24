"""
가상 피팅 전용: 내 사진(human)의 인물·포즈·배경을 유지하고, 옷만 참고 이미지(garment) 기준으로 교체.

- 배경 제거, 얼굴 교체, 별도 마스크 편집 등 다른 기능은 호출하지 않습니다.
- mask_img 등은 전달하지 않으며(모델이 영역 추정), 입력은 human_img + garm_img 중심입니다.

비공식 Replicate 모델은 POST /v1/predictions + version id 후 폴링합니다.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# backend/services → backend
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_ENV = _BACKEND_ROOT / ".env"


def _load_replicate_token_from_backend_env() -> str:
    """main 임포트 순서·cwd와 무관하게 backend/.env에서 토큰을 다시 읽습니다."""
    load_dotenv(_BACKEND_ENV, override=True, encoding="utf-8-sig")
    return (os.environ.get("REPLICATE_API_TOKEN") or "").strip()

HTTP_TIMEOUT = httpx.Timeout(120.0, connect=30.0)
VERSION_ID_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


def _data_uri(data: bytes, mime: str) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _split_model(model_id: str) -> tuple[str, str]:
    model_id = model_id.strip().strip("/")
    if "/" not in model_id:
        raise ValueError(
            "REPLICATE_MODEL must be 'owner/model', e.g. cuuupid/idm-vton",
        )
    owner, name = model_id.split("/", 1)
    if not owner or not name:
        raise ValueError("REPLICATE_MODEL owner and name must be non-empty")
    return owner, name


def _extract_output(output: Any) -> str:
    if output is None:
        raise RuntimeError("모델 출력이 비어 있습니다.")
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list) and output:
        return _extract_output(output[0])
    if isinstance(output, dict):
        for key in ("url", "image", "output", "uri"):
            v = output.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
    raise RuntimeError(
        f"모델 출력 형식을 해석할 수 없습니다: {type(output).__name__}",
    )


async def _resolve_version_id(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    owner: str,
    name: str,
) -> str:
    explicit = (os.environ.get("REPLICATE_VERSION") or "").strip()
    if explicit:
        if VERSION_ID_RE.match(explicit):
            return explicit.lower()
        raise RuntimeError(
            "REPLICATE_VERSION은 Replicate 모델 Versions 탭의 "
            "64자 16진 버전 ID여야 합니다. 비우면 latest_version을 자동 조회합니다.",
        )

    meta_url = f"https://api.replicate.com/v1/models/{owner}/{name}"
    meta_resp = await client.get(meta_url, headers=headers)
    try:
        meta = meta_resp.json()
    except ValueError as e:
        raise RuntimeError("Replicate 모델 메타 응답이 JSON이 아닙니다.") from e

    if meta_resp.status_code >= 400:
        detail = meta.get("detail", meta.get("title", str(meta)))
        raise RuntimeError(_format_replicate_error(detail, meta_resp.status_code))

    latest = meta.get("latest_version") or {}
    vid = latest.get("id")
    if not vid or not isinstance(vid, str):
        raise RuntimeError(
            "모델 메타데이터에 latest_version.id가 없습니다. "
            "REPLICATE_VERSION에 버전 ID를 직접 넣어 보세요.",
        )
    if not VERSION_ID_RE.match(vid):
        logger.warning("Unexpected version id format from API: %s", vid[:16])
    return vid.lower()


async def run_idm_vton(
    user_img: bytes,
    user_mime: str,
    cloth_img: bytes,
    cloth_mime: str,
) -> str:
    """
    사용자 전신 이미지(human)와 옷/착장 참고 이미지(garment)로 가상 피팅 1장을 생성합니다.
    (내 사진 속 인물의 의상만 참고 이미지의 옷으로 바꾼 결과 URL 1개)
    """
    token = (os.environ.get("REPLICATE_API_TOKEN") or "").strip()
    if not token:
        token = _load_replicate_token_from_backend_env()
    if not token:
        hint = (
            f"backend/.env 경로: {_BACKEND_ENV} "
            f"(존재: {_BACKEND_ENV.is_file()}). "
            "한 줄에 REPLICATE_API_TOKEN=r8_... 형식인지, 따옴표 없이 저장했는지 확인하세요."
        )
        raise RuntimeError(
            "REPLICATE_API_TOKEN 환경 변수가 설정되지 않았습니다. "
            "backend/.env에 토큰을 추가하세요. "
            + hint,
        )

    model_id = (os.environ.get("REPLICATE_MODEL") or "cuuupid/idm-vton").strip()
    poll_interval_sec = float(os.environ.get("REPLICATE_POLL_INTERVAL_SEC", "1.5"))
    max_wait_sec = float(os.environ.get("REPLICATE_MAX_WAIT_SEC", "600"))

    owner, name = _split_model(model_id)
    human_uri = _data_uri(user_img, user_mime)
    garm_uri = _data_uri(cloth_img, cloth_mime)

    # IDM-VTON: 인물 이미지 + 옷 참고만 전달. mask_img 미전달 = 모델이 의상 영역 처리(배경지우기 API 아님).
    input_payload: dict[str, Any] = {
        "human_img": human_uri,
        "garm_img": garm_uri,
        "garment_des": os.environ.get("REPLICATE_GARMENT_DES", "garment"),
        # upper_body | lower_body | dresses — 바꿀 의상 부위(기본 상의)
        "category": os.environ.get("REPLICATE_CATEGORY", "upper_body"),
        # 전신 비율이 3:4가 아닐 때 인물 영역 정렬(배경 제거와 무관)
        "crop": os.environ.get("REPLICATE_CROP", "true").lower()
        in ("1", "true", "yes"),
    }

    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            version_id = await _resolve_version_id(client, headers, owner, name)
        except httpx.RequestError as e:
            raise RuntimeError(f"Replicate 연결 실패: {e}") from e

        # 공식(official) 모델이 아닌 경우 /v1/models/.../predictions 는 404 → /v1/predictions 사용
        try:
            create_resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={"version": version_id, "input": input_payload},
            )
        except httpx.RequestError as e:
            logger.exception("Replicate request failed")
            raise RuntimeError(f"Replicate 연결 실패: {e}") from e

        try:
            body = create_resp.json()
        except ValueError as e:
            raise RuntimeError("Replicate 응답이 올바른 JSON이 아닙니다.") from e

        if create_resp.status_code >= 400:
            detail = body.get("detail", body.get("title", str(body)))
            logger.warning("Replicate create prediction error: %s", detail)
            raise RuntimeError(_format_replicate_error(detail, create_resp.status_code))

        urls = body.get("urls") or {}
        get_url = urls.get("get")
        if not get_url:
            raise RuntimeError("Replicate 응답에 prediction URL이 없습니다.")

        elapsed = 0.0
        while elapsed < max_wait_sec:
            try:
                poll_resp = await client.get(get_url, headers=headers)
            except httpx.RequestError as e:
                raise RuntimeError(f"Replicate 폴링 실패: {e}") from e

            try:
                pred = poll_resp.json()
            except ValueError as e:
                raise RuntimeError("Replicate 폴링 응답이 JSON이 아닙니다.") from e

            if poll_resp.status_code >= 400:
                detail = pred.get("detail", pred)
                raise RuntimeError(_format_replicate_error(detail, poll_resp.status_code))

            status = pred.get("status")
            if status == "succeeded":
                return _extract_output(pred.get("output"))
            if status in ("failed", "canceled"):
                err = pred.get("error") or "예측이 실패했습니다."
                raise RuntimeError(f"Replicate: {err}")
            if status not in (None, "starting", "processing"):
                logger.warning("Unknown prediction status: %s", status)

            await asyncio.sleep(poll_interval_sec)
            elapsed += poll_interval_sec

        raise RuntimeError(
            f"Replicate 응답 대기 시간 초과 ({max_wait_sec:.0f}초). 잠시 후 다시 시도하세요.",
        )


def _format_replicate_error(detail: Any, status_code: int) -> str:
    if isinstance(detail, str):
        return f"Replicate 오류 ({status_code}): {detail}"
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict) and "msg" in item:
                parts.append(str(item["msg"]))
            else:
                parts.append(str(item))
        return f"Replicate 오류 ({status_code}): {'; '.join(parts)}"
    return f"Replicate 오류 ({status_code}): {detail!r}"

"""Replicate IDM-VTON 호출: 예측 생성 후 폴링으로 결과 URL 반환."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")
REPLICATE_MODEL = os.environ.get("REPLICATE_MODEL", "cuuupid/idm-vton")
POLL_INTERVAL_SEC = float(os.environ.get("REPLICATE_POLL_INTERVAL_SEC", "1.5"))
MAX_WAIT_SEC = float(os.environ.get("REPLICATE_MAX_WAIT_SEC", "600"))
HTTP_TIMEOUT = httpx.Timeout(120.0, connect=30.0)


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
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str) and first.startswith("http"):
            return first
    raise RuntimeError(f"Unexpected model output shape: {type(output).__name__}")


async def run_idm_vton(
    user_img: bytes,
    user_mime: str,
    cloth_img: bytes,
    cloth_mime: str,
) -> str:
    """
    사용자 이미지·옷 이미지 바이트를 받아 Replicate IDM-VTON을 호출하고
    결과 이미지 URL을 반환합니다.
    """
    if not REPLICATE_API_TOKEN:
        raise RuntimeError(
            "REPLICATE_API_TOKEN 환경 변수가 설정되지 않았습니다. "
            "backend/.env에 토큰을 추가하세요.",
        )

    owner, name = _split_model(REPLICATE_MODEL)
    human_uri = _data_uri(user_img, user_mime)
    garm_uri = _data_uri(cloth_img, cloth_mime)

    input_payload: dict[str, Any] = {
        "human_img": human_uri,
        "garm_img": garm_uri,
        "garment_des": os.environ.get("REPLICATE_GARMENT_DES", "garment"),
        "category": os.environ.get("REPLICATE_CATEGORY", "upper_body"),
        "crop": os.environ.get("REPLICATE_CROP", "true").lower() in (
            "1",
            "true",
            "yes",
        ),
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    create_url = f"https://api.replicate.com/v1/models/{owner}/{name}/predictions"

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        try:
            create_resp = await client.post(
                create_url,
                headers=headers,
                json={"input": input_payload},
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
        while elapsed < MAX_WAIT_SEC:
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

            await asyncio.sleep(POLL_INTERVAL_SEC)
            elapsed += POLL_INTERVAL_SEC

        raise RuntimeError(
            f"Replicate 응답 대기 시간 초과 ({MAX_WAIT_SEC:.0f}초). 잠시 후 다시 시도하세요.",
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

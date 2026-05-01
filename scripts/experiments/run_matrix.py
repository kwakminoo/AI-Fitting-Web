#!/usr/bin/env python3
"""
T1~T6 × (3인물 × 3의류) = 54회 실험.

기본: 로컬에서 services.fashn_vton 직접 호출 (--local, 서버 재시작 불필요).
옵션: --http 로 POST /api/try-on/experiment (최신 백엔드 재기동 필요).
--resume: 기존 latency.csv·PNG가 있으면 (Trial, 인물, 의류) 조합 단위로 건너뜀.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
SAMPLES_JSON = Path(__file__).resolve().parent / "samples.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
LATENCY_CSV = RESULTS_DIR / "latency.csv"

LATENCY_HEADER: list[str] = [
    "trial_id",
    "steps",
    "guidance",
    "person_idx",
    "garment_idx",
    "person_path",
    "garment_path",
    "latency_ms",
    "http_status",
    "error",
]

BASE_URL = (os.environ.get("EXPERIMENT_API_BASE") or "http://127.0.0.1:8000").rstrip("/")

try:
    import requests
except ImportError:
    requests = None  # type: ignore[misc, assignment]

TRIALS: list[tuple[str, int, float]] = [
    ("T1", 18, 1.20),
    ("T2", 22, 1.35),
    ("T3", 30, 1.50),
    ("T4", 34, 1.65),
    ("T5", 40, 1.80),
    ("T6", 46, 2.00),
]

_TRIAL_ORDER: dict[str, int] = {tid: i for i, (tid, _, _) in enumerate(TRIALS)}


def _sort_latency_rows(rows: list[list[str]]) -> list[list[str]]:
    def sort_key(row: list[str]) -> tuple[int, int, int]:
        k = _combo_key(row)
        if k is None:
            return (999, 999, 999)
        tid, pi, gi = k
        return (_TRIAL_ORDER.get(tid, 999), pi, gi)

    return sorted(rows, key=sort_key)


def _mime(path: Path) -> str:
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"):
        return "image/jpeg"
    if s == ".png":
        return "image/png"
    if s == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _save_data_url_png(data_url: str, out_path: Path) -> None:
    m = re.match(r"^data:image/png;base64,(.+)$", data_url, re.DOTALL)
    if not m:
        raise ValueError("result_url이 예상 PNG data URL 형식이 아닙니다.")
    raw = base64.b64decode(m.group(1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)


def _read_latency_table() -> tuple[list[str], list[list[str]]]:
    """기존 latency.csv가 있으면 헤더+데이터 행을 반환. 없거나 비면 기본 헤더와 빈 리스트."""
    if not LATENCY_CSV.is_file():
        return LATENCY_HEADER, []
    with LATENCY_CSV.open(newline="", encoding="utf-8") as fcsv:
        rows = list(csv.reader(fcsv))
    if not rows:
        return LATENCY_HEADER, []
    header, *data = rows
    if len(header) != len(LATENCY_HEADER):
        return LATENCY_HEADER, []
    return header, data


def _write_latency_table(header: list[str], data_rows: list[list[str]]) -> None:
    LATENCY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with LATENCY_CSV.open("w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(header)
        for row in data_rows:
            w.writerow(row)


def _combo_key(row: list[str]) -> tuple[str, int, int] | None:
    if len(row) < 5:
        return None
    try:
        return (row[0], int(row[3]), int(row[4]))
    except ValueError:
        return None


def _health_ready() -> bool:
    if requests is None:
        return False
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            return False
        j = r.json()
        return bool(j.get("fashn_ready"))
    except OSError:
        return False


def _run_http_matrix(persons: list[str], garments: list[str], *, resume: bool) -> int:
    if requests is None:
        print("HTTP 모드에는 requests 패키지가 필요합니다.", file=sys.stderr)
        return 2
    if not _health_ready():
        print(
            f"백엔드 {BASE_URL}/health 에서 fashn_ready=false 이거나 연결 실패.",
            file=sys.stderr,
        )
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0
    by_key: dict[tuple[str, int, int], list[str]] = {}
    if resume:
        _, rows = _read_latency_table()
        for row in rows:
            k = _combo_key(row)
            if k:
                by_key[k] = row

    for tid, steps, guidance in TRIALS:
        for pi, ppath in enumerate(persons[:3], start=1):
            for gi, gpath in enumerate(garments[:3], start=1):
                pp = Path(ppath)
                gp = Path(gpath)
                out_png = RESULTS_DIR / tid / f"p{pi}-g{gi}.png"
                key = (tid, pi, gi)
                if resume and key in by_key and out_png.is_file():
                    continue

                t0 = time.perf_counter()
                err = ""
                status = 0
                try:
                    with pp.open("rb") as pf, gp.open("rb") as gf:
                        files = {
                            "user_img": (pp.name, pf, _mime(pp)),
                            "cloth_img": (gp.name, gf, _mime(gp)),
                        }
                        form = {
                            "num_timesteps": str(steps),
                            "guidance_scale": str(guidance),
                            "category": "tops",
                            "garment_photo_type": "flat-lay",
                            "seed": "42",
                        }
                        resp = requests.post(
                            f"{BASE_URL}/api/try-on/experiment",
                            files=files,
                            data=form,
                            timeout=600,
                        )
                    status = resp.status_code
                    resp.raise_for_status()
                    body = resp.json()
                    url = body.get("result_url")
                    if not isinstance(url, str):
                        raise ValueError("응답에 result_url 없음")
                    _save_data_url_png(url, out_png)
                except Exception as e:  # noqa: BLE001
                    err = str(e)
                    errors += 1
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                by_key[key] = [
                    tid,
                    steps,
                    guidance,
                    pi,
                    gi,
                    str(pp),
                    str(gp),
                    f"{elapsed_ms:.1f}",
                    status,
                    err,
                ]
                _write_latency_table(LATENCY_HEADER, _sort_latency_rows(list(by_key.values())))
                print(f"{tid} p{pi} g{gi} {elapsed_ms:.0f}ms status={status} err={err[:80]!r}")

    _write_latency_table(LATENCY_HEADER, _sort_latency_rows(list(by_key.values())))
    print(f"Done. CSV: {LATENCY_CSV}")
    return 1 if errors else 0


def _run_local_matrix(persons: list[str], garments: list[str], *, resume: bool) -> int:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    try:
        from dotenv import load_dotenv

        load_dotenv(BACKEND_DIR / ".env", encoding="utf-8-sig")
    except ImportError:
        pass

    from services.fashn_vton import (  # type: ignore[import-not-found]
        TryOnParams,
        fashn_health,
        run_fashn_inference_sync,
        startup_load_pipeline,
    )

    startup_load_pipeline()
    if not fashn_health().get("fashn_ready"):
        print("FASHN 파이프라인 로드 실패. 가중치 경로를 확인하세요.", file=sys.stderr)
        return 2

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    errors = 0
    by_key: dict[tuple[str, int, int], list[str]] = {}
    if resume:
        _, rows = _read_latency_table()
        for row in rows:
            k = _combo_key(row)
            if k:
                by_key[k] = row

    for tid, steps, guidance in TRIALS:
        for pi, ppath in enumerate(persons[:3], start=1):
            for gi, gpath in enumerate(garments[:3], start=1):
                pp = Path(ppath)
                gp = Path(gpath)
                out_png = RESULTS_DIR / tid / f"p{pi}-g{gi}.png"
                key = (tid, pi, gi)
                if resume and key in by_key and out_png.is_file():
                    continue

                t0 = time.perf_counter()
                err = ""
                status = 200
                try:
                    user_b = pp.read_bytes()
                    cloth_b = gp.read_bytes()
                    params = TryOnParams(
                        category="tops",
                        garment_photo_type="flat-lay",
                        num_timesteps=steps,
                        guidance_scale=guidance,
                        seed=42,
                    )
                    png = run_fashn_inference_sync(user_b, cloth_b, params)
                    out_png.parent.mkdir(parents=True, exist_ok=True)
                    out_png.write_bytes(png)
                except Exception as e:  # noqa: BLE001
                    err = str(e)
                    status = 0
                    errors += 1
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                by_key[key] = [
                    tid,
                    steps,
                    guidance,
                    pi,
                    gi,
                    str(pp),
                    str(gp),
                    f"{elapsed_ms:.1f}",
                    status,
                    err,
                ]
                _write_latency_table(LATENCY_HEADER, _sort_latency_rows(list(by_key.values())))
                print(f"{tid} p{pi} g{gi} {elapsed_ms:.0f}ms status={status} err={err[:80]!r}")

    _write_latency_table(LATENCY_HEADER, _sort_latency_rows(list(by_key.values())))
    print(f"Done (local). CSV: {LATENCY_CSV}")
    return 1 if errors else 0


def _maybe_reexec_with_backend_venv(argv: list[str]) -> None:
    """backend/.venv Python이 있으면 그 인터프리터로 스크립트를 한 번 재실행하고 종료."""
    if os.environ.get("_RUN_MATRIX_IN_VENV") == "1":
        return
    venv_win = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    venv_unix = BACKEND_DIR / ".venv" / "bin" / "python"
    target = venv_win if venv_win.is_file() else venv_unix if venv_unix.is_file() else None
    if target is None:
        return
    if Path(sys.executable).resolve() == Path(target).resolve():
        return
    env = os.environ.copy()
    env["_RUN_MATRIX_IN_VENV"] = "1"
    rc = subprocess.call([str(target), str(Path(__file__).resolve()), *argv], env=env)
    raise SystemExit(rc)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--http",
        action="store_true",
        help="HTTP로 /api/try-on/experiment 호출 (백엔드 최신 코드 재기동 필요)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="기존 latency.csv·PNG가 있으면 해당 (Trial, 인물, 의류) 조합은 건너뜀",
    )
    args = parser.parse_args()

    if not args.http:
        _maybe_reexec_with_backend_venv(sys.argv[1:])

    if not SAMPLES_JSON.is_file():
        print(f"samples.json 없음: {SAMPLES_JSON} — 먼저 select_samples.py 실행", file=sys.stderr)
        sys.exit(1)

    data: dict[str, Any] = json.loads(SAMPLES_JSON.read_text(encoding="utf-8"))
    persons: list[str] = data.get("persons") or []
    garments: list[str] = data.get("garments") or []
    if len(persons) < 3 or len(garments) < 3:
        print("persons 또는 garments가 3개 미만입니다.", file=sys.stderr)
        sys.exit(1)

    if args.http:
        rc = _run_http_matrix(persons, garments, resume=args.resume)
    else:
        rc = _run_local_matrix(persons, garments, resume=args.resume)
    sys.exit(rc)


if __name__ == "__main__":
    main()

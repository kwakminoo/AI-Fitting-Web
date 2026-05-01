#!/usr/bin/env python3
"""
3인물·3의류 자동 선정: 고정 경로(환경 변수) + testIMG 풀에서 규칙 기반 선택.
결과: scripts/experiments/samples.json
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore[misc, assignment]

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = Path(__file__).resolve().parent / "samples.json"
TEST_IMG_DIR = REPO_ROOT / "testIMG"

EXTS = {".jpg", ".jpeg", ".png", ".webp"}

PERSON_KEYS = ("person", "myimg", "model", "test1", "test2", "test3")
GARMENT_KEYS = ("garment", "codyimg", "cloth", "top", "shirt", "testimg")


def _mime_for(path: Path) -> str:
    s = path.suffix.lower()
    if s in (".jpg", ".jpeg"):
        return "image/jpeg"
    if s == ".png":
        return "image/png"
    if s == ".webp":
        return "image/webp"
    return "application/octet-stream"


def _collect_files() -> list[Path]:
    if not TEST_IMG_DIR.is_dir():
        return []
    out: list[Path] = []
    for p in TEST_IMG_DIR.rglob("*"):
        if p.is_file() and p.suffix.lower() in EXTS:
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def _classify(path: Path) -> tuple[bool, bool]:
    s = str(path).lower().replace("\\", "/")
    is_person = any(k in s for k in PERSON_KEYS)
    is_garment = any(k in s for k in GARMENT_KEYS)
    return is_person, is_garment


def _aspect_hw(path: Path) -> tuple[float, float] | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            w, h = im.size
            if w <= 0 or h <= 0:
                return None
            return float(h) / float(w), float(w) / float(h)
    except OSError:
        return None


def _score_person(path: Path) -> float:
    s = str(path).lower().replace("\\", "/")
    is_p, is_g = _classify(path)
    score = 0.0
    if "resultimg" in s:
        score -= 80.0
    if is_p:
        score += 50.0
    if is_g:
        score -= 30.0
    asp = _aspect_hw(path)
    if asp:
        hw, wh = asp
        if hw >= 1.15:
            score += 20.0
        if hw < 0.9:
            score -= 15.0
    # 다양성: 서브폴더 깊이
    rel = path.relative_to(TEST_IMG_DIR)
    score += min(len(rel.parts), 4) * 2.0
    ext = path.suffix.lower()
    if ext == ".webp":
        score += 1.0
    return score


def _score_garment(path: Path) -> float:
    s = str(path).lower().replace("\\", "/")
    is_p, is_g = _classify(path)
    score = 0.0
    if "resultimg" in s:
        score -= 100.0
    if is_g:
        score += 50.0
    if is_p and not is_g:
        score += 5.0
    asp = _aspect_hw(path)
    if asp:
        hw, wh = asp
        if wh >= 1.6:
            score -= 40.0
        if 0.7 <= hw <= 1.4:
            score += 10.0
    rel = path.relative_to(TEST_IMG_DIR)
    score += min(len(rel.parts), 4) * 2.0
    ext = path.suffix.lower()
    if ext in (".png", ".webp"):
        score += 1.0
    return score


def _unique_paths(paths: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        rp = str(Path(p).resolve())
        if rp in seen:
            continue
        seen.add(rp)
        out.append(rp)
        if len(out) >= limit:
            break
    return out


def main() -> None:
    fixed_p = (os.environ.get("VITON_FIXED_PERSON") or "").strip()
    fixed_g = (os.environ.get("VITON_FIXED_GARMENT") or "").strip()

    persons: list[str] = []
    garments: list[str] = []

    for fp in (fixed_p,):
        if fp and Path(fp).is_file():
            persons.append(str(Path(fp).resolve()))
    for fg in (fixed_g,):
        if fg and Path(fg).is_file():
            garments.append(str(Path(fg).resolve()))

    files = _collect_files()
    ranked_p = sorted(files, key=lambda p: _score_person(p), reverse=True)
    ranked_g = sorted(files, key=lambda p: _score_garment(p), reverse=True)

    fallback_order = [
        REPO_ROOT / "testIMG" / "person.webp",
        REPO_ROOT / "testIMG" / "person.png",
        REPO_ROOT / "testIMG" / "myIMG",
        REPO_ROOT / "testIMG" / "garment.png",
        REPO_ROOT / "testIMG" / "garment.webp",
        REPO_ROOT / "testIMG" / "codyIMG",
    ]

    def fill_persons() -> None:
        nonlocal persons
        for p in ranked_p:
            ps = str(p.resolve())
            if ps not in persons:
                persons.append(ps)
            if len(persons) >= 3:
                return
        for base in fallback_order:
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file() and p.suffix.lower() in EXTS:
                        ps = str(p.resolve())
                        if ps not in persons:
                            persons.append(ps)
                        if len(persons) >= 3:
                            return
            elif base.is_file() and base.suffix.lower() in EXTS:
                ps = str(base.resolve())
                if ps not in persons:
                    persons.append(ps)
                if len(persons) >= 3:
                    return

    def fill_garments() -> None:
        nonlocal garments
        for p in ranked_g:
            gs = str(p.resolve())
            if gs not in garments:
                garments.append(gs)
            if len(garments) >= 3:
                return
        for base in fallback_order:
            if base.is_dir():
                for p in sorted(base.rglob("*")):
                    if p.is_file() and p.suffix.lower() in EXTS:
                        gs = str(p.resolve())
                        if gs not in garments:
                            garments.append(gs)
                        if len(garments) >= 3:
                            return
            elif base.is_file() and base.suffix.lower() in EXTS:
                gs = str(base.resolve())
                if gs not in garments:
                    garments.append(gs)
                if len(garments) >= 3:
                    return

    fill_persons()
    fill_garments()

    persons = _unique_paths(persons, 3)
    garments = _unique_paths(garments, 3)

    meta = {
        "repo_root": str(REPO_ROOT),
        "testimg_dir": str(TEST_IMG_DIR),
        "pil_available": Image is not None,
        "fixed_person_env": fixed_p or None,
        "fixed_garment_env": fixed_g or None,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"persons": persons, "garments": garments, "meta": meta}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {OUT_JSON}")
    print("persons:", *persons, sep="\n  ")
    print("garments:", *garments, sep="\n  ")


if __name__ == "__main__":
    main()

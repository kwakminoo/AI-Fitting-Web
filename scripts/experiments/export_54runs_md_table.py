"""54회 실행 상세를 마크다운 표 조각으로 내보냄 (보고서에 수동 붙여넣기/검수용)."""
from __future__ import annotations

import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CSV_PATH = REPO / "scripts" / "experiments" / "results" / "latency.csv"
OUT = REPO / "docs" / "experiments" / "_54runs_table_fragment.md"


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8", newline="")))
    lines = [
        "| Trial | p | g | steps | guidance | latency (ms) | http |",
        "|---:|---:|---:|---:|---:|---:|:---|",
    ]
    for r in rows:
        lines.append(
            "| {tid} | {p} | {g} | {s} | {g2} | {lat:.1f} | {h} |".format(
                tid=r["trial_id"],
                p=r["person_idx"],
                g=r["garment_idx"],
                s=r["steps"],
                g2=r["guidance"],
                lat=float(r["latency_ms"]),
                h=r.get("http_status", ""),
            )
        )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
latency.csv 및 보고서 §4 정성 점수로 docs/experiments/figures/*.png 생성.
GitHub 표시용: 저장 후 EXPERIMENT_REPORT.md에 raw.githubusercontent.com URL로 삽입.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "scripts" / "experiments" / "results" / "latency.csv"
OUT_DIR = REPO_ROOT / "docs" / "experiments" / "figures"

# 보고서 §4 정성 표 — 인물/의류/경계/디테일 평균을 «정성 종합(프록시)»로 사용
QUALITY_BY_TRIAL: dict[str, tuple[float, float, float, float]] = {
    "T1": (4.0, 3.5, 3.0, 3.5),
    "T2": (4.0, 4.0, 3.5, 4.0),
    "T3": (4.5, 4.5, 4.0, 4.5),
    "T4": (4.5, 4.5, 4.0, 4.5),
    "T5": (4.5, 4.5, 4.5, 4.5),
    "T6": (4.5, 4.5, 4.5, 4.5),
}

TRIAL_ORDER = ["T1", "T2", "T3", "T4", "T5", "T6"]


def _load_latency_by_trial() -> dict[str, list[float]]:
    by_t: dict[str, list[float]] = defaultdict(list)
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            by_t[row["trial_id"]].append(float(row["latency_ms"]))
    return by_t


def _percentile(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    i = int(round(q * (len(xs) - 1)))
    return xs[i]


def _setup_matplotlib_ko() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 150,
            "font.size": 10,
            "axes.titlesize": 12,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            # Windows: Malgun Gothic 있으면 한글 축 제목이 안정적
            "font.family": "sans-serif",
            "font.sans-serif": ["Malgun Gothic", "AppleGothic", "Noto Sans CJK KR", "DejaVu Sans"],
        },
    )


def plot_latency_mean_p95(by_trial: dict[str, list[float]]) -> None:
    import matplotlib.pyplot as plt

    means = [mean(by_trial[t]) / 1000.0 for t in TRIAL_ORDER]
    p95s = [_percentile(by_trial[t], 0.95) / 1000.0 for t in TRIAL_ORDER]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(TRIAL_ORDER))
    w = 0.35
    ax.bar([i - w / 2 for i in x], means, width=w, label="평균 지연 (s)", color="#2563eb")
    ax.bar([i + w / 2 for i in x], p95s, width=w, label="p95 지연 (s)", color="#93c5fd")
    ax.set_xticks(list(x))
    ax.set_xticklabels(TRIAL_ORDER)
    ax.set_xlabel("Trial")
    ax.set_ylabel("추론 시간 (초)")
    ax.set_title("Trial별 추론 지연 (9회 평균·p95)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "latency_mean_p95_by_trial.png")
    plt.close()


def plot_quality_latency_tradeoff(by_trial: dict[str, list[float]]) -> None:
    import matplotlib.pyplot as plt

    q_avg = []
    for t in TRIAL_ORDER:
        a, b, c, d = QUALITY_BY_TRIAL[t]
        q_avg.append((a + b + c + d) / 4.0)
    lat_s = [mean(by_trial[t]) / 1000.0 for t in TRIAL_ORDER]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(lat_s, q_avg, s=120, c=range(6), cmap="viridis", zorder=3, edgecolors="white", linewidths=1.5)
    for i, tid in enumerate(TRIAL_ORDER):
        ax.annotate(tid, (lat_s[i], q_avg[i]), textcoords="offset points", xytext=(6, 4), fontsize=10)
    ax.set_xlabel("평균 추론 지연 (초)")
    ax.set_ylabel("정성 종합 점수 (§4 표, 4항목 평균 / 5점 만점)")
    ax.set_title("지연 vs 정성 (주관 평가 프록시)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "quality_latency_tradeoff.png")
    plt.close()


def plot_steps_vs_latency(by_trial: dict[str, list[float]]) -> None:
    """steps 수와 평균 지연의 관계 (설계상 거의 선형에 가깝다는 점 시각화)."""
    import matplotlib.pyplot as plt

    steps_map = {"T1": 18, "T2": 22, "T3": 30, "T4": 34, "T5": 40, "T6": 46}
    xs = [steps_map[t] for t in TRIAL_ORDER]
    ys = [mean(by_trial[t]) / 1000.0 for t in TRIAL_ORDER]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, ys, "o-", color="#0f766e", linewidth=2, markersize=8)
    for x, y, tid in zip(xs, ys, TRIAL_ORDER, strict=True):
        ax.annotate(tid, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=9)
    ax.set_xlabel("num_timesteps (steps)")
    ax.set_ylabel("평균 추론 지연 (초)")
    ax.set_title("확산 추론 스텝 수와 평균 지연")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "steps_vs_latency.png")
    plt.close()


def main() -> None:
    if not CSV_PATH.is_file():
        raise SystemExit(f"CSV 없음: {CSV_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_trial = _load_latency_by_trial()
    for t in TRIAL_ORDER:
        if len(by_trial.get(t, [])) != 9:
            print(f"경고: {t} 행 수 {len(by_trial.get(t, []))} (기대 9)")

    _setup_matplotlib_ko()
    plot_latency_mean_p95(by_trial)
    plot_quality_latency_tradeoff(by_trial)
    plot_steps_vs_latency(by_trial)
    print("저장:", OUT_DIR)


if __name__ == "__main__":
    main()

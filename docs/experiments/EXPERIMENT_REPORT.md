# FASHN 프리셋 실험 리포트

**실험일:** 2026-05-01  
**매트릭스:** Trial T1~T6 × 인물 3 × 의류 3 = **54회** (seed=42, category=`tops`, garment_photo_type=`flat-lay`)  
**결과물:** `scripts/experiments/results/latency.csv`, `scripts/experiments/results/T{n}/p{pi}-g{gi}.png`

---

## 실험 과정·결과 시각 요약

### 진행 순서

1. **`scripts/experiments/select_samples.py`** 실행 → `samples.json`에 인물·의류 경로 확정  
2. **`scripts/experiments/run_matrix.py`** 실행 → 각 조합별 추론 후 `results/T{n}/p{i}-g{j}.png` 저장 및 `latency.csv` 기록  

### 데이터 흐름

```mermaid
flowchart LR
  S[samples.json] --> R[run_matrix.py]
  R --> CSV[latency.csv]
  R --> IMG["T{n}/p{i}-g{j}.png"]
```

### 입력 이미지 (대표 셀 **p1–g1**: 인물 1 · 의류 1)

아래는 실험에 실제 사용된 원본 입력입니다.

| 인물 (p1, `TEST2.jpg`) | 의류 (g1, `TESTIMG3.webp`) |
|:---:|:---:|
| ![실험 인물 p1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/testIMG/myIMG/TEST2.jpg) | ![실험 의류 g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/testIMG/codyIMG/TESTIMG3.webp) |

### 출력 비교 — 동일 입력에서 Trial별 결과 (p1–g1)

steps·guidance만 달리한 합성 결과입니다.

| T1 · 18 / 1.20 | T3 · 30 / 1.50 | T6 · 46 / 2.00 |
|:---:|:---:|:---:|
| ![T1 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T1/p1-g1.png) | ![T3 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T3/p1-g1.png) | ![T6 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T6/p1-g1.png) |

### 출력 비교 — 최종 프리셋에 대응하는 Trial (p1–g1)

| 빠름 **fast** (T2 · 22 / 1.35) | 기본 **default** (T3 · 30 / 1.50) | 느림 **slow** (T5 · 40 / 1.80) |
|:---:|:---:|:---:|
| ![T2 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T2/p1-g1.png) | ![T3 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T3/p1-g1.png) | ![T5 결과 p1-g1](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T5/p1-g1.png) |

### 추가 예시 (인물 p2 × 의류 g2, Trial **T3**)

![T3 결과 p2-g2](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/scripts/experiments/results/T3/p2-g2.png)

*GitHub 웹에서 이미지가 보이도록 `main` 브랜치 기준 raw URL을 사용합니다. 로컬 클론에서는 `testIMG/`, `scripts/experiments/results/` 경로의 동일 파일을 참고하면 됩니다.*

---

## 1. 선정 샘플 (`scripts/experiments/samples.json`)

| 구분 | 인덱스 | 경로 |
|------|--------|------|
| 인물 1 | p1 | `testIMG/myIMG/TEST2.jpg` |
| 인물 2 | p2 | `testIMG/model.webp` |
| 인물 3 | p3 | `testIMG/person.webp` |
| 의류 1 | g1 | `testIMG/codyIMG/TESTIMG3.webp` |
| 의류 2 | g2 | `testIMG/codyIMG/TESTIMG2.jpg` |
| 의류 3 | g3 | `testIMG/myIMG/TEST3.jpg` |

## 2. Trial 정의

| Trial | steps | guidance |
|-------|-------|------------|
| T1 | 18 | 1.20 |
| T2 | 22 | 1.35 |
| T3 | 30 | 1.50 |
| T4 | 34 | 1.65 |
| T5 | 40 | 1.80 |
| T6 | 46 | 2.00 |

## 3. 지연 시간 집계 (단위: ms, Trial당 n=9)

| Trial | mean | median | p95 |
|-------|------|--------|-----|
| T1 | 11837.4 | 11780.8 | 12382.9 |
| T2 | 14289.6 | 14269.1 | 14381.0 |
| T3 | 19438.9 | 19424.8 | 19557.5 |
| T4 | 21680.3 | 21652.5 | 21959.7 |
| T5 | 25347.8 | 25352.7 | 25441.5 |
| T6 | 29094.6 | 29098.1 | 29173.6 |

**관찰:** T1 대비 T2는 +~2.4s, T3는 +~7.6s(기본), T5는 +~13.5s(느림), T6는 +~17.3s. T5→T6는 지연만 +~3.7s(mean)로 증가 폭이 완만해 **품질 대비 비용** 관점에서 T6는 선택지에서 제외 후보.

### 3.1 측정 지표 범위 (학습 Loss / Accuracy)

본 프로젝트 실험은 **사전학습된 FASHN VTON 가중치로 추론만 수행**하며, **추가 학습(fine-tuning)을 하지 않습니다.** 따라서 에폭별 **학습 Loss 감소**나 **분류 Accuracy** 같은 지표는 **로그에 존재하지 않습니다.**

대신 다음을 **결과 지표**로 사용합니다.

| 구분 | 의미 | 본 보고서에서의 위치 |
|------|------|----------------------|
| **추론 지연 (latency)** | 동일 하드웨어에서 1회 합성 소요 시간(ms) | `latency.csv`, §3 표, 아래 그래프 |
| **정성 점수** | 대표 샘플에 대한 주관 평가(1~5) | §4 표; 아래 «정성 종합»은 네 항목 산술평균 |
| **합성 이미지** | 동일 입력에서 Trial만 바꾼 출력 PNG | `scripts/experiments/results/T{n}/p{i}-g{j}.png` |

요청하신 «Loss/Accuracy 변화 추이»에 대응하여, **학습 곡선 대신** (1) **Trial별 평균·p95 지연 추이**, (2) **steps 수와 평균 지연의 관계**, (3) **지연 대비 정성(주관) 트레이드오프**를 그래프로 제시합니다.

---

## 3.2 Trial 통합 비교표 (설정값 + 집계 결과 + 정성 요약)

공통 조건: seed=42, category=`tops`, garment_photo_type=`flat-lay`, 인물 3×의류 3 → Trial당 **n=9**.

| Trial | steps | guidance | n | 평균 지연 (ms) | 중앙값 (ms) | p95 (ms) | 정성 종합¹ (5점) | 서비스 프리셋 매핑 |
|-------|-------|----------|---|----------------|-------------|----------|------------------|-------------------|
| T1 | 18 | 1.20 | 9 | 11837.4 | 11780.8 | 12382.9 | 3.63 | — |
| T2 | 22 | 1.35 | 9 | 14289.6 | 14269.1 | 14381.0 | 3.88 | **fast (빠름)** |
| T3 | 30 | 1.50 | 9 | 19438.9 | 19424.8 | 19557.5 | 4.38 | **default (기본)** |
| T4 | 34 | 1.65 | 9 | 21680.3 | 21652.5 | 21959.7 | 4.38 | — |
| T5 | 40 | 1.80 | 9 | 25347.8 | 25352.7 | 25441.5 | 4.50 | **slow (느림)** |
| T6 | 46 | 2.00 | 9 | 29094.6 | 29098.1 | 29173.6 | 4.50 | — |

¹ §4 정성 표의 네 항목(인물 충실도, 의류 충실도, 경계/아티팩트, 디테일) **산술평균**. 연속적인 «Accuracy»가 아니라 **동일 기준의 주관 스코어**입니다.

---

## 3.3 전체 54회 시도 상세 (설정·결과)

인물 인덱스 **p**, 의류 인덱스 **g** (각 1~3). 출력 파일명: `scripts/experiments/results/{Trial}/p{p}-g{g}.png`.

| Trial | p | g | steps | guidance | latency (ms) | http |
|---:|---:|---:|---:|---:|---:|:---|
| T1 | 1 | 1 | 18 | 1.2 | 12382.9 | 200 |
| T1 | 1 | 2 | 18 | 1.2 | 11720.8 | 200 |
| T1 | 1 | 3 | 18 | 1.2 | 11824.2 | 200 |
| T1 | 2 | 1 | 18 | 1.2 | 11807.7 | 200 |
| T1 | 2 | 2 | 18 | 1.2 | 11722.1 | 200 |
| T1 | 2 | 3 | 18 | 1.2 | 11821.5 | 200 |
| T1 | 3 | 1 | 18 | 1.2 | 11759.0 | 200 |
| T1 | 3 | 2 | 18 | 1.2 | 11717.4 | 200 |
| T1 | 3 | 3 | 18 | 1.2 | 11780.8 | 200 |
| T2 | 1 | 1 | 22 | 1.35 | 14229.4 | 200 |
| T2 | 1 | 2 | 22 | 1.35 | 14293.2 | 200 |
| T2 | 1 | 3 | 22 | 1.35 | 14346.8 | 200 |
| T2 | 2 | 1 | 22 | 1.35 | 14260.0 | 200 |
| T2 | 2 | 2 | 22 | 1.35 | 14269.1 | 200 |
| T2 | 2 | 3 | 22 | 1.35 | 14381.0 | 200 |
| T2 | 3 | 1 | 22 | 1.35 | 14244.7 | 200 |
| T2 | 3 | 2 | 22 | 1.35 | 14239.9 | 200 |
| T2 | 3 | 3 | 22 | 1.35 | 14342.2 | 200 |
| T3 | 1 | 1 | 30 | 1.5 | 19448.9 | 200 |
| T3 | 1 | 2 | 30 | 1.5 | 19379.8 | 200 |
| T3 | 1 | 3 | 30 | 1.5 | 19496.5 | 200 |
| T3 | 2 | 1 | 30 | 1.5 | 19414.1 | 200 |
| T3 | 2 | 2 | 30 | 1.5 | 19424.8 | 200 |
| T3 | 2 | 3 | 30 | 1.5 | 19557.5 | 200 |
| T3 | 3 | 1 | 30 | 1.5 | 19353.6 | 200 |
| T3 | 3 | 2 | 30 | 1.5 | 19390.8 | 200 |
| T3 | 3 | 3 | 30 | 1.5 | 19484.4 | 200 |
| T4 | 1 | 1 | 34 | 1.65 | 21924.6 | 200 |
| T4 | 1 | 2 | 34 | 1.65 | 21959.7 | 200 |
| T4 | 1 | 3 | 34 | 1.65 | 21870.3 | 200 |
| T4 | 2 | 1 | 34 | 1.65 | 21497.0 | 200 |
| T4 | 2 | 2 | 34 | 1.65 | 21561.3 | 200 |
| T4 | 2 | 3 | 34 | 1.65 | 21652.5 | 200 |
| T4 | 3 | 1 | 34 | 1.65 | 21486.2 | 200 |
| T4 | 3 | 2 | 34 | 1.65 | 21515.3 | 200 |
| T4 | 3 | 3 | 34 | 1.65 | 21655.7 | 200 |
| T5 | 1 | 1 | 40 | 1.8 | 25298.5 | 200 |
| T5 | 1 | 2 | 40 | 1.8 | 25369.4 | 200 |
| T5 | 1 | 3 | 40 | 1.8 | 25366.5 | 200 |
| T5 | 2 | 1 | 40 | 1.8 | 25352.7 | 200 |
| T5 | 2 | 2 | 40 | 1.8 | 25295.0 | 200 |
| T5 | 2 | 3 | 40 | 1.8 | 25323.6 | 200 |
| T5 | 3 | 1 | 40 | 1.8 | 25330.0 | 200 |
| T5 | 3 | 2 | 40 | 1.8 | 25353.0 | 200 |
| T5 | 3 | 3 | 40 | 1.8 | 25441.5 | 200 |
| T6 | 1 | 1 | 46 | 2.0 | 29144.2 | 200 |
| T6 | 1 | 2 | 46 | 2.0 | 29047.2 | 200 |
| T6 | 1 | 3 | 46 | 2.0 | 29131.8 | 200 |
| T6 | 2 | 1 | 46 | 2.0 | 29098.9 | 200 |
| T6 | 2 | 2 | 46 | 2.0 | 29036.2 | 200 |
| T6 | 2 | 3 | 46 | 2.0 | 29173.6 | 200 |
| T6 | 3 | 1 | 46 | 2.0 | 29098.1 | 200 |
| T6 | 3 | 2 | 46 | 2.0 | 29036.2 | 200 |
| T6 | 3 | 3 | 46 | 2.0 | 29085.3 | 200 |

원본 CSV: `scripts/experiments/results/latency.csv` — 재실행 시 `python scripts/experiments/run_matrix.py` 로 갱신 가능.

---

## 3.4 그래프 (시각 자료)

GitHub에서 깨지지 않도록 **`main` 브랜치 raw URL**로 삽입했습니다. 로컬에서는 `docs/experiments/figures/` 동일 파일을 보면 됩니다.

**Trial별 평균·p95 추론 지연 (초)**

![Trial별 평균 및 p95 지연](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/docs/experiments/figures/latency_mean_p95_by_trial.png)

**확산 스텝 수와 평균 지연** — 스텝을 늘리면 한 장 합성에 필요한 반복 연산이 늘어 지연이 증가하는 패턴이 선형에 가깝게 나타납니다.

![steps vs 평균 지연](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/docs/experiments/figures/steps_vs_latency.png)

**지연 vs 정성 종합(주관 프록시)** — 학습 Accuracy 곡선의 대안으로, «느릴수록 주관 품질 여유가 생기지만 포화 구간이 있다»는 점을 한눈에 비교합니다.

![지연 vs 정성 종합](https://raw.githubusercontent.com/kwakminoo/AI-Fitting-Web/main/docs/experiments/figures/quality_latency_tradeoff.png)

그래프 재생성: `python scripts/experiments/plot_report_figures.py`

---

## 3.5 변화 원인 분석 (왜 성능·체감이 바뀌는가)

1. **지연(latency)이 Trial마다 달라진 이유**  
   FASHN VTON 추론에서 `num_timesteps`(확산 스텝)가 커질수록 **한 번의 합성에 수행하는 역확산 반복 횟수**가 늘어납니다. 동일 GPU·동일 파이프라인에서 이는 **연산량 증가 → wall-clock 시간 증가**로 직결되며, 본 실험에서도 T1(18스텝)부터 T6(46스텝)까지 **평균 지연이 단조 증가**합니다. `guidance_scale`을 함께 올린 Trial은 조건(의류) 쪽으로 더 강하게 끌어당기는 설정이라, 구현·스케줄에 따라 **추가 연산/수렴 비용**에 소폭 기여할 수 있습니다.

2. **«품질·정확도»를 어떻게 해석할 것인가**  
   분류 모델의 **Accuracy**처럼 단일한 정답 라벨이 있는 것이 아니라, 생성 결과는 **인간 시각 기준의 유사도·자연스러움**으로 평가됩니다. §4의 정성 점수는 이를 **고정 루브릭(인물/의류/경계/디테일)** 으로 숫자화한 것이며, **Trial 간 상대 비교**에는 유용하지만 **절대적인 분류 정확도**와 동치는 아닙니다.

3. **정성이 유의미하게 나아진 구간 vs 포화 구간**  
   스텝·가이던스가 낮은 T1은 속도는 가장 빠르지만, 프린트 경계·디테일에서 불안정해 보일 여지가 있습니다. T2~T3 구간에서 **로고 형태·색 분리** 등이 비교적 안정적으로 보이고, T4 이후는 **미세한 개선**이 있으나 §4에서도 서술했듯 **T3 대비 체감 차이는 제한적**인 경우가 많습니다. 반면 지연은 T5→T6까지도 계속 증가해, **품질 대비 비용**이 불리해질 수 있습니다.

4. **프리셋(fast/default/slow) 선정과의 연결**  
   위 분석을 반영해 **fast=T2, default=T3, slow=T5**로 두면, 각각 **지연–품질 트레이드오프**에서 의미 있는 구간(빠름 / 균형 / 품질 우선)을 사용자 선택으로 노출할 수 있습니다. T6는 지연만 크게 늘고 주관 점수 상으로는 T5와 같은 구간에 머무는 경우가 있어, 서비스 프리셋에서는 **생략**하는 것이 합리적입니다.

---

## 4. 정성 평가 (대표 셀: p1-g1, 시각 검토 요약)

상단 **「출력 비교」** 이미지(T1/T3/T6, T2/T3/T5)와 함께 보면 Trial·프리셋별 차이를 바로 대조할 수 있습니다.

- **T1:** 가장 빠르나 프린트 가장자리·소매 경계가 T3~T6 대비 다소 거칠게 느껴질 수 있음.
- **T2~T3:** 로고 형태·색 분리가 안정적으로 보이는 구간; T3가 디테일/경계에서 약간 더 정돈된 인상.
- **T4~T6:** 미세 패턴·경계는 추가로 매끈해지는 경우가 있으나, 동일 셀 기준 체감 차이는 T3 대비 크지 않은 경우가 많고 지연은 선형에 가깝게 증가.

**종합(1~5 스케일, 대표 샘플 기준):**

| Trial | 인물 충실도 | 의류 충실도 | 경계/아티팩트 | 디테일 | 체감 코멘트 |
|-------|-------------|-------------|----------------|--------|-------------|
| T1 | 4 | 3.5 | 3 | 3.5 | 속도 최우선 시 허용 |
| T2 | 4 | 4 | 3.5 | 4 | 빠른 프리셋으로 균형 양호 |
| T3 | 4.5 | 4.5 | 4 | 4.5 | 기본 추천 |
| T4 | 4.5 | 4.5 | 4 | 4.5 | T3 대비 이득 대비 비용 증가 |
| T5 | 4.5 | 4.5 | 4.5 | 4.5 | 품질 우선 시 |
| T6 | 4.5 | 4.5 | 4.5 | 4.5 | T5 대비 체감 이득 제한적 |

## 5. 최종 프리셋 선정 (`backend/services/fashn_vton.py`)

| 프리셋 | steps | guidance | 매핑 Trial | 선정 근거 |
|--------|-------|----------|------------|-----------|
| **fast** | 22 | 1.35 | **T2** | T1 대비 품질 여유, T3 대비 ~5s 절감 |
| **default** | 30 | 1.50 | **T3** | 정성·지연 균형, 실험 매트릭스 중심값 |
| **slow** | 40 | 1.80 | **T5** | T6 대비 지연 증가 대비 체감 품질 이득이 제한적이라 T5에서 정지 |

seed는 계획대로 **42 고정**(코드 및 UI 요청과 일치).

## 6. 운영 메모

- **행 매트릭스 재실행:** `python scripts/experiments/run_matrix.py` (전체 덮어쓰기)  
- **중단 후 이어하기:** `python scripts/experiments/run_matrix.py --resume` (동일 `latency.csv`·PNG가 있으면 해당 조합 스킵)
- **HTTP 모드:** `python scripts/experiments/run_matrix.py --http` (백엔드 `/health`의 `fashn_ready=true` 필요)
- **보고서 그래프:** `pip install matplotlib` 후 `python scripts/experiments/plot_report_figures.py` — `docs/experiments/figures/*.png` 갱신
- **54회 상세 표 갱신:** `latency.csv` 변경 뒤 `python scripts/experiments/export_54runs_md_table.py` 로 조각 생성(필요 시 §3.3에 반영)

## 7. 스모크 테스트 (UI E2E 체크리스트)

백엔드 기동 후 `web`에서 다음 각 1회씩 확인:

1. **상의 + 기본** — 단일 의류 드롭, 결과 정상.
2. **하의 + 빠름** — 하의 카테고리, 지연 감소 체감.
3. **전신 + 느림** — 상의/하의 드롭 2칸, 2단 체인 결과 정상.
4. **원피스 + 기본** — 단일 의류, `one-pieces` 경로 정상.

각 요청에 `category` / `speed_preset` / (전신 시) `cloth_img2`가 포함되는지 네트워크 탭에서 검증.

## 8. Before / After (의미)

- **Before:** 단일 고정 하이퍼파라미터로만 추론.
- **After:** 사용자가 빠름/기본/느림을 선택하면 **T2 / T3 / T5에 대응하는 steps·guidance**가 요청 단위로 주입되며, 전신 모드는 상의→하의 2단 체인으로 동작.

---

*본 리포트의 정성 점수는 대표 샘플 시각 검토에 기반한 공학적 추정이며, 제품 기준 확정 시 추가 블라인드 평가를 권장합니다.*

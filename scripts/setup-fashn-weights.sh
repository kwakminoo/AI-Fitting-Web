#!/usr/bin/env bash
# FASHN VTON v1.5 사전학습 가중치를 backend/weights(또는 FASHN_WEIGHTS_DIR)에 다운로드합니다.
# 사용: ./scripts/setup-fashn-weights.sh
# 요구: git, python 3.10+, huggingface 접근 가능 네트워크

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEIGHTS_DIR="${FASHN_WEIGHTS_DIR:-$ROOT/backend/weights}"
TMP="${TMPDIR:-/tmp}/fashn-vton-weights-$$"

mkdir -p "$(dirname "$WEIGHTS_DIR")"
git clone --depth 1 https://github.com/fashn-AI/fashn-vton-1.5.git "$TMP"
python "$TMP/scripts/download_weights.py" --weights-dir "$WEIGHTS_DIR"
rm -rf "$TMP"
echo "가중치 저장 완료: $WEIGHTS_DIR"
echo "backend/.env 에 FASHN_WEIGHTS_DIR=$WEIGHTS_DIR 설정을 권장합니다."

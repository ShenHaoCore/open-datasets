#!/usr/bin/env bash
#
# 重建 cn-divisions 数据集。
#
# 依赖：Node.js ≥18、Python ≥3.10。版本以 build/package.json 为准。
#
#   ./build/build.sh              # 重建并写回数据集根目录
#   ./build/build.sh --check      # 只校验现有文件可复现，不写回
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PYTHON="${PYTHON:-python}"

npm install --silent --no-audit --no-fund
node extract-upstream.mjs
"$PYTHON" generate.py "$@"

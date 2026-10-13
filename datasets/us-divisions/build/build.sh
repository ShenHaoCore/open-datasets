#!/usr/bin/env bash
#
# 重建 us-divisions 数据集。
#
# 依赖：Python ≥3.10。州事实源与县级码表锁定在 build/。
#
#   ./build/build.sh              # 重建并写回数据集根目录
#   ./build/build.sh --check      # 只校验现有文件可复现，不写回
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

PYTHON="${PYTHON:-python}"
"$PYTHON" generate.py "$@"

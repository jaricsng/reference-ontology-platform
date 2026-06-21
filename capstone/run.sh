#!/usr/bin/env bash
# Run the Spark capstone (uses JDK 17 — Spark does not support JDK 26).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"

export JAVA_HOME="${JAVA_HOME:-/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export PYSPARK_PYTHON="$REPO/.venv/bin/python"

echo "JAVA_HOME=$JAVA_HOME"
exec "$REPO/.venv/bin/python" "$DIR/spark_capstone.py"

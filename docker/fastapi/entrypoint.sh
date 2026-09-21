#!/bin/bash
set -e

export BUILD_ENV="${BUILD_ENV:-local}"

echo "[$(date)] 🚀 Running Entrypoint in ${BUILD_ENV} mode..."

exec "$@"

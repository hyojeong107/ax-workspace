#!/bin/bash
set -e

echo "FitStep Multi-Agent API 시작..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

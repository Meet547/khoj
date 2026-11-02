#!/bin/sh
set -eu
# Enable during deployment to warm private R2 before the API accepts traffic.
if [ "${KHOJ_PREGEN_TTS:-0}" = "1" ]; then
  python scripts/pregen_tts.py --langs "${KHOJ_TTS_LANGS:-en,hi}"
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --no-proxy-headers

#!/usr/bin/env bash
set -e

python -m uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000 &
API_PID=$!

for i in $(seq 1 60); do
  if python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).status == 200 else 1)" 2>/dev/null; then
    echo "API is up"
    break
  fi
  sleep 2
done

trap "kill $API_PID" EXIT

exec python -m streamlit run src/examora_chat.py \
  --server.port "${STREAMLIT_SERVER_PORT:-7860}" \
  --server.address 0.0.0.0 \
  --server.headless true

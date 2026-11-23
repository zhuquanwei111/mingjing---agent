#!/usr/bin/env bash
set -euo pipefail
model_container="$P2_PROJECT-inference"
ollama_image=ollama/ollama@sha256:a5409cb903d30f9cd67e9f430dd336ddc9274e16fd78f75b675c42065991b4fd
docker pull "$ollama_image" >/dev/null
docker run -d --name "$model_container" -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_KEEP_ALIVE=15m "$ollama_image" >/dev/null
trap 'docker rm -f "$model_container" >/dev/null 2>&1 || true; cleanup' EXIT
for i in $(seq 1 45); do
  if docker exec "$model_container" ollama list >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$model_container" ollama pull qwen2.5:1.5b >"$RUNNER_TEMP/model-pull.txt" 2>&1 || { tail -c 700 "$RUNNER_TEMP/model-pull.txt"; exit 1; }
docker network connect --alias lab-model "${P2_PROJECT}_default" "$model_container"
docker network disconnect bridge "$model_container"
docker image inspect "$ollama_image" --format 'INFERENCE_IMAGE {{index .RepoDigests 0}}'
dc run --rm -T --no-deps test python -c "import json,urllib.request;d=json.load(urllib.request.urlopen('http://lab-model:11434/api/tags'))['models'][0]['digest']; print('INFERENCE_WEIGHTS',d); assert d=='65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b'"

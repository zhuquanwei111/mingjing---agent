#!/usr/bin/env bash
set -euo pipefail
model_container="$P2_PROJECT-inference"
ollama_image=ollama/ollama:0.11.10
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
dc run --rm -T --no-deps test python -c "import json,urllib.request;print('INFERENCE_WEIGHTS',json.load(urllib.request.urlopen('http://lab-model:11434/api/tags'))['models'][0]['digest'])"

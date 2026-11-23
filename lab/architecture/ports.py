"""HTTP wire client and interfaces belonging to the neutral laboratory."""
import json
import os
from urllib.request import Request, urlopen

FIXTURE = "http://127.0.0.1:8765"
TOKEN = os.environ.get("LAB_TOKEN", "")

def request(url, data, headers=None):
    req = Request(url, json.dumps(data).encode(), headers={"Content-Type":"application/json", **(headers or {})})
    with urlopen(req, timeout=90) as res:
        return json.load(res)

def sink(case, action, data=None):
    return request(FIXTURE + "/event", {"case":case,"action":action,"data":data or {}})

def barrier(case, name):
    return request(FIXTURE + "/barrier", {"case":case,"name":name})

def model_http(case, backend, messages, tools):
    payload = {"model":"qwen2.5:1.5b","messages":messages,"temperature":0,"max_tokens":160}
    if tools:
        payload["tools"] = tools
    result = request(f"{FIXTURE}/{case}/{backend}/v1/chat/completions",payload)
    return result["choices"][0]["message"]

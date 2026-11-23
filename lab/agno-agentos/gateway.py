"""Govern model bytes at a separate, trusted test egress process."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from control import authorized

app = FastAPI()


@app.post("/{scope}/v1/chat/completions")
def model(scope: str, body: dict):
    try:
        status, data = authorized(scope, "v1/chat/completions", body)
    except PermissionError:
        return JSONResponse({"error": "access revoked"}, status_code=403)
    return JSONResponse(data, status_code=status)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8091, log_level="error")

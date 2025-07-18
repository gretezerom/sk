from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import httpx, os

app = FastAPI()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")          # Railway → Variables

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
)

# ───────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def chat(req: Request, authorization: str = Header(None)):
    # ── 解析 / 校验 sk-key ───────────────────────────
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        auth = auth.split(" ", 1)[1]              # 允许 Bearer sk-xxx

    if not auth.startswith("sk-"):
        return JSONResponse({"error": "invalid key"}, status_code=401)

    # ── 组装 prompt ─────────────────────────────────
    data = await req.json()
    prompt = "\n".join(
        m["content"] for m in data.get("messages", []) if m["role"] == "user"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    # ── 调 Gemini API ──────────────────────────────
    async with httpx.AsyncClient() as c:
        r = await c.post(API_URL, json=payload, timeout=40)

    data = r.json()                # Google 返回的原始 JSON

    if r.status_code != 200 or "candidates" not in data:
        # 直接把 Google 的错误透给前端
        return JSONResponse(data, status_code=r.status_code)

    answer = data["candidates"][0]["content"]["parts"][0]["text"]

    # ── 返回 OpenAI 兼容结构 ─────────────────────────
    return {
        "id": "chatcmpl-gemini",
        "object": "chat.completion",
        "created": 0,
        "model": "gemini-2.5-pro",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }

# ── 兼容无 /v1 及尾斜杠写法 ───────────────────────
@app.post("/v1/chat/completions/")
@app.post("/chat/completions")
@app.post("/chat/completions/")
async def chat_alias(req: Request, authorization: str = Header(None)):
    return await chat(req, authorization)

# ── /v1/models 与 /models 让健康检查通过 ────────────
model_payload = {
    "object": "list",
    "data": [{
        "id": "gemini-2.5-pro",
        "object": "model",
        "created": 0,
        "owned_by": "google"
    }]
}

@app.get("/v1/models")
def list_models_v1():
    return model_payload

@app.get("/models")
@app.get("/models/")
def list_models_root():
    return model_payload

# ── 本地 / Railway 运行入口 ─────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 7860)))

from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import httpx, os

app = FastAPI()
# 加在 app = FastAPI() 下面
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 任何域都能访问
    allow_methods=["*"],
    allow_headers=["*"],
)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")          # Railway → Variables.

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
)

# ───────────────────────────────────────────────
async def call_gemini(prompt: str):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        async with httpx.AsyncClient(http2=True, timeout=None) as c:
            r = await c.post(API_URL, json=payload)
    except Exception as e:
        # 网络 / TLS / DNS 错误
        print("Gemini network error:", repr(e))
        return None, JSONResponse({"error": str(e)}, status_code=502)

    data = r.json()
    if r.status_code != 200 or "candidates" not in data:
        # 把 Google 的业务错误直接透给前端
        return None, JSONResponse(data, status_code=r.status_code)

    answer = data["candidates"][0]["content"]["parts"][0]["text"]
    return answer, None

# ── 主路由 ─────────────────────────────────────────
@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/")
@app.post("/chat/completions")
@app.post("/chat/completions/")
@app.post("/chat/completion")
@app.post("/chat/completion/")
async def chat(req: Request, authorization: str = Header(None)):
    # ── 校验 sk-key ────────────────────────────────
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        auth = auth.split(" ", 1)[1]

    if not auth.startswith("sk-"):
        return JSONResponse({"error": "invalid key"}, status_code=401)

    # ── 提取用户 prompt ────────────────────────────
    body = await req.json()
    prompt = "\n".join(
        m["content"] for m in body.get("messages", []) if m["role"] == "user"
    )

    answer, error_resp = await call_gemini(prompt)
    if error_resp:
        return error_resp

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

# ── /models 让健康检查通过 ────────────────────────
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
@app.get("/models")
@app.get("/models/")
def list_models():
    return model_payload

# ── 主页 ping ─────────────────────────────────────
@app.get("/")
def ping():
    return {"status": "ok"}

# ── 本地 / Railway 运行入口 ───────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

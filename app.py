from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import httpx, os

app = FastAPI()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")          # Railway → Variables

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
)

@app.post("/v1/chat/completions")
async def chat(req: Request, authorization: str = Header(None)):
    # ── 校验并提取 sk-key ───────────────────────────────
    auth = (authorization or "").strip()
    if auth.lower().startswith("bearer "):
        auth = auth.split(" ", 1)[1]              # 允许  Bearer sk-xxx

    if not auth.startswith("sk-"):
        return JSONResponse({"error": "invalid key"}, status_code=401)

    # ── 解析用户消息成单一 prompt ───────────────────────
    data = await req.json()
    prompt = "\n".join(
        m["content"] for m in data.get("messages", []) if m["role"] == "user"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    # ── 调 Gemini API ─────────────────────────────────
    async with httpx.AsyncClient() as c:
    r = await c.post(API_URL, json=payload, timeout=40)

data = r.json()

# 若 Google 返回 error，直接转给前端
if r.status_code != 200 or "candidates" not in data:
    return JSONResponse(data, status_code=r.status_code)

answer = data["candidates"][0]["content"]["parts"][0]["text"]

    # ── 返回 OpenAI 兼容结构 ───────────────────────────
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

# ── /v1/models 让 SillyTavern 健康检查通过 ──────────────
@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [{"id": "gemini-2.5-pro", "object": "model"}]
    }

# ── 本地运行（Railway 会注入 $PORT）───────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 7860)))

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

@app.get("/models")          # 兼容老端点
def list_models_root():
    return model_payload
    # 兼容末尾带 / 以及没有 v1 的写法
@app.post("/v1/chat/completions/")
@app.post("/chat/completions")
@app.post("/chat/completions/")
async def chat_alias(request: Request, authorization: str = Header(None)):
    return await chat(request, authorization)   # 复用主函数

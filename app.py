from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import httpx, os

app = FastAPI()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")   # 在 HF Secrets 里填 AIzaSy… 那串

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1/models/gemini-2.5-pro:generateContent?key={GEMINI_KEY}"
)

@app.post("/v1/chat/completions")
async def chat(req: Request, authorization: str = Header(None)):
    # 只检查 sk- 前缀即可
    auth = (authorization or "").strip()

# 允许两种写法：Bearer sk-xxx   或   sk-xxx
if auth.lower().startswith("bearer "):
    auth = auth.split(" ", 1)[1]

if not auth.startswith("sk-"):
    return JSONResponse(status_code=401, content={"error": "invalid key"})

    data = await req.json()
    prompt = "\n".join(m["content"] for m in data.get("messages", []) if m["role"] == "user")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    async with httpx.AsyncClient() as c:
        r = await c.post(API_URL, json=payload, timeout=40)

    if r.status_code != 200:
        return JSONResponse(r.json(), status_code=r.status_code)

    answer = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    return {
        "id": "chatcmpl-gemini",
        "object": "chat.completion",
        "created": 0,
        "model": "gemini-pro",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
    # --- 以下 4 行新增 ---
if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 7860)))

# 让 SillyTavern 能拿到模型列表，避免 Status Check 失败
@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "gemini-2.5-pro",
                "object": "model",
            }
        ]
    }

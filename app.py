from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import httpx, os

app = FastAPI()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")   # 在 HF Secrets 里填 AIzaSy… 那串

API_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1/models/gemini-pro:generateContent?key={GEMINI_KEY}"
)

@app.post("/v1/chat/completions")
async def chat(req: Request, authorization: str = Header(None)):
    # 只检查 sk- 前缀即可
    if not (authorization or "").startswith("Bearer sk-"):
        return JSONResponse({"error": "invalid key"}, status_code=401)

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

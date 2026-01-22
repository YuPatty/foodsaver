from openai import OpenAI
import os

# Simple wrapper for OpenRouter Chat Completions via openai-python client.
# Reads API key from environment: OPENROUTER_API_KEY
# Optional: OPENROUTER_MODEL (default: meta-llama/llama-3.3-8b-instruct:free)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

def _client():
    api_key = ""
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    # Allow both plain key or 'Bearer ...' format; normalize to plain
    if api_key.lower().startswith("bearer "):
        api_key = api_key.split(" ", 1)[1]
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

# 固定問答（可自行擴充；比對時我會做小寫與去空白）
QA_MAP = {
    "你好": "hi",
    "你是誰": "我是你的ai助理~",
    "今天晚餐吃甚麼?": "現在離你最近的7-11 忠孝店有在特價雞肉便當，推薦你可以去買來吃!",
    "幫我搭配健康又便宜的晚餐!": "根據你的喜好清單以及網路上各家商店的特價項目，我推薦以下搭配:主食選擇玉米、蔬菜選擇沙拉、飲料選擇牛奶，可以在離你最近的7-11 忠孝店買到打折的品項，這是最適合你的健康飲食!"
}

def ask_model(question: str, referer: str = "", title: str = "") -> str:
    """
    Returns a reply string. If question matches QA_MAP (case-insensitive), returns mapped answer.
    Otherwise, calls the model.
    """
    if not question or not question.strip():
        return "（問題是空的）"
    q_norm = question.lower().strip()
    if q_norm in QA_MAP:
        return QA_MAP[q_norm]

    cl = _client()
    extra_headers = {}
    if referer:
        extra_headers["HTTP-Referer"] = referer
    if title:
        extra_headers["X-Title"] = title

    resp = cl.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": question}],
        extra_headers=extra_headers or None,
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        return str(resp)

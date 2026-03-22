import os
from pathlib import Path

from google import genai
from google.genai import types
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import rag

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. Create backend/.env with:\n"
        "GEMINI_API_KEY=your_key_here"
    )

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-1.5-flash"

# ---------------------------------------------------------------------------
# Load knowledge base once at startup
# ---------------------------------------------------------------------------
KB_DIR = Path(__file__).parent.parent / "knowledge_base"
chunks = rag.load_knowledge_base(str(KB_DIR))
print(f"[RAG] Loaded {len(chunks)} chunks from {KB_DIR}")

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Kamu adalah Pajak Assistant, asisten AI yang tertanam di portal Coretax milik Direktorat Jenderal Pajak (DJP) Indonesia.

Tugas kamu:
- Membantu Wajib Pajak memahami kewajiban pajak mereka dengan bahasa yang mudah dimengerti
- Menjawab pertanyaan HANYA berdasarkan konteks yang disediakan di bawah
- Jika pertanyaan tidak tercakup dalam konteks, katakan kamu tidak memiliki informasi tersebut dan sarankan menghubungi DJP di 1500-200 atau mengunjungi KPP terdekat

Aturan penting:
- Jawab dalam bahasa yang sama dengan pertanyaan pengguna (Bahasa Indonesia jika mereka menulis dalam bahasa Indonesia, English jika mereka menulis dalam English)
- Gunakan langkah bernomor saat menjelaskan prosedur
- Bersikap ramah, jelas, dan ringkas
- Jangan mengarang informasi yang tidak ada di konteks
- Selalu sebutkan deadline penting jika relevan

KONTEKS PENGETAHUAN:
{context}
"""

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Coretax Buddy")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    sources: list[str]


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        # 1. Retrieve relevant context
        relevant_chunks = rag.retrieve(req.message, chunks, top_k=3)
        context_str = rag.build_context(relevant_chunks)
        sources = list({c["source"] for c in relevant_chunks})

        # 2. Build system prompt with context injected
        system_with_context = SYSTEM_PROMPT.format(context=context_str)

        # 3. Build conversation contents from history (last 6 turns)
        trimmed_history = req.history[-6:]
        contents = []
        for turn in trimmed_history:
            role = "user" if turn.get("role") == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=turn.get("content", ""))]
            ))

        # 4. Append current user message with system context injected
        full_user_message = f"{system_with_context}\n\nPertanyaan pengguna: {req.message}"
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=full_user_message)]
        ))

        # 5. Call Gemini
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
        )

        return ChatResponse(reply=response.text, sources=sources)

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Maaf, terjadi kesalahan pada layanan AI. Silakan coba lagi. ({str(e)})"
        )


# ---------------------------------------------------------------------------
# Serve frontend as static files
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import chat

app = FastAPI(
    title="ESCA HSE AI Agent Service",
    description="MySQL-backed LLM Agent with Groq integration and function calling.",
    version="1.0.0"
)

# Include Chat & Agent Routes
app.include_router(chat.router)

# Serve prototype UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse("static/index.html")

@app.get("/health")
def health_check():
    return {"status": "ok", "engine": "MySQL", "llm": "Groq"}
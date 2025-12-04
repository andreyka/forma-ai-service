"""Main entry point for the FormaAI API service.

This module initializes the FastAPI application, configures middleware,
serves static files, and includes the A2A router.
"""

import os
# Suppress tokenizers warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import logging
# Suppress Gemini warnings
logging.getLogger("tornado.access").setLevel(logging.ERROR)
logging.getLogger("google.generativeai").setLevel(logging.ERROR)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from tools.rag_tool import RAGTool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the application lifespan.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    # Startup: Ingest docs if needed
    print("Startup: Checking RAG database...")
    rag = RAGTool()
    await rag.ingest_docs()
    yield
    # Shutdown: Clean up if needed (optional)

app = FastAPI(title="FormaAI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow anonymous origin. Currently, there is no authentication.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the outputs directory so files can be downloaded
os.makedirs("outputs", exist_ok=True)
app.mount("/download", StaticFiles(directory="outputs"), name="outputs")

# --- A2A Protocol Implementation ---
from a2a.api import router as a2a_router

app.include_router(a2a_router)

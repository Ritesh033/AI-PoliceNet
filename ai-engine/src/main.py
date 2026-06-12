"""AI PoliceNet - AI Engine Service

FastAPI application serving AI models for:
- NLP: Complaint analysis, threat detection, hate speech classification
- Computer Vision: Violence detection, object detection, anomaly detection
- Audio: Speech-to-text, threat identification, voice analysis
- Evidence: Authenticity verification, deepfake detection
- Risk: Scoring engine, recommendation engine
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .routers import nlp, computer_vision, audio, evidence_ai, risk, health


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ai-engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading AI models...")
    # TODO: Pre-load models into memory
    yield
    logger.info("Shutting down AI engine...")


app = FastAPI(
    title="AI PoliceNet - AI Engine",
    description="AI-powered analysis engine for law enforcement support",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(nlp.router, prefix="/ai/nlp", tags=["NLP"])
app.include_router(computer_vision.router, prefix="/ai/cv", tags=["Computer Vision"])
app.include_router(audio.router, prefix="/ai/audio", tags=["Audio Analysis"])
app.include_router(evidence_ai.router, prefix="/ai/evidence", tags=["Evidence AI"])
app.include_router(risk.router, prefix="/ai/risk", tags=["Risk Analysis"])

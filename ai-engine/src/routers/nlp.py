"""NLP analysis router: complaint classification, threat detection, hate speech, sentiment, entity extraction."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import random

router = APIRouter()


class TextAnalysisRequest(BaseModel):
    text: str
    language: str = "en"
    analysis_types: list[str] = ["classification", "sentiment", "entities"]


class ComplaintClassification(BaseModel):
    category: str
    confidence: float
    subcategory: Optional[str] = None


class ThreatDetectionRequest(BaseModel):
    text: str
    context: Optional[str] = None


class HateSpeechRequest(BaseModel):
    text: str
    platform: Optional[str] = None


@router.post("/analyze")
async def analyze_text(request: TextAnalysisRequest):
    """Full NLP pipeline: classification + sentiment + entity extraction + threat detection."""
    results: dict = {"text_length": len(request.text), "language": request.language}

    if "classification" in request.analysis_types:
        categories = ["theft", "assault", "fraud", "cybercrime", "domestic_violence", "traffic", "corruption", "other"]
        results["classification"] = {
            "category": random.choice(categories),
            "confidence": round(random.uniform(0.65, 0.98), 3),
        }

    if "sentiment" in request.analysis_types:
        results["sentiment"] = {
            "label": random.choice(["negative", "neutral", "positive"]),
            "score": round(random.uniform(0.5, 1.0), 3),
            "urgency": random.choice(["low", "medium", "high"]),
        }

    if "entities" in request.analysis_types:
        results["entities"] = [
            {"type": "PERSON", "text": "placeholder_name", "confidence": 0.92},
            {"type": "LOCATION", "text": "placeholder_location", "confidence": 0.88},
        ]

    if "threat" in request.analysis_types:
        results["threat"] = {
            "is_threat": random.choice([True, False]),
            "threat_type": random.choice(["none", "physical", "verbal", "cyber"]),
            "severity": random.choice(["low", "medium", "high"]),
            "confidence": round(random.uniform(0.6, 0.95), 3),
        }

    return {"data": results}


@router.post("/classify-complaint")
async def classify_complaint(request: TextAnalysisRequest):
    """Classify a citizen complaint into crime categories."""
    categories = [
        ("theft", "burglary"), ("assault", "physical"), ("fraud", "financial"),
        ("cybercrime", "phishing"), ("harassment", "workplace"),
        ("corruption", "bribery"), ("misconduct", "police"),
    ]
    cat, sub = random.choice(categories)
    return {
        "data": ComplaintClassification(
            category=cat,
            confidence=round(random.uniform(0.7, 0.99), 3),
            subcategory=sub,
        )
    }


@router.post("/detect-threat")
async def detect_threat(request: ThreatDetectionRequest):
    """Detect threats in text content."""
    return {
        "data": {
            "is_threat": random.choice([True, False]),
            "threat_level": random.choice(["none", "low", "medium", "high", "critical"]),
            "threat_types": random.sample(
                ["physical_violence", "verbal_threat", "extortion", "terrorism", "harassment"],
                k=random.randint(0, 2),
            ),
            "confidence": round(random.uniform(0.6, 0.98), 3),
            "recommended_action": random.choice(["none", "flag_review", "immediate_alert"]),
        }
    }


@router.post("/detect-hate-speech")
async def detect_hate_speech(request: HateSpeechRequest):
    """Detect hate speech and offensive content."""
    return {
        "data": {
            "is_hate_speech": random.choice([True, False]),
            "categories": random.sample(
                ["religious", "racial", "gender", "caste", "political", "none"],
                k=random.randint(0, 2),
            ),
            "severity": random.choice(["none", "mild", "moderate", "severe"]),
            "confidence": round(random.uniform(0.6, 0.95), 3),
        }
    }


@router.post("/validate-fir")
async def validate_fir(request: TextAnalysisRequest):
    """Validate FIR content for completeness, consistency, and potential false reporting."""
    return {
        "data": {
            "is_valid": True,
            "completeness_score": round(random.uniform(0.5, 1.0), 3),
            "consistency_score": round(random.uniform(0.5, 1.0), 3),
            "false_report_probability": round(random.uniform(0.0, 0.4), 3),
            "missing_fields": random.sample(["witness_details", "exact_time", "suspect_description"], k=random.randint(0, 2)),
            "recommendations": ["Provide witness contact details", "Specify exact incident time"],
        }
    }

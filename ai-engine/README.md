# AI Engine

AI/ML processing pipeline for AI PoliceNet. All models assist human decision-making; they do not make autonomous legal decisions.

## Modules

### Analysis Modules
| Module | Purpose |
|--------|---------|
| complaint-analysis | Categorize and prioritize citizen complaints |
| fir-validation | Validate FIR completeness and consistency |
| false-report-detection | Detect potentially false reports and FIRs |
| officer-misconduct-analysis | Pattern detection in officer complaints |
| citizen-risk-analysis | Assess risk levels for citizen safety |
| social-media-analysis | Analyze social media content for threats |

### NLP Engine
- **Text Classification**: Categorize text content
- **Threat Detection**: Identify threatening language
- **Hate Content Detection**: Flag hate speech and incitement
- **Sentiment Analysis**: Gauge emotional tone
- **Entity Extraction**: Extract names, locations, dates, organizations

### Computer Vision
- **Object Detection**: General object detection (YOLOv8)
- **Violence Detection**: Detect violent content in video/images
- **Railway Risk Detection**: Detect dangerous railway stunts
- **Crowd Analysis**: Crowd density and behavior estimation
- **Vehicle Analysis**: License plate recognition and vehicle tracking
- **Anomaly Detection**: Detect unusual patterns in surveillance

### Audio Analysis
- **Speech-to-Text**: Transcribe audio evidence (Whisper)
- **Threat Identification**: Detect threatening audio content
- **Voice Analysis**: Speaker identification and verification

### Supporting Engines
- **Recommendation Engine**: Suggest investigation steps and resources
- **Risk Scoring Engine**: Calculate risk scores for cases and content
- **Evidence Authentication**: Verify evidence integrity and metadata
- **Deepfake Detection**: Detect manipulated media (images, video, audio)
- **Fraud Detection**: Detect fraudulent claims and patterns
- **Model Serving**: Production model deployment (TorchServe / TF Serving)

## Tech Stack
- Python 3.10+
- PyTorch / TensorFlow
- FastAPI for model serving
- OpenCV for computer vision
- Hugging Face Transformers for NLP
- Whisper for speech-to-text
- Apache Kafka for stream processing

## Getting Started

```bash
cd ai-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn model-serving.app:app --host 0.0.0.0 --port 8000
```

## Ethical Guidelines
- Models provide probability scores, not verdicts
- All high-risk decisions require human confirmation
- Regular bias audits across demographics
- Model explanations (SHAP/LIME) for transparency
- No facial recognition for mass surveillance

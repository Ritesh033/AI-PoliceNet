# Research

Research and development for AI PoliceNet's machine learning models.

## Directory Structure
```
research/
├── datasets/        # Training and evaluation datasets
├── model-training/  # Training scripts and configs
├── experiments/     # Experiment logs and results
├── benchmarks/      # Performance benchmarks
└── whitepapers/     # Research papers and documentation
```

## Active Research Areas
- False report detection accuracy improvement
- Multilingual NLP (Hindi + regional Indian languages)
- Real-time violence detection in video streams
- Railway safety risk detection
- Deepfake detection for evidence verification
- Hate speech detection in Indian social media context
- Officer misconduct pattern analysis
- Bias mitigation in AI models

## Datasets
All datasets are stored locally (not in git). See `.gitignore` for excluded formats.

## Experiment Tracking
Use MLflow or Weights & Biases for experiment tracking.

```bash
cd research/model-training
python train.py --config experiments/violence-detection-v2.yaml
```

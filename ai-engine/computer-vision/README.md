# Computer Vision

Visual analysis models for evidence verification and public safety monitoring.

## Models
- **Object Detection**: YOLOv8-based general object detection
- **Violence Detection**: CNN + LSTM for violent content in video/images
- **Railway Risk Detection**: Detect dangerous railway stunts and trespassing
- **Crowd Analysis**: Density estimation and crowd behavior analysis
- **Vehicle Analysis**: License plate recognition and vehicle type classification
- **Anomaly Detection**: Autoencoder-based unusual pattern detection

## Input Formats
- Video: MP4, AVI, MOV (frame extraction at configurable FPS)
- Image: JPEG, PNG, BMP, TIFF

## GPU Requirements
- Minimum: NVIDIA T4 (inference)
- Recommended: NVIDIA A10G (training + inference)

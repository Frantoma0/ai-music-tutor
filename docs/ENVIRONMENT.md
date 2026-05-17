# Environment Documentation

## Verified date
2026-05-17

## Host
- OS: Ubuntu 24.04.3 LTS on WSL2
- Project path: /home/frantoma/ai-music-tutor
- GPU: NVIDIA GeForce RTX 4070 Laptop GPU
- VRAM: 8188 MiB
- CUDA visible in WSL: 12.9 host / 12.1 PyTorch wheel

## Docker
- Docker works from WSL
- Docker Compose works from WSL
- Services:
  - amt-ollama: healthy
  - amt-backend: healthy
  - amt-frontend: running

## Ports
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Ollama host port: http://localhost:11435
- Ollama internal Docker URL: http://ollama:11434

## Backend stack verification
- PyTorch CUDA available: True
- PyTorch CUDA version: 12.1
- Basic Pitch installed as 0.4.0 with ONNX backend dependencies
- TensorFlow intentionally not installed
- CoreML/TFLite warnings are expected and ignored

## Qwen3
- Base model: qwen3:8b
- Custom model: qwen3-amt
- JSON API test: PASSED

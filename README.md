# Vehicle Monitoring & Detection

A real-time traffic monitoring and analysis system that uses YOLO-based object detection to track vehicles, detect violations, measure traffic density, and provide comprehensive traffic analytics from camera feeds.

## Overview

This project is a computer vision-based solution for smart traffic management. It processes video streams from traffic cameras to provide real-time vehicle detection, violation enforcement, traffic density analysis, and comprehensive counting statistics. The system supports multiple cameras simultaneously and provides both REST API and WebSocket interfaces for integration.

## Core Features

### Detection and Tracking
- Real-time vehicle detection using YOLO v8/v11/v12 models
- IOU-based object tracking with unique track IDs across frames
- Support for 6 vehicle classes: car, motorcycle, bus, truck, bicycle, person
- Configurable confidence and IOU thresholds
- Multi-camera support with independent tracking per camera

### Zone-Based Monitoring
- Interactive polygon editor for defining monitoring zones
- Multiple zone types:
  - Parking zones for violation detection
  - Traffic light zones for signal detection
  - Stop line zones for red light violations
  - Counting lines for directional vehicle counting
  - Ignore zones to exclude areas from analysis

### Violation Detection and Storage
- Parking violations: detect vehicles overstaying in no-parking zones
- Red light violations: detect vehicles crossing stop lines on red signals
- Automatic traffic light color detection using HSV color space
- Persistent violation storage with annotated frames
- Violation retrieval API with filtering by camera and type
- Automatic cleanup to maintain storage limits

### Traffic Density Analysis
- Real-time traffic density measurement using q = n/t formula
- Hourly historical comparison with rolling averages
- Density level classification: Low, Medium, Heavy
- Ignore zones support to exclude sidewalks and irrelevant areas
- Persistent hourly data storage per camera

### Vehicle Counting
- Directional line counting with in/out/both support
- Per-class counting statistics
- Cross-product detection algorithm for accurate line crossing
- Track ID-based duplicate prevention
- Real-time counting statistics API

### Model Management
- Dynamic model switching during runtime
- Support for multiple YOLO versions: v8, v11, v12
- Custom model discovery and loading
- Model benchmarking with performance metrics
- Automatic model download capability

### Advanced Streaming
- WebSocket-based real-time detection streaming
- Low-latency frame-by-frame processing
- HLS proxy for CORS bypass
- Base64 image detection support
- Multi-client connection management per camera

### Search and Analysis
- Image-based search functionality
- Text query support
- Historical violation search

## Technology Stack

### Frontend
- React 18.3 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- shadcn/ui component library
- React Router for navigation
- TanStack Query for data fetching
- HLS.js for video streaming
- Recharts for data visualization

### Backend
- FastAPI for REST API and WebSocket support
- Ultralytics YOLO for object detection
- OpenCV for image processing
- SimpleTracker for IOU-based tracking
- Shapely for geometric operations
- Pydantic for data validation
- Python 3.11.9

## Getting Started

### Prerequisites

- Node.js 18+ or Bun
- Python 3.11.9
- CUDA-compatible GPU (recommended for real-time detection)

### Frontend Setup

Using npm:

```bash
cd frontend
npm install
npm run dev
```

Using Bun:

```bash
cd frontend
bun install
bun run dev
```

The frontend will be available at `http://localhost:8080`

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
# Install Pytorch CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
# Check if CUDA is available
python -c 'import torch; print(torch.cuda.is_available())'
# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation is accessible at `http://localhost:8000/docs`

## Configuration

### Camera Configuration
Camera list is stored in `backend/app/data/ITS.link.json` with the following format:
```json
{
  "camera_id": {
    "name": "Camera Name",
    "location": "Location",
    "url": "http://....m3u8"
  }
}
```

### Zone Configuration
Zone configurations are stored per camera in `backend/app/data/zones/{camera_id}.json`. Each zone can be configured with:
- Polygon coordinates
- Zone type (parking, traffic light, stop line, counting, ignore)
- Zone name and ID
- Linked zones (for traffic light and stop line association)

### Model Configuration
Place YOLO model files (.pt) in `backend/app/preTrainedModels/`. The system automatically discovers custom models.

### Violation Storage
Violations are stored in `backend/app/data/violations/{camera_id}/{type}/` with:
- JSON metadata files
- Annotated frame images
- Automatic cleanup when exceeding 1000 violations per camera

## API Endpoints

### Detection
- `POST /api/detect` - Detect vehicles from image URL
- `POST /api/detect/frame` - Detect from video stream frame
- `POST /api/detection/detect-base64` - Detect from Base64 image
- `WS /api/detection/stream/{camera_id}` - WebSocket detection stream
- `WS /api/detection/video-stream/{camera_id}` - WebSocket video stream

### Camera Management
- `GET /api/cameras` - List available cameras

### Zone Management
- `GET /api/zones/{camera_id}` - Get zone configurations
- `POST /api/zones/{camera_id}` - Save zone configurations

### Violation Management
- `GET /api/violations/{camera_id}` - Get all violations for camera
- `GET /api/violations/{camera_id}/{type}` - Get violations by type

### Traffic Density
- `POST /api/detection/{camera_id}/density/start` - Start density tracking
- `GET /api/detection/{camera_id}/density/status` - Get tracking status
- `POST /api/detection/{camera_id}/density/stop` - Stop tracking and get results
- `GET /api/detection/{camera_id}/density/report` - Get report without stopping
- `POST /api/detection/{camera_id}/density/reset` - Reset tracking

### Counting Statistics
- `GET /api/detection/{camera_id}/counting/stats` - Get counting statistics
- `POST /api/detection/{camera_id}/counting/reset` - Reset counters
- `POST /api/detection/{camera_id}/counting/clear` - Clear all counting data

### Model Management
- `GET /api/models` - List all models
- `GET /api/models/downloaded` - List downloaded models
- `GET /api/models/current` - Get current active model
- `POST /api/models/switch` - Switch active model
- `POST /api/models/download` - Download a model
- `POST /api/models/unload` - Unload model from memory

### Benchmarking
- `POST /api/benchmark/run` - Run single model benchmark
- `POST /api/benchmark/run/all` - Benchmark all downloaded models
- `GET /api/benchmark/results` - Get benchmark results
- `GET /api/benchmark/comparison` - Get model comparison

### Proxy Services
- `GET /api/proxy/image?url={url}` - Proxy images with CORS bypass
- `GET /api/proxy/hls?url={url}` - Proxy HLS playlists
- `GET /api/proxy/hls/segment?url={url}` - Proxy HLS segments

### Search
- `POST /api/search` - Search with image or text query

## Baseline Evaluation Module

The baseline module provides comprehensive tools for evaluating detection models:

### Features
- Support for COCO, YOLO, and VOC dataset formats
- Metrics: mAP@0.5, mAP@0.75, mAP@[.5:.95], Precision, Recall, F1-Score
- IoU variants: IoU, GIoU, DIoU, CIoU
- FPS and latency benchmarking
- Model comparison reports in JSON, Markdown, and HTML formats
- Persistent benchmark history storage

### Usage

Run baseline evaluation:

```bash
python -m app.baseline.run_baseline --model yolov8n.pt --dataset data/coco --output results/
```

Quick FPS benchmark:

```bash
python -m app.baseline.run_baseline --model yolov8n.pt --benchmark-only
```

For detailed instructions, see `backend/app/baseline/README.md`

## Performance

### Expected Inference Times (GPU)
- YOLOv8n: 10ms, 30+ FPS
- YOLOv8s: 15ms, 25+ FPS
- YOLOv8m: 25ms, 20+ FPS
- YOLOv8l: 35ms, 15+ FPS
- YOLOv8x: 50ms, 10+ FPS

### Accuracy Targets
- YOLOv8n: mAP@0.5 37.3%
- YOLOv8s: mAP@0.5 44.9%
- YOLOv8m: mAP@0.5 50.2%
- YOLOv8l: mAP@0.5 52.9%
- YOLOv8x: mAP@0.5 53.9%

## Additional Documentation

- `ARCHITECTURE.md` - Complete system architecture with data flow diagrams
- `backend/app/baseline/README.md` - Baseline evaluation module documentation

## License

This project is for educational and research purposes.

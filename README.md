# 🎨 Auto Trace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ed.svg)](https://www.docker.com/)

> **A production-grade raster-to-vector conversion platform featuring three quality tiers, advanced preprocessing, async processing, and a modern web interface.**

---

## 📑 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [💻 CLI Usage](#-cli-usage)
- [🌐 API Usage](#-api-usage)
- [🛠️ Tech Stack](#️-tech-stack)
- [📚 Documentation](#-documentation)

---

## ✨ Features

### 🎛️ Quality Modes

| Mode | Preprocessing | SVG Optimization | Time | File Size | Best For |
|------|--------------|------------------|------|-----------|----------|
| **Fast** | None | Light | < 1s | 30-50KB | Simple graphics, clean images |
| **Standard** | Color reduction + Bilateral denoise + CLAHE | Standard | 1-3s | 20-40KB | Most images, photos |
| **High** | Standard + NLM + Sharpen + Edge enhancement | Aggressive | 3-10s | 15-30KB | Complex images, professional work |

### 🔬 Advanced Image Preprocessing
- **Color Reduction**: K-means clustering, Median cut (8-256 colors)
- **Noise Reduction**: Gaussian, Bilateral, NLM, Median filters
- **Contrast Enhancement**: CLAHE, Histogram equalization, Levels, Sigmoid
- **Sharpening & Edges**: Unsharp mask, Laplacian, Sobel, Scharr operators
- **Monochrome & Dithering**: Otsu, Adaptive, Floyd-Steinberg, Bayer, Atkinson

### 📉 SVG Optimization
- **Light**: Remove metadata and comments
- **Standard**: Scour optimization (path simplification, ID shortening)
- **Aggressive**: Standard + color optimization + number rounding + minification

### 📊 Quality Analysis
Provides deep metrics like **Edge Preservation Score (IoU)**, **SSIM**, **MSE**, **PSNR**, and **Histogram Correlation**.

### 💻 Modern Web Interface
- **Drag & Drop Upload**: Streamlined user experience
- **Real-time Progress**: Track Celery job conversions live
- **Quality Comparison**: Visual side-by-side comparison of different modes
- **Responsive**: Fully optimized for desktop, tablet, and mobile viewing

### ⚙️ Powerful API
- **Async Processing**: Driven by Celery & Redis
- **Batch Processing**: Parallelize multiple conversions
- **AI Recommendations**: Get the best mode recommended instantly

---

## 🏗️ Architecture

### System Flow

```mermaid
graph TD
    User([User]) --> Frontend[Next.js Frontend]
    Frontend --> API[FastAPI Backend]
    API --> Redis[(Redis Queue)]
    Redis --> Worker[Celery Worker]
    Worker --> CV[OpenCV Preprocessor]
    CV --> Engine[Vectorization Engine]
    Engine --> Opt[SVG Optimizer]
    Opt --> Result([SVG Result])
```

### Conversion Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant R as Redis
    participant W as Worker
    
    U->>F: Upload Image
    F->>B: POST /upload
    B-->>F: File ID
    F->>B: POST /convert (Quality Mode)
    B->>R: Queue Job
    B-->>F: Job ID
    loop Processing
        W->>R: Fetch Job
        W->>W: Preprocessing (OpenCV)
        W->>W: Vectorization (VTracer)
        W->>W: Optimization (Scour)
        W->>R: Update Status
        F->>B: GET /status/{job_id}
        B->>R: Query Status
        R-->>B: Status/Result
        B-->>F: Progress/Success
    end
    F->>U: Display SVG Result
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Redis 7+**

### Development Setup

```bash
# Clone repository
git clone https://github.com/mrigankad/RastertoSVG.git
cd RastertoSVG

# Setup Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup Frontend
cd ../frontend
npm install
```

### Run with Docker Compose (Recommended)

```bash
# Start all core services
docker-compose up -d

# Start with full monitoring (Prometheus, Grafana, Flower)
docker-compose --profile monitoring up -d
```

### Access Points
- **Frontend**: `http://localhost:3000`
- **API**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs`
- **Flower (Celery)**: `http://localhost:5555`
- **Prometheus / Grafana**: `http://localhost:9090` / `http://localhost:3001`

---

## 💻 CLI Usage

Auto Trace comes with a rich Command Line Interface for direct local usage.

```bash
# Convert single image
python -m backend.app.cli convert input.png -o output.svg --quality standard

# Batch convert an entire directory
python -m backend.app.cli batch ./input-dir -o ./output-dir --quality standard

# Run an automated quality comparison
python -m backend.app.cli compare input.png --output ./comparison

# Get AI-based quality recommendations
python -m backend.app.cli recommend input.png
```

---

## 🌐 API Usage

Easily integrate Auto Trace into your own applications using Python or direct HTTP calls.

### Python Client Example
```python
from examples.api_client import RasterToSVGClient

client = RasterToSVGClient("http://localhost:8000")

# Convert and block until complete
client.convert_and_wait("input.png", quality_mode="standard")

# Get recommendation
recommendation = client.get_recommendation("input.png")
print(f"Recommended: {recommendation['recommended_mode']}")
```

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/upload` | `POST` | Upload an image for processing |
| `/api/v1/convert` | `POST` | Start a conversion job |
| `/api/v1/status/{id}` | `GET`  | Poll conversion job status |
| `/api/v1/result/{id}` | `GET`  | Retrieve optimized SVG |
| `/api/v1/batch` | `POST` | Submit a batch conversion |

---

## 🛠️ Tech Stack

### Frontend
- **Next.js 14** (App Router)
- **TypeScript** & **Tailwind CSS**
- State Management: **Zustand**

### Backend & AI
- **FastAPI** (Python 3.11)
- Queue & Workers: **Celery** + **Redis**
- Vision & Processing: **OpenCV**, **Pillow**, **scikit-image**
- Vectorization: **VTracer**, **Potrace**, **Scour**

### Infrastructure
- **Docker** & **Docker Compose**
- **Kubernetes** Manifests included
- CI/CD via **GitHub Actions**

---

## 📚 Documentation

Dive deeper into Auto Trace's architecture and advanced capabilities:
- [Development Roadmap](./docs/PHASES.md)
- [Architecture & Design](./docs/ARCHITECTURE.md)
- [Preprocessing Guide](./docs/PREPROCESSING.md)
- [Deployment Guide](./docs/DEPLOYMENT.md)
- [API Reference](./docs/API.md)

---

## 🤝 Contributing & License

Contributions, issues, and feature requests are welcome!

Distributed under the **MIT License**. See `LICENSE` for more information.

---
<div align="center">
  <b>Built with ❤️ for the open source community</b>
</div>

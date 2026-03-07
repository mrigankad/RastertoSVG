# Agent Instructions: Building and Testing Raster to SVG Converter

This document provides step-by-step instructions for building, testing, and validating the entire Raster to SVG conversion system from scratch.

## Overview

**Purpose**: Complete build and test guide for the Raster to SVG Converter
**Audience**: Agents, developers, CI/CD systems
**Expected Duration**: 2-3 hours for first complete build
**Prerequisites**: Git, Docker (optional), Python 3.11+, Node.js 18+

---

## Part 1: System Prerequisites & Validation

### 1.1 Verify System Requirements

```bash
# Check Python version
python --version  # Should be 3.11 or higher

# Check Node.js version
node --version  # Should be 18 or higher
npm --version   # Should be 8 or higher (or use pnpm)

# Check Git
git --version   # Should be 2.30 or higher

# Check optional: Docker
docker --version  # Optional for containerized builds
```

**Expected Output**: All commands should return valid version numbers. If any fail, install missing tools.

### 1.2 Verify System Resources

```bash
# Check available disk space (need ~10GB minimum)
# On Linux/Mac: df -h
# On Windows: Get-Volume (PowerShell)

# Check available RAM (need ~4GB minimum)
# On Linux/Mac: free -h
# On Windows: Get-ComputerInfo | Select-Object CsTotalPhysicalMemory
```

**Expected Output**: At least 10GB free disk space and 4GB RAM available.

---

## Part 2: Backend Setup

### 2.1 Initialize Backend Project Structure

```bash
# Navigate to project root
cd "Raster to SVG"

# Create backend directory
mkdir -p backend/app/api
mkdir -p backend/app/services
mkdir -p backend/app/workers
mkdir -p backend/tests
mkdir -p backend/tests/fixtures/images
```

**Expected Result**: Backend directory structure created.

### 2.2 Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

**Expected Result**: Virtual environment activated (you should see `(venv)` in terminal).

**Troubleshooting**:
- If activation fails on Windows, try: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Verify venv folder exists with `ls venv` or `dir venv`

### 2.3 Create Requirements Files

Create `backend/requirements.txt`:

```
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6

# Async Task Queue
celery==5.3.4
redis==5.0.1

# Image Processing
pillow==10.1.0
opencv-python==4.8.1.78
scikit-image==0.22.0
numpy==1.26.2
scipy==1.11.4

# CLI
typer[all]==0.9.0

# Database (if using PostgreSQL)
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0

# Utilities
python-dotenv==1.0.0
httpx==0.25.2
aiofiles==23.2.1

# Monitoring (optional)
prometheus-client==0.19.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.12.0
flake8==6.1.0
mypy==1.7.1
```

Create `backend/requirements-dev.txt`:

```
-r requirements.txt

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
responses==0.24.1

# Code Quality
black==23.12.0
flake8==6.1.0
mypy==1.7.1
isort==5.13.2

# Pre-commit hooks
pre-commit==3.5.0
```

**Expected Result**: Two requirements files created in `backend/` directory.

### 2.4 Install Backend Dependencies

```bash
# Install production dependencies
pip install -r backend/requirements.txt

# Install development dependencies (optional)
pip install -r backend/requirements-dev.txt
```

**Expected Output**: All packages install successfully without errors.

**Troubleshooting**:
- If OpenCV fails: Try `pip install opencv-python-headless` instead
- If compilation errors occur: Ensure build tools are installed
  - Linux: `apt-get install build-essential`
  - macOS: `xcode-select --install`
  - Windows: Install Visual C++ Build Tools

### 2.5 Validate Backend Dependencies

```bash
# Test Python imports
python -c "
import fastapi
import celery
import pillow
import cv2
import numpy
import sklearn
import typer
print('✓ All core dependencies imported successfully')
"
```

**Expected Output**: "✓ All core dependencies imported successfully"

**If import fails**: Check which package failed and reinstall it individually.

---

## Part 3: Backend Core Implementation

### 3.1 Create Application Entry Point

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("Application starting up...")
    yield
    print("Application shutting down...")

app = FastAPI(
    title="Raster to SVG API",
    version="1.0.0",
    description="Convert raster images to vector SVG",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Raster to SVG Converter API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Expected Result**: File created successfully.

### 3.2 Create Configuration Module

Create `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Processing
    max_image_size: int = 104857600  # 100MB
    conversion_timeout: int = 300

    class Config:
        env_file = ".env"

settings = Settings()
```

**Expected Result**: Configuration module created.

### 3.3 Create Basic Converter Service

Create `backend/app/services/converter.py`:

```python
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class Converter:
    def __init__(self):
        self.vtracer_available = self._check_vtracer()
        self.potrace_available = self._check_potrace()

    def _check_vtracer(self) -> bool:
        """Check if VTracer is available"""
        try:
            import subprocess
            result = subprocess.run(['vtracer', '--version'], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("VTracer not found in PATH")
            return False

    def _check_potrace(self) -> bool:
        """Check if Potrace is available"""
        try:
            import subprocess
            result = subprocess.run(['potrace', '--version'], capture_output=True)
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("Potrace not found in PATH")
            return False

    def convert(
        self,
        input_path: str,
        output_path: str,
        image_type: str = "auto",
        quality_mode: str = "fast"
    ) -> Dict[str, Any]:
        """Convert raster image to SVG"""
        logger.info(f"Converting {input_path} -> {output_path}")

        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        try:
            # Placeholder conversion logic
            # To be replaced with actual VTracer/Potrace integration
            logger.info("Conversion completed")
            return {
                "status": "success",
                "input": input_path,
                "output": output_path,
                "processing_time": 0.0
            }
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise
```

**Expected Result**: Converter service created with basic structure.

### 3.4 Test Backend Application Startup

```bash
# Navigate to backend directory
cd backend

# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Test Health Endpoint**:
```bash
# In another terminal
curl http://localhost:8000/health
# Should return: {"status":"ok"}

curl http://localhost:8000/
# Should return: {"message":"Raster to SVG Converter API"}
```

**Expected Output**: Both endpoints return JSON responses.

**Troubleshooting**:
- If port already in use: `lsof -i :8000` (Linux/Mac) or `Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess` (Windows)
- Kill process and try again or use different port
- Stop the server with `Ctrl+C`

---

## Part 4: Frontend Setup

### 4.1 Create Next.js Project

```bash
# Navigate to project root
cd "Raster to SVG"

# Create Next.js project
npx create-next-app@14 frontend \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --eslint \
  --git

# Navigate into frontend
cd frontend
```

**Expected Result**: Next.js project created with TypeScript and Tailwind CSS.

**If create-next-app doesn't work**, manually create:

```bash
mkdir frontend
cd frontend
npm init -y
npm install next react react-dom typescript @types/react @types/node tailwindcss postcss autoprefixer
```

### 4.2 Create Frontend Project Structure

```bash
# Create directories
mkdir -p app
mkdir -p components
mkdir -p lib
mkdir -p public/images
mkdir -p __tests__
```

**Expected Result**: Frontend directory structure created.

### 4.3 Create Essential Frontend Files

Create `frontend/app/layout.tsx`:

```typescript
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Raster to SVG Converter',
  description: 'Convert raster images to vector SVG format',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
```

Create `frontend/app/page.tsx`:

```typescript
'use client'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">
          Raster to SVG Converter
        </h1>
        <p className="text-gray-600 mb-8">
          Convert your raster images to scalable vector graphics
        </p>
        <button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
          Get Started
        </button>
      </div>
    </main>
  )
}
```

Create `frontend/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
}
```

Create `frontend/tsconfig.json` (if not auto-created):

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForEnumMembers": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "resolveJsonModule": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "jsx": "preserve",
    "plugins": [
      {
        "name": "next"
      }
    ]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**Expected Result**: Frontend files created successfully.

### 4.4 Install Frontend Dependencies

```bash
# Install all dependencies
npm install

# Install additional libraries
npm install axios zustand @tanstack/react-query react-hot-toast lucide-react
```

**Expected Output**: All packages installed successfully.

**Troubleshooting**:
- If npm fails: Try `npm cache clean --force` then retry
- If OpenSSL errors: Update Node.js to latest LTS version

### 4.5 Create Environment Configuration

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME="Raster to SVG"
NEXT_PUBLIC_APP_VERSION=1.0.0
```

**Expected Result**: Environment file created.

### 4.6 Build and Test Frontend

```bash
# Development build and run
npm run dev

# In another terminal, verify it's running
curl http://localhost:3000
```

**Expected Output**:
```
> next dev
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
```

**Test Frontend**:
- Open `http://localhost:3000` in browser
- Should see "Raster to SVG Converter" heading
- Should see "Get Started" button

**Expected Result**: Frontend loads without errors.

**Troubleshooting**:
- If port already in use: `npm run dev -- -p 3001`
- Clear Next.js cache: `rm -rf .next`
- Clear npm cache: `npm cache clean --force`

---

## Part 5: Redis & Celery Setup (Optional but recommended)

### 5.1 Set Up Redis (Using Docker)

```bash
# Run Redis in Docker
docker run -d \
  --name raster-redis \
  -p 6379:6379 \
  redis:7-alpine

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

**Expected Output**: Redis container running, ping returns PONG.

**Alternative (Local Installation)**:
- Linux: `apt-get install redis-server && redis-server`
- macOS: `brew install redis && redis-server`
- Windows: Download from https://github.com/microsoftarchive/redis/releases

### 5.2 Create Celery Configuration

Create `backend/app/workers/celery.py`:

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "raster_to_svg",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)
```

Create `backend/app/workers/tasks.py`:

```python
from celery import shared_task
from app.services.converter import Converter
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def convert_image_task(self, input_path, output_path, image_type="auto", quality_mode="fast"):
    """Celery task for image conversion"""
    try:
        converter = Converter()
        result = converter.convert(
            input_path=input_path,
            output_path=output_path,
            image_type=image_type,
            quality_mode=quality_mode
        )
        return result
    except Exception as e:
        logger.error(f"Conversion task failed: {str(e)}")
        raise
```

**Expected Result**: Celery configuration created.

### 5.3 Test Celery Worker

```bash
# In a new terminal, start Celery worker
cd backend
celery -A app.workers.celery worker --loglevel=info
```

**Expected Output**:
```
 ---------- celery@hostname v5.x.x (herbivore)
 --- ***** -----
 -- ******* ----
 - *** --- * ---
 - ** ---------- [config]
 - ** ----------
 - -----
celery@hostname ready.
```

**Expected Result**: Celery worker starts successfully.

---

## Part 6: Integration Testing

### 6.1 Test Backend API Endpoints

Create `backend/tests/test_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
```

Run tests:

```bash
cd backend
pytest tests/test_api.py -v
```

**Expected Output**:
```
tests/test_api.py::test_health_check PASSED
tests/test_api.py::test_root_endpoint PASSED
```

### 6.2 Test Converter Service

Create `backend/tests/test_converter.py`:

```python
import pytest
from app.services.converter import Converter
import tempfile
from pathlib import Path

def test_converter_initialization():
    """Test that converter initializes"""
    converter = Converter()
    assert converter is not None

def test_converter_missing_file():
    """Test converter with missing file"""
    converter = Converter()
    with pytest.raises(FileNotFoundError):
        converter.convert("/nonexistent/file.png", "output.svg")
```

Run tests:

```bash
pytest tests/test_converter.py -v
```

**Expected Output**: Tests pass without errors.

### 6.3 Create Test Image

```bash
# Create a simple test image using Python
python -c "
from PIL import Image, ImageDraw
import os

os.makedirs('backend/tests/fixtures/images', exist_ok=True)

# Create color test image
img = Image.new('RGB', (100, 100), color='white')
draw = ImageDraw.Draw(img)
draw.ellipse([25, 25, 75, 75], fill='red', outline='blue')
img.save('backend/tests/fixtures/images/test_color.png')

# Create monochrome test image
img_bw = Image.new('L', (100, 100), color=255)
draw_bw = ImageDraw.Draw(img_bw)
draw_bw.rectangle([25, 25, 75, 75], fill=0)
img_bw.save('backend/tests/fixtures/images/test_monochrome.png')

print('✓ Test images created')
"
```

**Expected Result**: Test images created in `backend/tests/fixtures/images/`.

---

## Part 7: Full System Integration Test

### 7.1 Start All Services

Terminal 1 - Backend API:
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

Terminal 3 - Celery Worker (optional):
```bash
cd backend
celery -A app.workers.celery worker --loglevel=info
```

Terminal 4 - Redis (if using local Redis):
```bash
redis-server
```

**Expected Output**: All services running without errors.

### 7.2 Test Frontend to Backend Communication

Create `frontend/lib/api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function healthCheck() {
  const response = await fetch(`${API_URL}/health`);
  return response.json();
}
```

Create `frontend/app/test/page.tsx`:

```typescript
'use client'

import { useEffect, useState } from 'react';
import { healthCheck } from '@/lib/api';

export default function TestPage() {
  const [status, setStatus] = useState('Testing...');

  useEffect(() => {
    healthCheck()
      .then(data => setStatus(`✓ Backend OK: ${JSON.stringify(data)}`))
      .catch(err => setStatus(`✗ Backend Error: ${err.message}`));
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">System Status</h1>
      <p className="text-lg">{status}</p>
    </div>
  );
}
```

Visit `http://localhost:3000/test` in browser.

**Expected Result**: Should show "✓ Backend OK: {"status":"ok"}"

### 7.3 Run Complete Test Suite

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app --cov-report=html

# Frontend tests (if set up)
cd frontend
npm run test
```

**Expected Output**: All tests pass with good coverage (>80%).

---

## Part 8: Build for Production

### 8.1 Create Production Build Files

**Backend Dockerfile**:

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**:

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine

WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY package*.json ./
RUN npm ci --production

EXPOSE 3000
CMD ["npm", "start"]
```

### 8.2 Build Docker Images

```bash
# Build backend image
docker build -t raster-to-svg:backend ./backend

# Build frontend image
docker build -t raster-to-svg:frontend ./frontend

# Verify images built
docker images | grep raster-to-svg
```

**Expected Output**: Both images appear in docker images list.

### 8.3 Create Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  api:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./backend:/app

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://api:8000
    depends_on:
      - api

volumes:
  redis_data:
```

### 8.4 Test with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Test health
curl http://localhost:8000/health
curl http://localhost:3000

# Stop all services
docker-compose down
```

**Expected Output**: All services running, both health checks pass.

---

## Part 9: Validation Checklist

### 9.1 Backend Validation

- [ ] Python environment created and activated
- [ ] All Python dependencies installed
- [ ] `python -c "import fastapi"` works
- [ ] API starts with `uvicorn app.main:app`
- [ ] Health endpoint returns 200
- [ ] Root endpoint returns JSON
- [ ] Tests run and pass: `pytest tests/`
- [ ] No import errors
- [ ] Configuration loads correctly
- [ ] Celery worker starts successfully
- [ ] Redis connection successful

### 9.2 Frontend Validation

- [ ] Next.js project created
- [ ] All Node dependencies installed
- [ ] `npm run dev` starts without errors
- [ ] Frontend loads at `http://localhost:3000`
- [ ] No console errors in browser
- [ ] Tailwind CSS styles apply correctly
- [ ] TypeScript compiles without errors
- [ ] API communication test passes
- [ ] Build succeeds: `npm run build`

### 9.3 Integration Validation

- [ ] Both services running simultaneously
- [ ] Frontend can reach backend API
- [ ] Health check from frontend works
- [ ] No CORS errors in console
- [ ] Docker images build successfully
- [ ] Docker Compose starts all services
- [ ] All services healthy in Docker

### 9.4 Performance Validation

- [ ] Backend API responds in <100ms
- [ ] Frontend initial load <2s
- [ ] No memory leaks (monitor for 5 minutes)
- [ ] CPU usage reasonable (<50% idle)
- [ ] File upload accepts files properly
- [ ] Error handling graceful
- [ ] No unhandled exceptions in logs

---

## Part 10: Troubleshooting Guide

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
# Solution: Activate venv and reinstall
source venv/bin/activate  # Linux/Mac
pip install fastapi
```

**Issue**: Port 8000 already in use
```bash
# Solution: Find and kill process or use different port
lsof -i :8000  # Find process
kill -9 <PID>  # Kill it
# Or use different port:
uvicorn app.main:app --port 8001
```

**Issue**: `redis.ConnectionError: Error 111 connecting to localhost:6379`
```bash
# Solution: Start Redis
redis-server  # Local installation
# Or:
docker run -d -p 6379:6379 redis:7-alpine
```

**Issue**: `npm ERR! 404 Not Found`
```bash
# Solution: Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**Issue**: TypeScript compilation errors
```bash
# Solution: Regenerate types
rm -rf .next
npm run build
```

**Issue**: CORS errors from frontend
```bash
# Solution: Check CORS configuration in backend
# Verify allowed origins in app/main.py include frontend URL
```

### Debug Logging

Enable debug logging:

**Backend**:
```bash
PYTHONUNBUFFERED=1 python -m uvicorn app.main:app --log-level debug
```

**Frontend**:
```bash
npm run dev -- --verbose
```

---

## Part 11: Next Steps After Build

Once all validation passes:

1. **Review Phase Documentation**:
   - Read `PHASES.md`
   - Review current phase implementation
   - Plan next features

2. **Implement Phase 1 Core Features**:
   - Integrate VTracer/Potrace
   - Build CLI tool
   - Create unit tests

3. **Add API Endpoints**:
   - File upload endpoint
   - Conversion request endpoint
   - Status tracking endpoint

4. **Enhance Frontend**:
   - Add file upload component
   - Add conversion form
   - Add progress tracking

5. **Set Up CI/CD**:
   - Create GitHub Actions workflow
   - Add automated testing
   - Configure deployment

---

## Quick Reference Commands

```bash
# Backend setup
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && python -m uvicorn app.main:app --reload

# Frontend setup
npm install
npm run dev

# Testing
pytest backend/tests/ -v
npm run test

# Docker
docker build -t raster-to-svg:backend ./backend
docker-compose up -d

# Health checks
curl http://localhost:8000/health
curl http://localhost:3000
redis-cli ping
```

---

## Support & Debugging

If you encounter issues:

1. Check the troubleshooting guide above
2. Review logs carefully for error messages
3. Verify all prerequisites are installed
4. Try restarting services
5. Clear caches (npm, pip, Docker)
6. Check network connectivity (Redis, API)
7. Review phase documentation for implementation details

---

**Document Version**: 1.0
**Last Updated**: 2025-03-07
**For Questions**: Refer to PHASES.md for detailed phase instructions

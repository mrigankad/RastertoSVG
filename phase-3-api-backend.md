# Phase 3: Backend Infrastructure (API + Async Processing)

**Duration**: 3-4 weeks
**Goal**: Build scalable API with async job processing using FastAPI, Celery, and Redis

## Objectives

- Create FastAPI REST API for conversion requests
- Implement Celery worker system for async processing
- Set up Redis for caching and job queue
- Build job management and status tracking
- Implement request validation and error handling
- Create comprehensive API documentation
- Add monitoring and logging infrastructure

## Architecture

```
Client Request
    ↓
FastAPI Server
├→ Validate Request
├→ Create Job Record
├→ Queue to Celery
└→ Return Job ID
    ↓
Redis Queue
    ↓
Celery Workers (multiple)
├→ Retrieve Job
├→ Run Conversion
├→ Update Status
└→ Store Result
    ↓
Client Polls Status / Receives Result
```

## Tasks

### 3.1 FastAPI Application Setup

- [ ] Create `backend/app/main.py`:
  ```python
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.responses import FileResponse

  app = FastAPI(
      title="Raster to SVG API",
      version="1.0.0",
      description="Convert raster images to vector SVG"
  )

  # CORS configuration
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000", "http://localhost:8000"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- [ ] Configure logging:
  - Structured logging (JSON format)
  - Log levels: DEBUG, INFO, WARNING, ERROR
  - Request/response logging middleware
  - Access logs
- [ ] Error handling:
  - Custom exception classes
  - Global exception handlers
  - Proper HTTP status codes
- [ ] Health check endpoint:
  - `/health` - API status
  - `/health/db` - Redis connection
  - `/health/celery` - Worker status

### 3.2 Data Models (Pydantic)

- [ ] Create `backend/app/api/models.py`:
  ```python
  class ConversionRequest(BaseModel):
      image_type: Literal["auto", "color", "monochrome"]
      quality_mode: Literal["fast", "standard", "high"]
      color_palette: Optional[int] = 32
      denoise_strength: Optional[str] = "medium"

  class ConversionResponse(BaseModel):
      job_id: str
      status: str
      created_at: datetime

  class JobStatus(BaseModel):
      job_id: str
      status: Literal["pending", "processing", "completed", "failed"]
      progress: float  # 0.0 to 1.0
      error: Optional[str] = None
      result_url: Optional[str] = None
      created_at: datetime
      completed_at: Optional[datetime] = None
      processing_time: Optional[float] = None

  class UploadResponse(BaseModel):
      file_id: str
      filename: str
      size: int
      format: str
  ```
- [ ] Validation:
  - File size limits
  - Supported formats
  - Parameter ranges
  - Custom validators

### 3.3 API Routes

- [ ] Create `backend/app/api/routes.py`:

#### Upload Endpoint
```python
@router.post("/api/v1/upload")
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload an image file for conversion
    Returns file_id for use in conversion requests
    """
```

#### Conversion Endpoint
```python
@router.post("/api/v1/convert")
async def convert_image(
    file_id: str = Form(...),
    request: ConversionRequest = Form(...)
) -> ConversionResponse:
    """
    Start conversion job for uploaded image
    Returns job_id to track conversion status
    """
```

#### Status Endpoint
```python
@router.get("/api/v1/status/{job_id}")
async def get_job_status(job_id: str) -> JobStatus:
    """
    Get current status and progress of conversion job
    """
```

#### Download Endpoint
```python
@router.get("/api/v1/result/{job_id}")
async def download_result(job_id: str) -> FileResponse:
    """
    Download completed SVG file
    """
```

#### Batch Conversion
```python
@router.post("/api/v1/batch")
async def batch_convert(
    file_ids: List[str] = Form(...),
    request: ConversionRequest = Form(...)
) -> BatchResponse:
    """
    Start multiple conversion jobs
    Returns list of job_ids
    """
```

- [ ] Implement file storage:
  - Temporary upload directory
  - Result storage directory
  - Cleanup strategy (old files after N days)
  - File size validation
- [ ] Rate limiting:
  - Per-IP rate limits
  - Per-user rate limits (if authenticated)
  - Graceful error handling

### 3.4 Celery Task Queue

- [ ] Create `backend/app/workers/celery.py`:
  ```python
  from celery import Celery

  celery_app = Celery(
      "raster_to_svg",
      broker=CELERY_BROKER_URL,
      backend=CELERY_RESULT_BACKEND,
      include=["app.workers.tasks"]
  )

  celery_app.conf.update(
      task_serializer='json',
      accept_content=['json'],
      result_serializer='json',
      timezone='UTC',
      enable_utc=True,
      task_track_started=True,
      task_time_limit=30 * 60,  # 30 minutes hard limit
      task_soft_time_limit=25 * 60,  # 25 minutes soft limit
  )
  ```

- [ ] Create `backend/app/workers/tasks.py`:
  ```python
  @celery_app.task(bind=True, name="convert_image")
  def convert_image_task(self, file_id: str, request_data: dict):
      """
      Main conversion task executed by Celery workers
      """
      try:
          # Update status: processing
          update_job_status(file_id, "processing", progress=0.1)

          # Run conversion
          converter = Converter()
          result = converter.convert(...)

          # Update status: completed
          update_job_status(file_id, "completed", progress=1.0)

          return {"status": "success", "result": result}
      except Exception as e:
          update_job_status(file_id, "failed", error=str(e))
          raise
  ```

- [ ] Implement task features:
  - Task retries (exponential backoff)
  - Task timeouts
  - Progress tracking
  - Error callbacks
  - Dead letter queue for failed tasks

### 3.5 Redis Integration

- [ ] Set up Redis connection:
  ```python
  import redis

  redis_client = redis.from_url(REDIS_URL, decode_responses=True)
  ```

- [ ] Implement caching:
  - Cache job status
  - Cache intermediate results
  - Cache conversion parameters
  - TTL strategy (30 days for completed jobs)

- [ ] Job tracking:
  ```python
  # Store job metadata
  redis_client.hset(
      f"job:{job_id}",
      mapping={
          "status": "processing",
          "progress": 0.5,
          "created_at": datetime.now().isoformat(),
          "image_type": "color",
          "quality_mode": "standard"
      }
  )

  # Job list (for user history)
  redis_client.lpush(f"user:{user_id}:jobs", job_id)
  ```

### 3.6 File Management Service

- [ ] Create `backend/app/services/file_manager.py`:
  ```python
  class FileManager:
      def save_upload(self, file: UploadFile) -> str:
          """Save uploaded file, return file_id"""

      def save_result(self, job_id: str, svg_content: str) -> str:
          """Save result SVG, return path"""

      def get_upload(self, file_id: str) -> Path:
          """Get path to uploaded file"""

      def get_result(self, job_id: str) -> Path:
          """Get path to result SVG"""

      def cleanup_old_files(self, days: int = 30):
          """Remove files older than N days"""
  ```

- [ ] Storage structure:
  ```
  storage/
  ├── uploads/
  │   ├── {date}/
  │   │   ├── {file_id}.png
  │   │   └── {file_id}.jpg
  │   └── {date}/
  └── results/
      ├── {date}/
      │   ├── {job_id}.svg
      │   └── {job_id}.metadata.json
      └── {date}/
  ```

- [ ] Cleanup strategy:
  - Scheduled task (daily, weekly)
  - Configurable retention period
  - Preserve recent conversions
  - Audit trail of deletions

### 3.7 Job Database

- [ ] Choose persistence layer:
  - Option A: PostgreSQL for persistent records
  - Option B: Redis with dumps for simplicity
  - Option C: SQLite for development, scale later

- [ ] If using database (Option A):
  ```python
  class Job(Base):
      __tablename__ = "jobs"

      id = Column(String, primary_key=True)
      file_id = Column(String)
      status = Column(String)  # pending, processing, completed, failed
      progress = Column(Float)
      error = Column(String, nullable=True)
      image_type = Column(String)
      quality_mode = Column(String)
      created_at = Column(DateTime)
      completed_at = Column(DateTime, nullable=True)
      processing_time = Column(Float, nullable=True)
  ```

- [ ] CRUD operations:
  - Create job record on request
  - Update status and progress
  - Query job history
  - Cleanup old records

### 3.8 Monitoring & Metrics

- [ ] Add Prometheus metrics:
  - Request count
  - Request latency
  - Conversion time distribution
  - Error rates
  - Queue length
  - Worker status

- [ ] Implement metric collection:
  ```python
  from prometheus_client import Counter, Histogram

  conversion_counter = Counter(
      'conversions_total',
      'Total conversions',
      ['status', 'quality_mode']
  )

  conversion_time = Histogram(
      'conversion_seconds',
      'Conversion time in seconds',
      ['quality_mode']
  )
  ```

- [ ] Metrics endpoint:
  - `/metrics` - Prometheus format
  - Dashboard (Grafana integration later)

### 3.9 Logging

- [ ] Structured logging configuration:
  ```python
  import logging
  import json

  class JSONFormatter(logging.Formatter):
      def format(self, record):
          return json.dumps({
              "timestamp": datetime.utcnow().isoformat(),
              "level": record.levelname,
              "message": record.getMessage(),
              "module": record.name
          })
  ```

- [ ] Log levels:
  - DEBUG: Conversion parameters, intermediate steps
  - INFO: Job created, completed, status updates
  - WARNING: Slow conversions, resource issues
  - ERROR: Conversion failures, system errors
  - CRITICAL: Worker crashes, Redis disconnection

- [ ] Centralized logging (optional):
  - ELK stack integration
  - Log rotation
  - Long-term storage

### 3.10 Testing

- [ ] Create `backend/tests/test_api.py`:
  - Test all endpoints
  - Test request validation
  - Test file upload/download
  - Test error handling
  - Test concurrent requests
  - Use pytest with async support

- [ ] Create `backend/tests/test_celery.py`:
  - Test task execution
  - Test retry logic
  - Test error callbacks
  - Test progress tracking

- [ ] Create `backend/tests/test_redis.py`:
  - Test connection
  - Test caching
  - Test job tracking
  - Test cleanup

- [ ] Integration tests:
  - Upload → Convert → Download workflow
  - Batch conversions
  - Status polling
  - Concurrent job handling

### 3.11 Documentation

- [ ] Create `docs/API.md`:
  - Endpoint documentation
  - Request/response examples
  - Error codes
  - Authentication (if added)
  - Rate limits

- [ ] Create OpenAPI/Swagger docs:
  - Auto-generated from FastAPI
  - Available at `/docs`
  - Interactive testing interface

- [ ] Create deployment guide:
  - Docker setup
  - Environment variables
  - Worker scaling
  - Redis configuration

## Deliverables

- ✅ FastAPI application with all endpoints
- ✅ Celery task queue configured
- ✅ Redis integration for caching and job tracking
- ✅ File upload/download system
- ✅ Job status tracking
- ✅ Comprehensive API documentation
- ✅ Monitoring and logging
- ✅ Test suite with good coverage
- ✅ Docker compose for local development

## Success Criteria

- [ ] All API endpoints working correctly
- [ ] File upload/download working reliably
- [ ] Celery tasks executing successfully
- [ ] Job status tracking accurate
- [ ] Concurrent conversions handled properly
- [ ] Error handling covers edge cases
- [ ] API documentation complete
- [ ] Tests pass with >80% coverage
- [ ] Performance acceptable (median <5s for standard conversions)

## Performance Targets

- Upload: < 2s for 10MB file
- Job creation: < 100ms
- Status query: < 50ms
- Concurrent jobs: Support 10+ simultaneous
- Queue processing: Process jobs in order of submission

## Next Phase

→ [Phase 4: Frontend Application](./phase-4-frontend.md)

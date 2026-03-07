# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Web UI     │  │     CLI      │  │  API Client  │              │
│  │  (Next.js)   │  │   (Typer)    │  │  (HTTP/REST) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
└─────────┼─────────────────┼─────────────────┼──────────────────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼──────────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Routes: /upload, /convert, /status, /result, /batch          │ │
│  │  Middleware: CORS, Auth, Rate Limiting, Logging               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────┐
│    JOB QUEUE (Redis)    │  │    DATABASE (Redis)     │
│  ┌─────────────────────┐│  │  ┌─────────────────────┐│
│  │  Celery Task Queue  ││  │  │   Job Metadata      ││
│  └─────────────────────┘│  │  │   - Status          ││
└─────────────────────────┘  │  │   - Progress        ││
                             │  │   - Results         ││
                             │  └─────────────────────┘│
                             └─────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKER LAYER (Celery)                            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Tasks: convert_image, batch_convert, cleanup_old_files       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐      ┌──────────────────┐      ┌───────────────┐
│ Preprocessing │──────▶  Conversion      │──────▶ Optimization  │
│   Service     │      │   Engines        │      │   Service     │
│               │      │                  │      │               │
│ - Denoise     │      │ - VTracer        │      │ - Scour       │
│ - Color Red.  │      │ - Potrace        │      │ - SVGO        │
│ - Contrast    │      │ - ML Models      │      │ - Simplify    │
└───────────────┘      └──────────────────┘      └───────────────┘
```

## Component Details

### Frontend (Next.js 14)

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Data Fetching**: React Query / Axios

Key pages:
- `/` - Home/Landing
- `/convert` - Conversion interface
- `/history` - Conversion history

### Backend (FastAPI)

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Validation**: Pydantic
- **Async**: Native async/await support

Key modules:
- `api/routes.py` - API endpoints
- `api/models.py` - Request/response models
- `services/converter.py` - Main conversion logic
- `services/preprocessor.py` - Image preprocessing
- `services/optimizer.py` - SVG optimization

### Worker Queue (Celery + Redis)

- **Queue**: Redis (broker and result backend)
- **Workers**: Celery distributed task queue
- **Monitoring**: Celery Flower (optional)

Tasks:
- `convert_image` - Single image conversion
- `batch_convert` - Multiple image conversion
- `cleanup_old_files` - Periodic cleanup

### Conversion Engines

#### VTracer (Color Images)
- Modern Rust-based tracer
- Color clustering and hierarchical grouping
- Good for photographs and colorful graphics

#### Potrace (Monochrome Images)
- Classic bitmap tracing
- Optimized for black and white images
- Fast and reliable

#### ML Models (High Quality Mode)
- SAMVG or similar segmentation-based approaches
- Better edge detection and shape preservation
- Slower but higher quality

## Data Flow

### Single Conversion

```
1. Client uploads image → POST /upload
2. Server saves file → Returns file_id
3. Client requests conversion → POST /convert (file_id, options)
4. Server creates job → Queues Celery task → Returns job_id
5. Worker processes conversion
   a. Load image
   b. Preprocess (if quality != fast)
   c. Convert (VTracer/Potrace)
   d. Optimize SVG
   e. Save result
6. Client polls status → GET /status/{job_id}
7. When complete, client downloads → GET /result/{job_id}
```

### Batch Conversion

```
1. Client uploads multiple images
2. Client requests batch conversion with file_ids
3. Server creates batch job with multiple Celery tasks
4. Workers process in parallel
5. Client polls batch status
6. Download individual results
```

## Storage Structure

```
storage/
├── uploads/
│   ├── 20240301/
│   │   ├── {uuid1}.png
│   │   └── {uuid2}.jpg
│   └── 20240302/
└── results/
    ├── 20240301/
    │   ├── {job_id1}.svg
    │   └── {job_id1}.metadata.json
    └── 20240302/
```

## Quality Modes

| Mode | Preprocessing | Engine | Time | Best For |
|------|--------------|--------|------|----------|
| Fast | None | VTracer/Potrace | < 1s | Simple graphics |
| Standard | Color reduction, denoise | VTracer/Potrace | 2-5s | Most images |
| High | Full preprocessing + ML | SAMVG/Enhanced | 5-30s | Professional work |

## Security Considerations

- File upload validation (type, size)
- Output sanitization
- Rate limiting
- CORS configuration
- Input sanitization

## Scalability

- Stateless API servers (horizontal scaling)
- Celery workers scale independently
- Redis clustering for high availability
- File storage can use S3-compatible object storage

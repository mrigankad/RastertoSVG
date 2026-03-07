# API Documentation

## Base URL

Development: `http://localhost:8000/api/v1`

## Authentication

Currently, the API does not require authentication. Rate limiting may be applied.

## Endpoints

### Health Check

```
GET /health
```

Returns service status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": 1234567890
}
```

### Upload Image

```
POST /upload
```

Upload an image file for conversion.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (binary)

**Response:**
```json
{
  "file_id": "uuid-string",
  "filename": "image.png",
  "size": 12345,
  "format": "image/png"
}
```

**Errors:**
- `400 Bad Request` - Invalid file type or too large
- `500 Internal Server Error` - Server error

### Convert Image

```
POST /convert
```

Start a conversion job for an uploaded image.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `file_id` (string, required) - File ID from upload
  - `image_type` (string, optional) - `auto`, `color`, `monochrome` (default: `auto`)
  - `quality_mode` (string, optional) - `fast`, `standard`, `high` (default: `standard`)
  - `color_palette` (int, optional) - Max colors 8-256 (default: 32)
  - `denoise_strength` (string, optional) - `light`, `medium`, `heavy` (default: `medium`)

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "created_at": "2024-03-01T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - File not found
- `500 Internal Server Error` - Failed to create job

### Get Job Status

```
GET /status/{job_id}
```

Get current status and progress of conversion job.

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "processing",
  "progress": 0.5,
  "error": null,
  "result_url": null,
  "created_at": "2024-03-01T12:00:00Z",
  "completed_at": null,
  "processing_time": null
}
```

Status values: `pending`, `processing`, `completed`, `failed`

### Download Result

```
GET /result/{job_id}
```

Download the completed SVG file.

**Response:**
- Content-Type: `image/svg+xml`
- Body: SVG file content

**Errors:**
- `404 Not Found` - Job not found
- `400 Bad Request` - Job not complete or failed

### Batch Convert

```
POST /batch
```

Start multiple conversion jobs.

**Request:**
```json
{
  "file_ids": ["uuid-1", "uuid-2"],
  "options": {
    "image_type": "auto",
    "quality_mode": "standard",
    "color_palette": 32,
    "denoise_strength": "medium"
  }
}
```

**Response:**
```json
{
  "batch_id": "uuid-string",
  "job_ids": ["job-1", "job-2"],
  "total": 2
}
```

### List Jobs

```
GET /jobs?status={status}&limit={limit}&offset={offset}
```

List conversion jobs.

**Query Parameters:**
- `status` (optional) - Filter by status: `pending`, `processing`, `completed`, `failed`
- `limit` (optional) - Number of jobs to return (default: 50, max: 200)
- `offset` (optional) - Offset for pagination (default: 0)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "completed",
      "progress": 1.0,
      ...
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

### Delete Job

```
DELETE /jobs/{job_id}
```

Delete a job and its associated files.

**Response:**
```json
{
  "status": "deleted",
  "job_id": "uuid-string"
}
```

### Storage Stats

```
GET /storage/stats
```

Get storage usage statistics.

**Response:**
```json
{
  "uploads": {
    "count": 100,
    "size_mb": 50.5
  },
  "results": {
    "count": 50,
    "size_mb": 10.2
  },
  "total_size_mb": 60.7
}
```

### Cleanup Storage

```
POST /storage/cleanup?days={days}
```

Clean up old files.

**Query Parameters:**
- `days` (optional) - Age in days for files to be deleted (default: 30, max: 365)

**Response:**
```json
{
  "status": "cleanup_started",
  "days": 30,
  "message": "Cleanup task queued"
}
```

### Queue Stats

```
GET /queue/stats
```

Get job queue statistics.

**Response:**
```json
{
  "pending": 5,
  "processing": 2,
  "completed": 100,
  "failed": 3
}
```

## Error Format

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

## Rate Limits

- Upload: 10 requests/minute
- Convert: 30 requests/minute
- Status: 60 requests/minute

## Workflow

### Single Image Conversion

```
1. Upload image → POST /upload
2. Get file_id from response
3. Start conversion → POST /convert (file_id, options)
4. Get job_id from response
5. Poll status → GET /status/{job_id}
6. When status = "completed", download → GET /result/{job_id}
```

### Batch Conversion

```
1. Upload multiple images → POST /upload (for each)
2. Collect file_ids
3. Start batch → POST /batch (file_ids, options)
4. Get list of job_ids
5. Poll status for each job → GET /status/{job_id}
6. Download results when complete
```

## SDK Examples

### Python

```python
import requests
import time

API_BASE = "http://localhost:8000/api/v1"

# Upload
with open('image.png', 'rb') as f:
    response = requests.post(
        f'{API_BASE}/upload',
        files={'file': f}
    )
file_id = response.json()['file_id']

# Convert
response = requests.post(
    f'{API_BASE}/convert',
    data={
        'file_id': file_id,
        'quality_mode': 'standard',
        'image_type': 'auto',
    }
)
job_id = response.json()['job_id']

# Poll status
while True:
    response = requests.get(f'{API_BASE}/status/{job_id}')
    status = response.json()
    print(f"Progress: {status['progress']*100:.0f}%")
    
    if status['status'] == 'completed':
        break
    elif status['status'] == 'failed':
        print(f"Error: {status['error']}")
        break
    
    time.sleep(1)

# Download
response = requests.get(f'{API_BASE}/result/{job_id}')
with open('output.svg', 'wb') as f:
    f.write(response.content)
```

### JavaScript

```javascript
// Upload
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const uploadRes = await fetch('http://localhost:8000/api/v1/upload', {
  method: 'POST',
  body: formData
});
const { file_id } = await uploadRes.json();

// Convert
const convertRes = await fetch('http://localhost:8000/api/v1/convert', {
  method: 'POST',
  headers: {'Content-Type': 'application/x-www-form-urlencoded'},
  body: new URLSearchParams({
    file_id,
    quality_mode: 'standard'
  })
});
const { job_id } = await convertRes.json();

// Poll status
const pollStatus = async () => {
  const res = await fetch(`http://localhost:8000/api/v1/status/${job_id}`);
  const status = await res.json();
  
  console.log(`Progress: ${(status.progress * 100).toFixed(0)}%`);
  
  if (status.status === 'completed') {
    // Download result
    window.location.href = `http://localhost:8000/api/v1/result/${job_id}`;
  } else if (status.status !== 'failed') {
    setTimeout(pollStatus, 1000);
  } else {
    console.error('Conversion failed:', status.error);
  }
};
pollStatus();
```

### cURL

```bash
# Upload
curl -X POST -F "file=@image.png" http://localhost:8000/api/v1/upload

# Convert
curl -X POST -d "file_id=<file_id>&quality_mode=standard" \
  http://localhost:8000/api/v1/convert

# Check status
curl http://localhost:8000/api/v1/status/<job_id>

# Download
curl -o output.svg http://localhost:8000/api/v1/result/<job_id>
```

## WebSocket (Future)

Real-time status updates via WebSocket:

```
ws://localhost:8000/ws/{job_id}
```

Messages:
- `{"type": "progress", "value": 0.5}`
- `{"type": "status", "status": "completed"}`
- `{"type": "error", "message": "..."}`

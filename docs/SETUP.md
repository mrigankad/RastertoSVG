# Setup Guide

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Redis 7 or higher
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd raster-to-svg
```

### 2. Set up Python Environment

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Set up Node.js Environment

```bash
cd ../frontend

# Install dependencies
npm install

# Or if using pnpm:
pnpm install
```

### 4. Configure Environment Variables

```bash
cd ../backend

# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

### 5. Start Redis

Make sure Redis is running on your system:

```bash
# On macOS with Homebrew:
brew services start redis

# On Ubuntu/Debian:
sudo service redis-server start

# Or using Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Run the Application

You need to run three services simultaneously:

**Terminal 1 - API Server:**
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 - Celery Worker:**
```bash
cd backend
celery -A app.workers.celery worker --loglevel=info
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

### 7. Verify Installation

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

## Docker Setup (Alternative)

If you prefer using Docker:

```bash
# Build and run all services
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Troubleshooting

### Redis Connection Error

Make sure Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

### Python Import Errors

Make sure you're in the virtual environment and dependencies are installed:
```bash
which python
pip list
```

### Node.js Errors

Clear npm cache and reinstall:
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Port Already in Use

Change the ports in `.env`:
```bash
API_PORT=8001
```

And in frontend `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
```

## Development Workflow

1. **Create a new branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test:**
   ```bash
   # Run tests
   cd backend
   pytest
   
   # Type check
   cd ../frontend
   npm run type-check
   ```

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin feature/your-feature-name
   ```

## Next Steps

- Read the [API Documentation](./API.md)
- Review the [Architecture Overview](./ARCHITECTURE.md)
- Check the [CLI Documentation](./CLI.md)

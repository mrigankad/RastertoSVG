# Phase 0: Foundation & Environment Setup

**Duration**: 1-2 weeks
**Goal**: Establish development environment, project structure, and core dependencies

## Objectives

- Set up Python virtual environment and package management
- Configure Node.js/npm environment for frontend development
- Create project directory structure
- Initialize Git repository with .gitignore
- Document project setup for team collaboration
- Validate all core dependencies install correctly

## Tasks

### 0.1 Python Environment Setup
- [ ] Create Python 3.11+ virtual environment
- [ ] Create `requirements.txt` with core dependencies:
  - `typer[all]` - CLI framework
  - `fastapi` - Web API framework
  - `celery` - Task queue
  - `redis` - Message broker & cache
  - `pillow` - Image manipulation
  - `opencv-python` - Advanced image processing
  - `scikit-image` - Scientific image processing
  - `numpy` - Numerical computing
  - `pydantic` - Data validation
  - `python-multipart` - Form data handling
  - `uvicorn` - ASGI server
  - `python-dotenv` - Environment management
- [ ] Create `requirements-dev.txt` with dev dependencies:
  - `pytest` - Testing framework
  - `pytest-asyncio` - Async test support
  - `black` - Code formatter
  - `flake8` - Linter
  - `mypy` - Type checker
  - `pre-commit` - Git hooks

### 0.2 Node.js/Frontend Environment
- [ ] Initialize Node.js project with npm/pnpm
- [ ] Create `package.json` with dependencies:
  - `next@14` - React framework
  - `react@18` - UI library
  - `typescript` - Type safety
  - `tailwindcss` - Styling
  - `axios` - HTTP client
  - `zustand` or `redux-toolkit` - State management
  - `svgo` - SVG optimization
- [ ] Create `package-dev.json` or dev dependencies:
  - `eslint` - Linting
  - `prettier` - Formatting
  - `@types/*` - TypeScript definitions

### 0.3 Project Structure
```
Raster-to-SVG/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py (FastAPI app entry)
│   │   ├── cli.py (Typer CLI)
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes.py
│   │   │   └── models.py
│   │   ├── workers/
│   │   │   ├── celery.py
│   │   │   └── tasks.py
│   │   └── services/
│   │       ├── converter.py
│   │       ├── preprocessor.py
│   │       └── optimizer.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/ (Next.js App Router)
│   ├── components/
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   ├── ARCHITECTURE.md
│   └── API.md
├── .gitignore
├── README.md
└── PHASES.md
```

### 0.4 Git & Version Control
- [ ] Initialize git repository
- [ ] Create comprehensive `.gitignore`:
  - Python: `__pycache__/`, `*.pyc`, `venv/`, `.env`
  - Node: `node_modules/`, `.next/`, `.env.local`
  - IDE: `.vscode/`, `.idea/`, `*.swp`
  - OS: `.DS_Store`, `Thumbs.db`
- [ ] Create initial commit with project structure
- [ ] Set up Git hooks with pre-commit:
  - Run black formatter
  - Run flake8 linter
  - Run mypy type checker
  - Run pytest for Python tests

### 0.5 Configuration & Documentation
- [ ] Create `.env.example` with all required environment variables:
  ```
  # Redis
  REDIS_URL=redis://localhost:6379

  # Celery
  CELERY_BROKER_URL=redis://localhost:6379/0
  CELERY_RESULT_BACKEND=redis://localhost:6379/1

  # FastAPI
  API_HOST=0.0.0.0
  API_PORT=8000

  # Processing
  MAX_IMAGE_SIZE=50MB
  CONVERSION_TIMEOUT=300
  ```
- [ ] Create `SETUP.md` with installation instructions
- [ ] Create `DEVELOPMENT.md` with development workflow
- [ ] Create `ARCHITECTURE.md` with system design overview

### 0.6 Dependency Validation
- [ ] Test Python environment:
  - Install all requirements
  - Verify imports work
  - Test Redis connection
  - Test core library versions
- [ ] Test Node.js environment:
  - Install all packages
  - Verify TypeScript compilation
  - Test Tailwind build
- [ ] Document any compatibility issues

## Deliverables

- ✅ Working Python virtual environment
- ✅ Working Node.js development environment
- ✅ Project directory structure created
- ✅ Git repository initialized with proper gitignore
- ✅ All dependencies documented and installable
- ✅ Setup and development documentation complete
- ✅ Pre-commit hooks configured
- ✅ Team can clone and run `npm install` & `pip install -r requirements.txt`

## Success Criteria

- [ ] All Python dependencies import without errors
- [ ] All Node packages install successfully
- [ ] Git pre-commit hooks run without issues
- [ ] CI/CD pipeline (if applicable) passes initial checks
- [ ] README has clear setup instructions
- [ ] New developer can get environment running in <30 minutes

## Next Phase

→ [Phase 1: Core Engine & CLI](./phase-1-cli-core.md)

# Development Phases & Roadmap

This document outlines the development lifecycle of the Raster to SVG platform, including completed phases, future roadmap, and discarded concepts.

## Core Development Roadmap

### ✅ Phase 0: Foundation & Environment Setup
- **Focus**: Environment parity, dependency management, and project structure.
- **Key Deliverables**: Dockerized growth environment, CI/CD foundations.
- [Detailed Tasks](./phase-0-foundation.md)

### ✅ Phase 1: Core Engine & CLI Tool
- **Focus**: Integrating VTracer and Potrace with a unified CLI interface.
- **Key Deliverables**: A robust CLI for local conversions.
- [Detailed Tasks](./phase-1-cli-core.md)

### ✅ Phase 2: Preprocessing Pipeline
- **Focus**: OpenCV-based image enhancement (denoising, contrast, color reduction).
- **Key Deliverables**: Configurable pipeline for improving vectorization results.
- [Detailed Tasks](./phase-2-preprocessing.md)

### ✅ Phase 3: Backend Infrastructure (API + Async)
- **Focus**: Scalable API and background worker architecture.
- **Key Deliverables**: FastAPI + Celery + Redis stack.
- [Detailed Tasks](./phase-3-api-backend.md)

### ✅ Phase 4: Frontend Application
- **Focus**: Modern, responsive web interface with real-time feedback.
- **Key Deliverables**: Next.js 14 application with drag-and-drop.
- [Detailed Tasks](./phase-4-frontend.md)

### ✅ Phase 5: Quality Modes & Advanced Optimization
- **Focus**: Defining "Fast", "Standard", and "High" tiers with tiered optimization.
- **Key Deliverables**: SVG optimization (Scour/SVGO) and quality scoring.
- [Detailed Tasks](./phase-5-quality-modes.md)

### ✅ Phase 6: Production & Deployment
- **Focus**: Monitoring, security, and cloud scalability.
- **Key Deliverables**: Kubernetes manifests, Prometheus/Grafana monitoring.
- [Detailed Tasks](./phase-6-production.md)

---

## 🚫 Discarded / Not Needed Phases

During exploration, certain phases were considered but ultimately set aside to maintain focus on the core mission of high-perf vectorization:

### Phase X: Native Mobile App (iOS/Android)
- **Reason**: The Next.js web application is fully responsive and covers 95% of use cases. A native app would add significant maintenance overhead without offering unique features.
- **Status**: Discarded.

### Phase Y: Blockchain Integration for SVG NFTs
- **Reason**: Market saturation and high environmental costs. The tool is designed for designers and developers, not specifically for the NFT space.
- **Status**: Not needed for core platform.

### Phase Z: Custom ML Model Training for Vectorization
- **Reason**: Existing tools like VTracer and AI-based preprocessing (NLM, Sharpening) already provide superior results with lower compute costs compared to training a scratch generative model.
- **Status**: Deferred indefinitely in favor of existing SOTA algorithms.

### Phase W: Real-time Collaborative SVG Editing
- **Reason**: This is a converter tool, not a full-blown design suite like Figma. Collaborative editing complicates the architecture without adding value to the conversion process.
- **Status**: Discarded.

---

## Future Roadmap (Planned)

1.  **Browser-based WebAssembly Engine**: Port the core engine to WASM for client-side processing to reduce server load.
2.  **Plugin Architecture**: Allow community-contributed preprocessing filters.
3.  **Enterprise Auth**: Integration with SSO/SAML for team accounts.

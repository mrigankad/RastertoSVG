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

### ✅ Phase 7: AI-Powered Vectorization Engine *(Completed — Q2 2026)*
- **Focus**: Deep learning integration for SOTA vectorization quality.
- **Key Deliverables**:
  - ✅ Smart Engine Selector (ML-based image classifier → engine routing)
  - ✅ AI Preprocessing Pipeline (noise detection, super-resolution, background removal)
  - ✅ DiffVG-inspired SVG Optimizer (gradient fills, path simplification, color quantization)
  - ✅ AI Vectorization Engine Orchestrator (unified 5-mode conversion pipeline)
  - ✅ API endpoints for AI analysis, conversion, preprocessing, and noise analysis
  - 🔄 SAM2 integration for semantic segmentation (depends on GPU availability)
- **New Services**: `ai_engine.py`, `smart_engine_selector.py`, `ai_preprocessing.py`, `diffvg_optimizer.py`
- **New Routes**: `/api/v1/ai/*` (8 endpoints)

### 🔨 Phase 8: WebAssembly Client-Side Engine *(In Progress — Q2-Q3 2026)*
- **Focus**: Client-side processing via WASM + PWA for offline/zero-latency conversion.
- **Key Deliverables**:
  - ✅ WASM Vector Engine (Web Worker execution, SIMD/threads detection, lazy loading)
  - ✅ Client-side Preprocessor (denoise, contrast, sharpen, color reduce, threshold — all in browser)
  - ✅ Hybrid Processing Router (auto-routing: WASM for <1MP, server for >5MP, adaptive for 1-5MP)
  - ✅ PWA Configuration (manifest, service worker, 4 caching strategies, background sync)
  - ✅ Offline page with WASM status detection
  - ✅ Zustand stores (WASM state, PWA state, preprocessing settings, performance stats)
  - ✅ AI API client (typed frontend client for all Phase 7 endpoints)
  - ✅ PWA hooks (service worker lifecycle, install prompt, online/offline detection)
- **New Frontend Files**: `wasm-engine.ts`, `client-preprocessor.ts`, `hybrid-processor.ts`, `wasm-store.ts`, `ai-api.ts`, `pwa-hooks.ts`
- **New Public Files**: `manifest.json`, `sw.js`

### 🔨 Phase 9: User Accounts & Cloud Platform *(In Progress — Q3 2026)*
- **Focus**: Transform from stateless tool to persistent platform with auth, projects, and cloud storage.
- **Key Deliverables**:
  - ✅ Database Models (User, Team, Project, Conversion, Preset, APIKey, Usage — SQLAlchemy async ORM)
  - ✅ Authentication Service (JWT access/refresh tokens, bcrypt passwords, API key generation)
  - ✅ OAuth 2.0 (Google, GitHub, Microsoft — code exchange + user creation)
  - ✅ Auth Middleware (JWT + API key auth, RBAC, plan-based feature gating)
  - ✅ Auth Routes (register, login, refresh, OAuth, email verify, password reset, profile, API keys)
  - ✅ Dashboard Routes (projects CRUD, conversions listing, presets CRUD, usage stats)
  - ✅ Cloud Storage Service (S3/R2/local abstraction, presigned URLs, quota tracking)
  - ✅ Database Session Management (async SQLAlchemy, auto-create tables on startup)
  - ✅ Plan Limits Matrix (Free/Pro/Team/Enterprise with quotas for conversions, storage, API calls)
- **New Backend Files**: `models/database.py`, `services/auth_service.py`, `services/cloud_storage.py`, `api/auth_routes.py`, `api/dashboard_routes.py`, `api/auth_middleware.py`, `database.py`

### 🔨 Phase 10: Multi-Format Export & Advanced Output *(In Progress — Q4 2026)*
- **Focus**: Export SVG to PDF, EPS, DXF, PNG + animation + accessibility.
- **Key Deliverables**:
  - ✅ Format Exporters (PDF via CairoSVG, EPS pure Python PostScript, DXF pure Python AutoCAD, PNG rasterized preview)
  - ✅ SVG Animation Engine (CSS keyframes, SMIL inline, Lottie JSON export — 7 animation types, 4 presets)
  - ✅ SVG Enhancer (responsive viewBox, WCAG accessibility, gradient defs, clipPath, minification, stats)
  - ✅ Export API Routes (10 endpoints: format listing, conversion, batch export, animation, enhancement)
  - ✅ Batch Export (export SVG to multiple formats in one request)
- **New Backend Files**: `services/format_exporters.py`, `services/svg_animator.py`, `services/svg_enhancer.py`, `api/export_routes.py`

### 🔨 Phase 11: Plugin Architecture & Marketplace *(In Progress — Q1 2027)*
- **Focus**: Extensible plugin system with community marketplace and template library.
- **Key Deliverables**:
  - ✅ Plugin SDK (4 base classes: Preprocessing, Vectorization, PostProcessing, Export)
  - ✅ Plugin Registry (discover, load, validate, execute with timing, install/uninstall lifecycle)
  - ✅ Plugin Manifest Schema (JSON manifest with settings schema, permissions, dependencies)
  - ✅ Marketplace Service (listings, reviews, ratings, download tracking, search, featured)
  - ✅ Community Templates (6 seeded templates: Clean Logo, Artistic Photo, Pixel Icon, Line Art, Technical Drawing, Rich Illustration)
  - ✅ Marketplace API (20 endpoints: plugin CRUD, marketplace search, reviews, templates)
  - ✅ Example Plugin (SVG Watermark — tiled text overlay with configurable position, rotation, color)
  - ✅ Hook System (event-driven plugin communication)
- **New Backend Files**: `services/plugin_sdk.py`, `services/marketplace.py`, `api/plugin_routes.py`
- **Example Plugin**: `storage/plugins/example-watermark/` (plugin.json + main.py)

### 🔨 Phase 12: Enterprise & Monetization *(In Progress — Q1–Q2 2027)*
- **Focus**: Stripe billing, subscription management, admin dashboard, audit logging, license keys.
- **Key Deliverables**:
  - ✅ Billing Models (Subscription, Invoice, AuditLog, LicenseKey with 4 pricing tiers)
  - ✅ Stripe Integration (customer creation, checkout sessions, subscription CRUD with proration, customer portal, invoices, metered usage, webhook verification)
  - ✅ Billing API (10 endpoints: plans, checkout, portal, subscription management, invoices, webhooks)
  - ✅ Admin Dashboard API (10 endpoints: platform stats, user management, audit logs, revenue metrics, conversion analytics, system health, license keys)
  - ✅ Audit Logger (25 action types with IP/user-agent tracking, buffered database writes)
  - ✅ License Key System (RSVG-XXXX format, hash-based validation, activation limits, expiry)
  - ✅ RBAC Admin Protection (superadmin + enterprise_admin gating on all admin endpoints)
  - ✅ Pricing Tiers ($9.99/mo Pro, $29.99/mo Team, $99.99/mo Enterprise with yearly discounts)
- **New Backend Files**: `models/billing.py`, `services/billing_service.py`, `api/billing_routes.py`, `api/admin_routes.py`

### ✨ Phase 13: Text-to-SVG & Generative Features *(In Progress — Q2 2027)*
- **Focus**: AI-assisted SVG creation, procedural patterns, geometric generation.
- **Key Deliverables**:
  - ✅ Icon Generator (45+ keywords mapped to procedural geometric logic with 4 style variants)
  - ✅ Pattern Generator (12 procedural patterns: stripes, dots, grid, waves, noise, gradient mesh, etc.)
  - ✅ Text Renderer (Multiline SVG text + styled headings with gradients/shadows/outlines)
  - ✅ Palette Generator (5 color theory schemes via HSL math: analogous, triadic, etc.)
  - ✅ SVG Compositor (Multi-layer stacking, mix-blend-mode, rotation, grouping)
  - ✅ API Routes (10 endpoints under `/api/v1/generate/` for all features)
- **New Backend Files**: `services/pattern_generator.py`, `services/text_to_svg.py`, `api/generative_routes.py`

### Phase 14 (see [plan.md](../plan.md))

| Phase | Name | Priority | Timeline |
|-------|------|----------|----------|
| 14 | Performance & Scale | Ongoing | All Phases |

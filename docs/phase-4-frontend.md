# Phase 4: Frontend Application

**Duration**: 3-4 weeks
**Goal**: Build responsive web interface for image conversion with real-time progress tracking

## Objectives

- Create modern React/Next.js web application
- Implement file upload with drag-and-drop
- Build conversion request interface with parameter controls
- Add real-time job status tracking
- Implement result preview and download
- Create responsive design for mobile/desktop
- Build conversion history and batch features

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Axios (HTTP client)
- Zustand (state management)
- React Query (data fetching)

## Architecture

```
Pages (Next.js App Router)
├── app/page.tsx (Home)
├── app/convert/page.tsx (Conversion)
├── app/history/page.tsx (History)
└── app/layout.tsx

Components
├── FileUpload
├── ConversionForm
├── ProgressTracker
├── ResultPreview
└── HistoryList

State (Zustand)
├── uploadStore
├── jobStore
└── historyStore

API Client
└── api/client.ts
```

## Tasks

### 4.1 Project Setup

- [ ] Create Next.js project:
  ```bash
  npx create-next-app@14 --typescript --tailwind
  ```

- [ ] Project structure:
  ```
  frontend/
  ├── app/
  │   ├── layout.tsx (root layout)
  │   ├── page.tsx (home)
  │   ├── convert/
  │   │   └── page.tsx
  │   ├── history/
  │   │   └── page.tsx
  │   └── api/ (optional: API routes for proxying)
  ├── components/
  │   ├── FileUpload.tsx
  │   ├── ConversionForm.tsx
  │   ├── ProgressTracker.tsx
  │   ├── ResultPreview.tsx
  │   ├── HistoryList.tsx
  │   └── Layout/
  │       ├── Header.tsx
  │       ├── Footer.tsx
  │       └── Navigation.tsx
  ├── lib/
  │   ├── api.ts (API client)
  │   ├── store.ts (Zustand stores)
  │   └── utils.ts
  ├── styles/
  │   └── globals.css
  ├── public/
  │   └── images/
  ├── package.json
  ├── tsconfig.json
  └── tailwind.config.ts
  ```

- [ ] Install dependencies:
  ```
  axios
  zustand
  @tanstack/react-query
  react-hot-toast
  lucide-react (icons)
  clsx
  ```

### 4.2 API Client

- [ ] Create `frontend/lib/api.ts`:
  ```typescript
  import axios from 'axios';

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const api = axios.create({
    baseURL: API_BASE,
  });

  export const apiClient = {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return api.post('/api/v1/upload', formData);
    },

    convert: (fileId: string, request: ConversionRequest) => {
      const formData = new FormData();
      formData.append('file_id', fileId);
      formData.append('request', JSON.stringify(request));
      return api.post('/api/v1/convert', formData);
    },

    getStatus: (jobId: string) => {
      return api.get(`/api/v1/status/${jobId}`);
    },

    downloadResult: (jobId: string) => {
      return api.get(`/api/v1/result/${jobId}`, {
        responseType: 'blob',
      });
    },
  };
  ```

### 4.3 State Management (Zustand)

- [ ] Create `frontend/lib/store.ts`:
  ```typescript
  import { create } from 'zustand';

  // Upload store
  export const useUploadStore = create((set) => ({
    file: null,
    fileId: null,
    isUploading: false,
    uploadProgress: 0,

    setFile: (file) => set({ file }),
    setFileId: (fileId) => set({ fileId }),
    setIsUploading: (isUploading) => set({ isUploading }),
    setUploadProgress: (uploadProgress) => set({ uploadProgress }),
  }));

  // Job store
  export const useJobStore = create((set) => ({
    jobs: {},
    currentJobId: null,

    addJob: (jobId, job) => set((state) => ({
      jobs: { ...state.jobs, [jobId]: job }
    })),

    updateJob: (jobId, update) => set((state) => ({
      jobs: { ...state.jobs, [jobId]: { ...state.jobs[jobId], ...update } }
    })),

    setCurrentJob: (jobId) => set({ currentJobId: jobId }),
  }));

  // History store
  export const useHistoryStore = create((set) => ({
    history: [],

    addToHistory: (item) => set((state) => ({
      history: [item, ...state.history].slice(0, 50) // Keep last 50
    })),

    loadHistory: () => {
      // Load from localStorage
    },

    clearHistory: () => set({ history: [] }),
  }));
  ```

### 4.4 Components

#### 4.4.1 FileUpload Component
- [ ] Create `components/FileUpload.tsx`:
  ```typescript
  export function FileUpload() {
    const [isDragging, setIsDragging] = useState(false);
    const { setFile, setFileId, setIsUploading } = useUploadStore();

    const handleDrop = async (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && isValidImageFormat(file)) {
        await uploadFile(file);
      }
    };

    const uploadFile = async (file: File) => {
      setIsUploading(true);
      try {
        const response = await apiClient.upload(file);
        setFile(file);
        setFileId(response.data.file_id);
      } finally {
        setIsUploading(false);
      }
    };

    // Render: drag-and-drop zone, file input, file preview
  }
  ```

Features:
- Drag-and-drop zone
- Click to select file
- File preview (thumbnail)
- Format validation
- File size validation
- Upload progress bar

#### 4.4.2 ConversionForm Component
- [ ] Create `components/ConversionForm.tsx`:
  ```typescript
  export function ConversionForm() {
    const [imageType, setImageType] = useState<'auto' | 'color' | 'monochrome'>('auto');
    const [qualityMode, setQualityMode] = useState<'fast' | 'standard' | 'high'>('standard');
    const [colorPalette, setColorPalette] = useState(32);
    const [denoiseStrength, setDenoiseStrength] = useState('medium');

    const handleConvert = async () => {
      const response = await apiClient.convert(fileId, {
        image_type: imageType,
        quality_mode: qualityMode,
        color_palette: colorPalette,
        denoise_strength: denoiseStrength,
      });
      // Handle response
    };

    // Render: form fields, submit button
  }
  ```

Features:
- Image type selector (radio buttons)
- Quality mode selector (segmented control)
- Advanced options (collapsible)
- Color palette slider
- Denoise strength dropdown
- Preview of selected options
- Submit button

#### 4.4.3 ProgressTracker Component
- [ ] Create `components/ProgressTracker.tsx`:
  ```typescript
  export function ProgressTracker({ jobId }: { jobId: string }) {
    const [job, setJob] = useState(null);

    useEffect(() => {
      const interval = setInterval(async () => {
        const response = await apiClient.getStatus(jobId);
        setJob(response.data);

        if (response.data.status === 'completed' ||
            response.data.status === 'failed') {
          clearInterval(interval);
        }
      }, 1000);

      return () => clearInterval(interval);
    }, [jobId]);

    // Render: progress bar, status text, elapsed time
  }
  ```

Features:
- Real-time status polling
- Progress bar (0-100%)
- Status text updates
- Estimated time remaining
- Elapsed time counter
- Error display if failed
- Auto-stop polling when complete

#### 4.4.4 ResultPreview Component
- [ ] Create `components/ResultPreview.tsx`:
  ```typescript
  export function ResultPreview({ jobId }: { jobId: string }) {
    const [svgContent, setSvgContent] = useState('');

    useEffect(() => {
      const response = await apiClient.getStatus(jobId);
      if (response.data.status === 'completed') {
        // Fetch SVG content
        const svg = await fetch(response.data.result_url).then(r => r.text());
        setSvgContent(svg);
      }
    }, [jobId]);

    // Render: SVG preview, zoom controls, download button
  }
  ```

Features:
- Display SVG preview
- Zoom in/out
- Pan/drag functionality
- View SVG source code
- Download button
- Copy SVG code to clipboard
- Share result

#### 4.4.5 HistoryList Component
- [ ] Create `components/HistoryList.tsx`:
  ```typescript
  export function HistoryList() {
    const { history } = useHistoryStore();

    // Render: list of past conversions with thumbnails and metadata
  }
  ```

Features:
- List of past conversions
- Thumbnail preview
- File name and size
- Conversion date/time
- Quality mode used
- Ability to re-download
- Delete individual items
- Clear all history

### 4.5 Pages

#### 4.5.1 Home Page
- [ ] Create `app/page.tsx`:
  - Hero section with feature highlights
  - Quick start guide
  - Feature showcase
  - Links to convert and history pages

#### 4.5.2 Conversion Page
- [ ] Create `app/convert/page.tsx`:
  - Multi-step workflow:
    1. Upload file
    2. Select options
    3. Convert (show progress)
    4. Download result

#### 4.5.3 History Page
- [ ] Create `app/history/page.tsx`:
  - Display conversion history
  - Filter by date, quality mode
  - Sort by newest/oldest
  - Search by filename
  - Batch download

#### 4.5.4 Layout
- [ ] Create `app/layout.tsx`:
  - Navigation header
  - Footer
  - Global styles
  - Metadata

### 4.6 Styling & UI

- [ ] Tailwind configuration:
  - Color scheme
  - Typography
  - Component classes
  - Responsive breakpoints

- [ ] Design system:
  - Button styles (primary, secondary, outline)
  - Input styles
  - Card styles
  - Modal styles
  - Alert styles
  - Toast notifications

- [ ] Responsive design:
  - Mobile first approach
  - Tablet layout
  - Desktop layout
  - Touch-friendly controls

### 4.7 Features & Polish

#### 4.7.1 Error Handling
- [ ] Display user-friendly error messages
- [ ] Retry failed conversions
- [ ] Validation error messages
- [ ] Network error handling
- [ ] Timeout handling

#### 4.7.2 User Feedback
- [ ] Toast notifications (success, error, info)
- [ ] Loading skeletons
- [ ] Confirmation dialogs
- [ ] Help tooltips
- [ ] Empty states

#### 4.7.3 Performance
- [ ] Image optimization
- [ ] Code splitting
- [ ] Lazy loading of components
- [ ] Debounced API calls
- [ ] LocalStorage for state persistence

#### 4.7.4 Accessibility
- [ ] ARIA labels
- [ ] Keyboard navigation
- [ ] Color contrast
- [ ] Focus indicators
- [ ] Form labels

#### 4.7.5 SEO
- [ ] Meta tags
- [ ] Open Graph tags
- [ ] Structured data
- [ ] Sitemap
- [ ] Robots.txt

### 4.8 Environment Configuration

- [ ] Create `.env.example`:
  ```
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_APP_NAME="Raster to SVG"
  NEXT_PUBLIC_APP_VERSION=1.0.0
  ```

- [ ] Configure for different environments:
  - Development: localhost:3000 → localhost:8000
  - Staging: staging.app.com → staging-api.app.com
  - Production: app.com → api.app.com

### 4.9 Testing

- [ ] Create test suite:
  - Component tests (React Testing Library)
  - Integration tests (Cypress or Playwright)
  - Accessibility tests

- [ ] Test files:
  - `__tests__/FileUpload.test.tsx`
  - `__tests__/ConversionForm.test.tsx`
  - `__tests__/ProgressTracker.test.tsx`

### 4.10 Documentation

- [ ] Create `FRONTEND.md`:
  - Project structure
  - Component documentation
  - State management guide
  - API integration guide
  - Development workflow

- [ ] Component storybook (optional):
  - Interactive component preview
  - Prop variations
  - Usage examples

## Deliverables

- ✅ Next.js application with App Router
- ✅ All major pages and components
- ✅ API client fully integrated
- ✅ State management with Zustand
- ✅ Responsive design (mobile/tablet/desktop)
- ✅ Real-time progress tracking
- ✅ Error handling and user feedback
- ✅ Conversion history
- ✅ Full documentation
- ✅ Test suite

## Success Criteria

- [ ] All pages load quickly (<2s)
- [ ] File upload works reliably
- [ ] Conversion request accepted and processed
- [ ] Progress tracking shows in real-time
- [ ] Result downloads successfully
- [ ] Mobile responsive design works
- [ ] Error messages clear and helpful
- [ ] Tests pass with good coverage
- [ ] Accessibility standards met
- [ ] SEO optimized

## Performance Targets

- Initial page load: < 2s
- Time to interactive: < 3s
- Lighthouse score: > 90
- Core Web Vitals: All green

## Next Phase

→ [Phase 5: Quality Modes & Optimization](./phase-5-quality-modes.md)

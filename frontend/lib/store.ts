import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { JobStatus, ConversionRequest } from './api';

// Upload Store
interface UploadState {
  file: File | null;
  fileId: string | null;
  isUploading: boolean;
  uploadProgress: number;
  error: string | null;
  setFile: (file: File | null) => void;
  setFileId: (fileId: string | null) => void;
  setIsUploading: (isUploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  file: null,
  fileId: null,
  isUploading: false,
  uploadProgress: 0,
  error: null,
  setFile: (file) => set({ file, error: null }),
  setFileId: (fileId) => set({ fileId }),
  setIsUploading: (isUploading) => set({ isUploading }),
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  setError: (error) => set({ error }),
  reset: () => set({
    file: null,
    fileId: null,
    isUploading: false,
    uploadProgress: 0,
    error: null,
  }),
}));

// Conversion Options Store
interface ConversionOptionsState extends ConversionRequest {
  setImageType: (type: ConversionRequest['image_type']) => void;
  setQualityMode: (mode: ConversionRequest['quality_mode']) => void;
  setColorPalette: (palette: number) => void;
  setDenoiseStrength: (strength: string) => void;
  reset: () => void;
}

export const useConversionOptionsStore = create<ConversionOptionsState>((set) => ({
  image_type: 'auto',
  quality_mode: 'standard',
  color_palette: 32,
  denoise_strength: 'medium',
  setImageType: (image_type) => set({ image_type }),
  setQualityMode: (quality_mode) => set({ quality_mode }),
  setColorPalette: (color_palette) => set({ color_palette }),
  setDenoiseStrength: (denoise_strength) => set({ denoise_strength }),
  reset: () => set({
    image_type: 'auto',
    quality_mode: 'standard',
    color_palette: 32,
    denoise_strength: 'medium',
  }),
}));

// Job Store
interface ActiveJob {
  jobId: string;
  fileName: string;
  status: JobStatus['status'];
  progress: number;
  error: string | null;
  resultUrl: string | null;
  createdAt: string;
  completedAt: string | null;
  processingTime: number | null;
}

interface JobState {
  activeJobs: Record<string, ActiveJob>;
  currentJobId: string | null;
  addJob: (job: ActiveJob) => void;
  updateJob: (jobId: string, updates: Partial<ActiveJob>) => void;
  removeJob: (jobId: string) => void;
  setCurrentJob: (jobId: string | null) => void;
  getJob: (jobId: string) => ActiveJob | undefined;
  clearCompleted: () => void;
}

export const useJobStore = create<JobState>((set, get) => ({
  activeJobs: {},
  currentJobId: null,
  addJob: (job) =>
    set((state) => ({
      activeJobs: { ...state.activeJobs, [job.jobId]: job },
    })),
  updateJob: (jobId, updates) =>
    set((state) => ({
      activeJobs: {
        ...state.activeJobs,
        [jobId]: { ...state.activeJobs[jobId], ...updates },
      },
    })),
  removeJob: (jobId) =>
    set((state) => {
      const { [jobId]: _, ...rest } = state.activeJobs;
      return { activeJobs: rest };
    }),
  setCurrentJob: (jobId) => set({ currentJobId: jobId }),
  getJob: (jobId) => get().activeJobs[jobId],
  clearCompleted: () =>
    set((state) => {
      const activeJobs = Object.entries(state.activeJobs).reduce(
        (acc, [id, job]) => {
          if (job.status !== 'completed' && job.status !== 'failed') {
            acc[id] = job;
          }
          return acc;
        },
        {} as Record<string, ActiveJob>
      );
      return { activeJobs };
    }),
}));

// History Item (persisted)
interface HistoryItem {
  id: string;
  fileName: string;
  fileSize: number;
  quality: string;
  imageType: string;
  status: 'completed' | 'failed';
  createdAt: string;
  completedAt: string;
  processingTime?: number;
}

interface HistoryState {
  history: HistoryItem[];
  addToHistory: (item: HistoryItem) => void;
  removeFromHistory: (id: string) => void;
  clearHistory: () => void;
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set) => ({
      history: [],
      addToHistory: (item) =>
        set((state) => ({
          history: [item, ...state.history].slice(0, 100), // Keep last 100
        })),
      removeFromHistory: (id) =>
        set((state) => ({
          history: state.history.filter((item) => item.id !== id),
        })),
      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'conversion-history',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// UI Store
interface UIState {
  isSidebarOpen: boolean;
  theme: 'light' | 'dark';
  toast: {
    message: string;
    type: 'success' | 'error' | 'info';
    visible: boolean;
  } | null;
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
  showToast: (message: string, type: 'success' | 'error' | 'info') => void;
  hideToast: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarOpen: false,
  theme: 'light',
  toast: null,
  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setTheme: (theme) => set({ theme }),
  toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
  showToast: (message, type) => set({ toast: { message, type, visible: true } }),
  hideToast: () => set({ toast: null }),
}));

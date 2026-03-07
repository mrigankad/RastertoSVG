import axios, { AxiosProgressEvent } from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: {
    'Accept': 'application/json',
  },
});

// Request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    return Promise.reject(new Error(message));
  }
);

export interface ConversionRequest {
  image_type: 'auto' | 'color' | 'monochrome';
  quality_mode: 'fast' | 'standard' | 'high';
  color_palette?: number;
  denoise_strength?: string;
}

export interface UploadResponse {
  file_id: string;
  filename: string;
  size: number;
  format: string;
}

export interface ConversionResponse {
  job_id: string;
  status: string;
  created_at: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error: string | null;
  result_url: string | null;
  created_at: string;
  completed_at: string | null;
  processing_time: number | null;
  options?: ConversionRequest;
}

export interface BatchConversionRequest {
  file_ids: string[];
  options: ConversionRequest;
}

export interface BatchConversionResponse {
  batch_id: string;
  job_ids: string[];
  total: number;
}

export interface StorageStats {
  uploads: {
    count: number;
    size_mb: number;
  };
  results: {
    count: number;
    size_mb: number;
  };
  total_size_mb: number;
}

export interface QueueStats {
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface HealthCheck {
  status: string;
  version: string;
  timestamp: string;
}

export const apiClient = {
  // Upload
  upload: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    return response.data;
  },

  // Convert
  convert: async (
    fileId: string,
    request: ConversionRequest
  ): Promise<ConversionResponse> => {
    const formData = new FormData();
    formData.append('file_id', fileId);
    formData.append('image_type', request.image_type);
    formData.append('quality_mode', request.quality_mode);
    if (request.color_palette) {
      formData.append('color_palette', request.color_palette.toString());
    }
    if (request.denoise_strength) {
      formData.append('denoise_strength', request.denoise_strength);
    }

    const response = await api.post('/convert', formData);
    return response.data;
  },

  // Get status
  getStatus: async (jobId: string): Promise<JobStatus> => {
    const response = await api.get(`/status/${jobId}`);
    return response.data;
  },

  // Download result
  downloadResult: async (jobId: string): Promise<Blob> => {
    const response = await api.get(`/result/${jobId}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Batch convert
  batchConvert: async (
    fileIds: string[],
    options: ConversionRequest
  ): Promise<BatchConversionResponse> => {
    const response = await api.post('/batch', {
      file_ids: fileIds,
      options,
    });
    return response.data;
  },

  // List jobs
  listJobs: async (params?: { status?: string; limit?: number }): Promise<{
    jobs: JobStatus[];
    count: number;
    limit: number;
    offset: number;
  }> => {
    const response = await api.get('/jobs', { params });
    return response.data;
  },

  // Delete job
  deleteJob: async (jobId: string): Promise<{ status: string; job_id: string }> => {
    const response = await api.delete(`/jobs/${jobId}`);
    return response.data;
  },

  // Storage stats
  getStorageStats: async (): Promise<StorageStats> => {
    const response = await api.get('/storage/stats');
    return response.data;
  },

  // Queue stats
  getQueueStats: async (): Promise<QueueStats> => {
    const response = await api.get('/queue/stats');
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<HealthCheck> => {
    const response = await api.get('/health');
    return response.data;
  },

  // Cleanup storage
  cleanupStorage: async (days: number = 30): Promise<{ status: string; days: number }> => {
    const response = await api.post(`/storage/cleanup?days=${days}`);
    return response.data;
  },
};

// Poll job status until completion
export const pollJobStatus = async (
  jobId: string,
  onUpdate: (status: JobStatus) => void,
  onComplete?: (status: JobStatus) => void,
  onError?: (error: string) => void,
  interval: number = 1000
): Promise<() => void> => {
  let isActive = true;

  const poll = async () => {
    if (!isActive) return;

    try {
      const status = await apiClient.getStatus(jobId);
      onUpdate(status);

      if (status.status === 'completed') {
        onComplete?.(status);
        return;
      } else if (status.status === 'failed') {
        onError?.(status.error || 'Conversion failed');
        return;
      }

      // Continue polling
      setTimeout(poll, interval);
    } catch (error) {
      onError?.(error instanceof Error ? error.message : 'Unknown error');
    }
  };

  poll();

  // Return cleanup function
  return () => {
    isActive = false;
  };
};

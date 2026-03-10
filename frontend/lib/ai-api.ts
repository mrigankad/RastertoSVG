/**
 * AI Engine API client — Phase 7 frontend integration.
 *
 * Provides typed methods for all /api/v1/ai/* endpoints:
 * - Image analysis & engine recommendation
 * - AI-powered conversion
 * - Preprocessing preview
 * - Background removal
 * - Noise analysis
 * - Engine capabilities
 */

import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const API_BASE = (typeof process !== 'undefined' && (process as any).env?.NEXT_PUBLIC_API_URL) || 'http://localhost:8000';

const aiApi = axios.create({
    baseURL: `${API_BASE}/api/v1/ai`,
    headers: { 'Accept': 'application/json' },
});

aiApi.interceptors.response.use(
    (response) => response,
    (error) => {
        const message = error.response?.data?.detail || error.message || 'AI Engine error';
        return Promise.reject(new Error(message));
    }
);

// =============================================================================
// Types 
// =============================================================================

export interface ImageFeatureReport {
    dimensions: string;
    megapixels: number;
    is_grayscale: boolean;
    unique_colors: number;
    dominant_colors: number;
    color_complexity: number;
    edge_density: number;
    texture_energy: number;
    noise_level: number;
    contour_count: number;
}

export interface EngineRecommendation {
    engine: string;
    confidence: number;
    category: string;
    reasoning: string;
    alternative: string | null;
    estimated_quality: number;
    estimated_time: number;
    suggested_params: Record<string, any>;
    preprocessing_hints: string[];
}

export interface NoiseAnalysis {
    noise_score: number;
    noise_type: string;
    recommendation: Record<string, any>;
}

export interface ImageAnalysisResult {
    recommendation: EngineRecommendation;
    features: ImageFeatureReport;
    noise: NoiseAnalysis;
    capabilities: Record<string, any>;
}

export interface AIConversionRequest {
    file_id: string;
    mode?: 'auto' | 'speed' | 'balanced' | 'quality' | 'max_quality';
    engine_override?: string;
    enable_ai_preprocessing?: boolean;
    enable_sam?: boolean;
    enable_optimization?: boolean;
    enable_gradients?: boolean;
    enable_upscale?: boolean;
    enable_bg_removal?: boolean;
    custom_params?: Record<string, any>;
    webhook_url?: string;
    generate_preview?: boolean;
}

export interface AIConversionResult {
    job_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    engine_used: string | null;
    category_detected: string | null;
    confidence: number | null;
    mode: string;
    ai_features_used: string[];
    preprocessing_steps: string[];
    output_url: string | null;
    output_size_bytes: number | null;
    timings: {
        load?: number;
        analysis?: number;
        ai_preprocessing?: number;
        sam_segmentation?: number;
        conversion?: number;
        optimization?: number;
    } | null;
    total_time: number | null;
    created_at: string;
}

export interface AIPreprocessRequest {
    file_id: string;
    enable_denoise?: boolean;
    enable_upscale?: boolean;
    enable_bg_removal?: boolean;
    enable_contrast?: boolean;
    enable_sharpen?: boolean;
    upscale_factor?: number;
    min_dimension?: number;
}

export interface AIPreprocessResult {
    preview_id: string;
    file_id: string;
    original_url: string;
    processed_url: string;
    steps_applied: string[];
    noise_analysis: Record<string, any> | null;
    processing_time: number;
    original_size: { width: number; height: number };
    processed_size: { width: number; height: number };
}

export interface BackgroundRemovalRequest {
    file_id: string;
    method?: 'auto' | 'grabcut' | 'color' | 'edge';
    threshold?: number;
}

export interface BackgroundRemovalResult {
    preview_id: string;
    file_id: string;
    original_url: string;
    processed_url: string;
    method_used: string;
    mask_coverage: number;
    processing_time: number;
}

export interface NoiseAnalysisResult {
    file_id: string;
    noise_score: number;
    noise_type: string;
    laplacian_variance: number;
    mad_noise: number;
    local_noise: number;
    high_freq_noise: number;
    recommendation: Record<string, any>;
}

export interface EngineCapability {
    id: string;
    name: string;
    description: string;
    best_for: string[];
    color_support: boolean;
    speed: string;
    quality_range: string;
    requires_gpu: boolean;
}

export interface AICapabilities {
    engines: Record<string, any>;
    ai_preprocessing: Record<string, any>;
    diffvg_optimizer: Record<string, any>;
    sam_available: boolean;
    modes: Record<string, string>;
}

// =============================================================================
// API Client
// =============================================================================

export const aiApiClient = {
    /**
     * Analyze an image and get engine recommendations.
     */
    analyzeImage: async (fileId: string): Promise<ImageAnalysisResult> => {
        const res = await aiApi.post(`/analyze/${fileId}`);
        return res.data;
    },

    /**
     * Start AI-powered conversion.
     */
    convert: async (request: AIConversionRequest): Promise<AIConversionResult> => {
        const res = await aiApi.post('/convert', request);
        return res.data;
    },

    /**
     * Download AI conversion result as SVG blob.
     */
    downloadResult: async (jobId: string): Promise<Blob> => {
        const res = await aiApi.get(`/result/${jobId}`, { responseType: 'blob' });
        return res.data;
    },

    /**
     * Apply AI preprocessing (returns preview URLs).
     */
    preprocess: async (request: AIPreprocessRequest): Promise<AIPreprocessResult> => {
        const res = await aiApi.post('/preprocess', request);
        return res.data;
    },

    /**
     * Get AI preprocessing preview image.
     */
    getPreviewUrl: (previewId: string, type: 'original' | 'processed'): string => {
        return `${API_BASE}/api/v1/ai/preview/${previewId}/${type}`;
    },

    /**
     * Remove background from image.
     */
    removeBackground: async (request: BackgroundRemovalRequest): Promise<BackgroundRemovalResult> => {
        const res = await aiApi.post('/remove-background', request);
        return res.data;
    },

    /**
     * Analyze image noise levels.
     */
    analyzeNoise: async (fileId: string): Promise<NoiseAnalysisResult> => {
        const res = await aiApi.post(`/noise-analysis/${fileId}`);
        return res.data;
    },

    /**
     * Get AI engine capabilities.
     */
    getCapabilities: async (): Promise<AICapabilities> => {
        const res = await aiApi.get('/capabilities');
        return res.data;
    },

    /**
     * Get available vectorization engines.
     */
    getEngines: async (): Promise<{ engines: EngineCapability[]; categories: string[] }> => {
        const res = await aiApi.get('/engines');
        return res.data;
    },
};

/**
 * Advanced API client for granular control endpoints
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// =============================================================================
// Types
// =============================================================================

export interface FilterInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'noise' | 'enhance' | 'color' | 'transform' | 'edge';
  default_params: Record<string, any>;
  param_schema: Record<string, any>;
}

export interface PreprocessingStep {
  id: string;
  name: string;
  enabled: boolean;
  order: number;
  params: Record<string, any>;
}

export interface PreprocessingPipeline {
  steps: PreprocessingStep[];
}

export interface ColorInfo {
  hex: string;
  rgb: number[];
  percentage?: number;
}

export interface ColorPaletteConfig {
  mode: 'auto' | 'extract' | 'custom' | 'preserve';
  max_colors: number;
  extracted_colors: string[];
  custom_colors: string[];
  dithering: 'none' | 'floyd_steinberg' | 'bayer' | 'atkinson' | 'ordered';
  preserve_transparency: boolean;
}

export interface VectorizationParams {
  engine: 'vtracer' | 'potrace' | 'auto';
  curve_fitting: 'auto' | 'tight' | 'smooth';
  corner_threshold: number;
  path_precision: number;
  color_mode: 'color' | 'monochrome' | 'grayscale';
  hierarchical: boolean;
  simplify_paths: boolean;
  smooth_corners: boolean;
  remove_small_paths: boolean;
  min_path_area: number;
}

export interface SVGOutputConfig {
  viewbox_mode: 'auto' | 'custom' | 'percentage';
  custom_width?: number;
  custom_height?: number;
  style_mode: 'inline' | 'css' | 'attributes';
  add_classes: boolean;
  class_prefix: string;
  optimization_level: 'none' | 'light' | 'standard' | 'aggressive';
  precision: number;
  remove_metadata: boolean;
  minify: boolean;
  id_prefix?: string;
  reuse_paths: boolean;
}

export interface ConversionPreset {
  id: string;
  name: string;
  description: string;
  category: 'built_in' | 'user' | 'shared';
  tags: string[];
  preview_image?: string;
  control_level: 1 | 2 | 3;
  preprocessing?: PreprocessingPipeline;
  palette_config?: ColorPaletteConfig;
  vectorization?: VectorizationParams;
  output_config?: SVGOutputConfig;
  quality_mode?: 'fast' | 'standard' | 'high';
  image_type?: 'auto' | 'color' | 'monochrome';
  color_palette?: number;
}

export interface PreviewResponse {
  preview_id: string;
  file_id: string;
  original_url: string;
  processed_url: string;
  processing_time: number;
  expires_at: string;
  dimensions: { width: number; height: number };
}

export interface ImageAnalysisResult {
  file_id: string;
  is_photo: boolean;
  is_line_art: boolean;
  has_text: boolean;
  color_complexity: number;
  unique_colors: number;
  noise_level: number;
  brightness: number;
  contrast: number;
  sharpness: number;
  recommended_mode: 'fast' | 'standard' | 'high';
  suggested_filters: string[];
}

export interface EnhancedConversionRequest {
  file_id: string;
  control_level: 1 | 2 | 3;
  quality_mode?: 'fast' | 'standard' | 'high';
  image_type?: 'auto' | 'color' | 'monochrome';
  color_palette?: number;
  denoise_strength?: 'light' | 'medium' | 'heavy';
  preset_id?: string;
  preprocessing?: PreprocessingPipeline;
  palette_config?: ColorPaletteConfig;
  vectorization?: VectorizationParams;
  output_config?: SVGOutputConfig;
  generate_preview?: boolean;
  webhook_url?: string;
}

export interface EnhancedConversionResponse {
  job_id: string;
  status: string;
  preview_job_id?: string;
  created_at: string;
  estimated_time?: number;
}

export interface ComparisonResult {
  mode: string;
  job_id: string;
  preview_url: string;
  svg_url?: string;
  file_size?: number;
  processing_time?: number;
  metrics?: Record<string, number>;
}

export interface ComparisonResponse {
  comparison_id: string;
  file_id: string;
  results: ComparisonResult[];
  created_at: string;
}

// =============================================================================
// API Client
// =============================================================================

export const advancedApi = {
  // Filters
  async getFilters(): Promise<{ filters: FilterInfo[]; categories: string[] }> {
    const response = await fetch(`${API_URL}/api/v1/advanced/filters`);
    if (!response.ok) throw new Error('Failed to fetch filters');
    return response.json();
  },

  // Preview
  async createPreview(
    fileId: string,
    pipeline?: PreprocessingPipeline,
    maxDimension: number = 400,
    stepId?: string
  ): Promise<PreviewResponse> {
    const response = await fetch(`${API_URL}/api/v1/advanced/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_id: fileId,
        preprocessing: pipeline,
        max_dimension: maxDimension,
        step_id: stepId,
      }),
    });
    if (!response.ok) throw new Error('Failed to create preview');
    return response.json();
  },

  getPreviewUrl(previewId: string, type: 'original' | 'processed'): string {
    return `${API_URL}/api/v1/advanced/preview/${previewId}/${type}`;
  },

  // Color Extraction
  async extractColors(fileId: string, maxColors: number = 32): Promise<{
    file_id: string;
    max_colors: number;
    palette: ColorInfo[];
    total_colors: number;
  }> {
    const response = await fetch(
      `${API_URL}/api/v1/advanced/extract-colors/${fileId}?max_colors=${maxColors}`,
      { method: 'POST' }
    );
    if (!response.ok) throw new Error('Failed to extract colors');
    return response.json();
  },

  // Image Analysis
  async analyzeImage(fileId: string, detailed: boolean = false): Promise<ImageAnalysisResult> {
    const response = await fetch(
      `${API_URL}/api/v1/advanced/analyze/${fileId}?detailed=${detailed}`,
      { method: 'POST' }
    );
    if (!response.ok) throw new Error('Failed to analyze image');
    return response.json();
  },

  // Presets
  async getPresets(category?: string, search?: string): Promise<{
    presets: ConversionPreset[];
    total: number;
    categories: string[];
  }> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (search) params.append('search', search);
    
    const response = await fetch(`${API_URL}/api/v1/advanced/presets?${params}`);
    if (!response.ok) throw new Error('Failed to fetch presets');
    return response.json();
  },

  async getPreset(presetId: string): Promise<ConversionPreset> {
    const response = await fetch(`${API_URL}/api/v1/advanced/presets/${presetId}`);
    if (!response.ok) throw new Error('Failed to fetch preset');
    return response.json();
  },

  async createPreset(preset: ConversionPreset): Promise<ConversionPreset> {
    const response = await fetch(`${API_URL}/api/v1/advanced/presets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preset),
    });
    if (!response.ok) throw new Error('Failed to create preset');
    return response.json();
  },

  async updatePreset(presetId: string, preset: ConversionPreset): Promise<ConversionPreset> {
    const response = await fetch(`${API_URL}/api/v1/advanced/presets/${presetId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preset),
    });
    if (!response.ok) throw new Error('Failed to update preset');
    return response.json();
  },

  async deletePreset(presetId: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/advanced/presets/${presetId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete preset');
  },

  // Enhanced Conversion
  async enhancedConvert(request: EnhancedConversionRequest): Promise<EnhancedConversionResponse> {
    const response = await fetch(`${API_URL}/api/v1/advanced/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Conversion failed');
    }
    return response.json();
  },

  // Comparison
  async createComparison(
    fileId: string,
    modes: ('fast' | 'standard' | 'high' | 'custom')[],
    customConfig?: any
  ): Promise<ComparisonResponse> {
    const response = await fetch(`${API_URL}/api/v1/advanced/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_id: fileId,
        modes,
        custom_config: customConfig,
        include_metrics: true,
      }),
    });
    if (!response.ok) throw new Error('Failed to create comparison');
    return response.json();
  },

  // Default Pipeline
  async getDefaultPipeline(
    qualityMode: string,
    imageType: string = 'auto'
  ): Promise<{
    quality_mode: string;
    image_type: string;
    pipeline: PreprocessingPipeline;
  }> {
    const response = await fetch(
      `${API_URL}/api/v1/advanced/pipeline/defaults/${qualityMode}?image_type=${imageType}`
    );
    if (!response.ok) throw new Error('Failed to fetch default pipeline');
    return response.json();
  },
};

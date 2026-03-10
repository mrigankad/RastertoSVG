/**
 * Advanced control state management using Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  ConversionPreset,
  FilterInfo,
  PreprocessingPipeline,
  PreprocessingStep,
  ColorPaletteConfig,
  VectorizationParams,
  SVGOutputConfig,
} from './advanced-api';

// =============================================================================
// Control Level State
// =============================================================================

export type ControlLevel = 1 | 2 | 3;

interface ControlLevelState {
  level: ControlLevel;
  setLevel: (level: ControlLevel) => void;
}

export const useControlLevelStore = create<ControlLevelState>()(
  persist(
    (set) => ({
      level: 2, // Default to guided control
      setLevel: (level) => set({ level }),
    }),
    {
      name: 'control-level',
    }
  )
);

// =============================================================================
// Advanced Conversion Options State
// =============================================================================

interface AdvancedConversionState {
  // Control level 2 options
  qualityMode: 'fast' | 'standard' | 'high';
  imageType: 'auto' | 'color' | 'monochrome';
  colorPalette: number;
  denoiseStrength: 'light' | 'medium' | 'heavy';

  // Control level 3 options
  selectedPresetId: string | null;
  preprocessing: PreprocessingPipeline;
  paletteConfig: ColorPaletteConfig;
  vectorization: VectorizationParams;
  outputConfig: SVGOutputConfig;

  // Actions
  setQualityMode: (mode: 'fast' | 'standard' | 'high') => void;
  setImageType: (type: 'auto' | 'color' | 'monochrome') => void;
  setColorPalette: (palette: number) => void;
  setDenoiseStrength: (strength: 'light' | 'medium' | 'heavy') => void;
  setSelectedPreset: (presetId: string | null) => void;

  // Preprocessing actions
  setPreprocessing: (pipeline: PreprocessingPipeline) => void;
  addPreprocessingStep: (step: PreprocessingStep) => void;
  updatePreprocessingStep: (stepId: string, updates: Partial<PreprocessingStep>) => void;
  removePreprocessingStep: (stepId: string) => void;
  movePreprocessingStep: (stepId: string, direction: 'up' | 'down') => void;
  togglePreprocessingStep: (stepId: string) => void;

  // Advanced config actions
  setPaletteConfig: (config: ColorPaletteConfig) => void;
  setVectorization: (params: VectorizationParams) => void;
  setOutputConfig: (config: SVGOutputConfig) => void;

  // Reset
  resetToDefaults: () => void;
  applyPreset: (preset: ConversionPreset) => void;
}

const defaultPreprocessing: PreprocessingPipeline = {
  steps: [],
};

const defaultPaletteConfig: ColorPaletteConfig = {
  mode: 'auto',
  max_colors: 32,
  extracted_colors: [],
  custom_colors: [],
  dithering: 'none',
  preserve_transparency: true,
};

const defaultVectorization: VectorizationParams = {
  engine: 'auto',
  curve_fitting: 'auto',
  corner_threshold: 60,
  path_precision: 2,
  color_mode: 'color',
  hierarchical: true,
  simplify_paths: true,
  smooth_corners: true,
  remove_small_paths: true,
  min_path_area: 5,
};

const defaultOutputConfig: SVGOutputConfig = {
  viewbox_mode: 'auto',
  style_mode: 'inline',
  add_classes: false,
  class_prefix: 'path-',
  optimization_level: 'standard',
  precision: 2,
  remove_metadata: true,
  minify: false,
  reuse_paths: true,
};

export const useAdvancedConversionStore = create<AdvancedConversionState>()(
  persist(
    (set, get) => ({
      // Level 2 defaults
      qualityMode: 'standard',
      imageType: 'auto',
      colorPalette: 32,
      denoiseStrength: 'medium',

      // Level 3 defaults
      selectedPresetId: null,
      preprocessing: defaultPreprocessing,
      paletteConfig: defaultPaletteConfig,
      vectorization: defaultVectorization,
      outputConfig: defaultOutputConfig,

      // Actions
      setQualityMode: (qualityMode) => set({ qualityMode }),
      setImageType: (imageType) => set({ imageType }),
      setColorPalette: (colorPalette) => set({ colorPalette }),
      setDenoiseStrength: (denoiseStrength) => set({ denoiseStrength }),
      setSelectedPreset: (selectedPresetId) => set({ selectedPresetId }),

      // Preprocessing actions
      setPreprocessing: (preprocessing) => set({ preprocessing }),

      addPreprocessingStep: (step) =>
        set((state) => ({
          preprocessing: {
            steps: [...state.preprocessing.steps, step].sort((a, b) => a.order - b.order),
          },
        })),

      updatePreprocessingStep: (stepId, updates) =>
        set((state) => ({
          preprocessing: {
            steps: state.preprocessing.steps.map((step) =>
              step.id === stepId ? { ...step, ...updates } : step
            ),
          },
        })),

      removePreprocessingStep: (stepId) =>
        set((state) => ({
          preprocessing: {
            steps: state.preprocessing.steps.filter((step) => step.id !== stepId),
          },
        })),

      movePreprocessingStep: (stepId, direction) =>
        set((state) => {
          const steps = [...state.preprocessing.steps];
          const index = steps.findIndex((s) => s.id === stepId);
          if (index === -1) return state;

          const newIndex = direction === 'up' ? index - 1 : index + 1;
          if (newIndex < 0 || newIndex >= steps.length) return state;

          // Swap orders
          const tempOrder = steps[index].order;
          steps[index].order = steps[newIndex].order;
          steps[newIndex].order = tempOrder;

          return {
            preprocessing: {
              steps: steps.sort((a, b) => a.order - b.order),
            },
          };
        }),

      togglePreprocessingStep: (stepId) =>
        set((state) => ({
          preprocessing: {
            steps: state.preprocessing.steps.map((step) =>
              step.id === stepId ? { ...step, enabled: !step.enabled } : step
            ),
          },
        })),

      // Advanced config actions
      setPaletteConfig: (paletteConfig) => set({ paletteConfig }),
      setVectorization: (vectorization) => set({ vectorization }),
      setOutputConfig: (outputConfig) => set({ outputConfig }),

      // Reset
      resetToDefaults: () =>
        set({
          qualityMode: 'standard',
          imageType: 'auto',
          colorPalette: 32,
          denoiseStrength: 'medium',
          selectedPresetId: null,
          preprocessing: defaultPreprocessing,
          paletteConfig: defaultPaletteConfig,
          vectorization: defaultVectorization,
          outputConfig: defaultOutputConfig,
        }),

      // Apply preset
      applyPreset: (preset) =>
        set({
          selectedPresetId: preset.id,
          qualityMode: preset.quality_mode || 'standard',
          imageType: preset.image_type || 'auto',
          colorPalette: preset.color_palette || 32,
          preprocessing: preset.preprocessing || defaultPreprocessing,
          paletteConfig: preset.palette_config || defaultPaletteConfig,
          vectorization: preset.vectorization || defaultVectorization,
          outputConfig: preset.output_config || defaultOutputConfig,
        }),
    }),
    {
      name: 'advanced-conversion-options',
      partialize: (state) => ({
        qualityMode: state.qualityMode,
        imageType: state.imageType,
        colorPalette: state.colorPalette,
        denoiseStrength: state.denoiseStrength,
        selectedPresetId: state.selectedPresetId,
        preprocessing: state.preprocessing,
        paletteConfig: state.paletteConfig,
        vectorization: state.vectorization,
        outputConfig: state.outputConfig,
      }),
    }
  )
);

// =============================================================================
// Preview State
// =============================================================================

interface PreviewState {
  isGenerating: boolean;
  previewId: string | null;
  originalUrl: string | null;
  processedUrl: string | null;
  processingTime: number | null;
  dimensions: { width: number; height: number } | null;
  error: string | null;

  setGenerating: (isGenerating: boolean) => void;
  setPreview: (preview: {
    previewId: string;
    originalUrl: string;
    processedUrl: string;
    processingTime: number;
    dimensions: { width: number; height: number };
  }) => void;
  setError: (error: string | null) => void;
  clearPreview: () => void;
}

export const usePreviewStore = create<PreviewState>((set) => ({
  isGenerating: false,
  previewId: null,
  originalUrl: null,
  processedUrl: null,
  processingTime: null,
  dimensions: null,
  error: null,

  setGenerating: (isGenerating) => set({ isGenerating }),
  setPreview: (preview) =>
    set({
      previewId: preview.previewId,
      originalUrl: preview.originalUrl,
      processedUrl: preview.processedUrl,
      processingTime: preview.processingTime,
      dimensions: preview.dimensions,
      error: null,
    }),
  setError: (error) => set({ error }),
  clearPreview: () =>
    set({
      previewId: null,
      originalUrl: null,
      processedUrl: null,
      processingTime: null,
      dimensions: null,
      error: null,
    }),
}));

// =============================================================================
// Filter Registry State
// =============================================================================

interface FilterRegistryState {
  filters: FilterInfo[];
  categories: string[];
  isLoading: boolean;
  error: string | null;

  setFilters: (filters: FilterInfo[], categories: string[]) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  getFilterById: (id: string) => FilterInfo | undefined;
}

export const useFilterRegistryStore = create<FilterRegistryState>((set, get) => ({
  filters: [],
  categories: [],
  isLoading: false,
  error: null,

  setFilters: (filters, categories) => set({ filters, categories }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  getFilterById: (id) => get().filters.find((f) => f.id === id),
}));

// =============================================================================
// Image Analysis State
// =============================================================================

interface ImageAnalysisState {
  analysis: {
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
  } | null;
  isAnalyzing: boolean;
  error: string | null;

  setAnalysis: (analysis: ImageAnalysisState['analysis']) => void;
  setAnalyzing: (isAnalyzing: boolean) => void;
  setError: (error: string | null) => void;
  clearAnalysis: () => void;
}

export const useImageAnalysisStore = create<ImageAnalysisState>((set) => ({
  analysis: null,
  isAnalyzing: false,
  error: null,

  setAnalysis: (analysis) => set({ analysis }),
  setAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
  setError: (error) => set({ error }),
  clearAnalysis: () => set({ analysis: null, error: null }),
}));

// =============================================================================
// Preset State
// =============================================================================

interface PresetState {
  presets: ConversionPreset[];
  selectedPreset: ConversionPreset | null;
  isLoading: boolean;
  error: string | null;

  setPresets: (presets: ConversionPreset[]) => void;
  setSelectedPreset: (preset: ConversionPreset | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  addPreset: (preset: ConversionPreset) => void;
  updatePreset: (preset: ConversionPreset) => void;
  removePreset: (presetId: string) => void;
}

export const usePresetStore = create<PresetState>((set) => ({
  presets: [],
  selectedPreset: null,
  isLoading: false,
  error: null,

  setPresets: (presets) => set({ presets }),
  setSelectedPreset: (selectedPreset) => set({ selectedPreset }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  addPreset: (preset) =>
    set((state) => ({
      presets: [...state.presets, preset],
    })),
  updatePreset: (preset) =>
    set((state) => ({
      presets: state.presets.map((p) => (p.id === preset.id ? preset : p)),
    })),
  removePreset: (presetId) =>
    set((state) => ({
      presets: state.presets.filter((p) => p.id !== presetId),
    })),
}));

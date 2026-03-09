'use client';

import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Loader2, 
  Wand2, 
  Image as ImageIcon, 
  SlidersHorizontal,
  Palette,
  Eye,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Settings2,
  GitCompare
} from 'lucide-react';
import { ComparisonMode } from './ComparisonMode';
import { useUploadStore } from '@/lib/store';
import { 
  useControlLevelStore, 
  useAdvancedConversionStore, 
  usePreviewStore,
  useImageAnalysisStore,
} from '@/lib/advanced-store';
import { advancedApi } from '@/lib/advanced-api';
import { ControlLevelSelector } from './ControlLevelSelector';
import { PreprocessingPipelineBuilder } from './PreprocessingPipeline';
import { PresetSelector } from './PresetSelector';
import { VectorizationConfig } from './VectorizationConfig';
import { SVGOutputConfigPanel } from './SVGOutputConfig';
import { ColorPaletteEditor } from './ColorPaletteEditor';
import toast from 'react-hot-toast';

export function EnhancedConversionForm() {
  const { fileId, file } = useUploadStore();
  const { level } = useControlLevelStore();
  const {
    qualityMode,
    imageType,
    colorPalette,
    denoiseStrength,
    preprocessing,
    paletteConfig,
    vectorization,
    outputConfig,
    setQualityMode,
    setImageType,
    setColorPalette,
    setDenoiseStrength,
  } = useAdvancedConversionStore();
  const { setGenerating, setPreview, setError, clearPreview } = usePreviewStore();
  const { analysis, setAnalysis, setAnalyzing } = useImageAnalysisStore();
  
  const [isConverting, setIsConverting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [activeTab, setActiveTab] = useState<'presets' | 'filters' | 'colors' | 'vectorization' | 'output'>('presets');
  const [showComparison, setShowComparison] = useState(false);

  // Analyze image on file change
  useEffect(() => {
    if (fileId) {
      const analyze = async () => {
        setAnalyzing(true);
        try {
          const result = await advancedApi.analyzeImage(fileId);
          setAnalysis(result);
        } catch (err) {
          console.error('Analysis failed:', err);
        } finally {
          setAnalyzing(false);
        }
      };
      analyze();
    } else {
      setAnalysis(null);
    }
  }, [fileId, setAnalysis, setAnalyzing]);

  const handleGeneratePreview = async () => {
    if (!fileId) {
      toast.error('Please upload an image first');
      return;
    }

    setGenerating(true);
    clearPreview();

    try {
      const result = await advancedApi.createPreview(
        fileId,
        preprocessing.steps.length > 0 ? preprocessing : undefined
      );
      
      setPreview({
        previewId: result.preview_id,
        originalUrl: advancedApi.getPreviewUrl(result.preview_id, 'original'),
        processedUrl: advancedApi.getPreviewUrl(result.preview_id, 'processed'),
        processingTime: result.processing_time,
        dimensions: result.dimensions,
      });
      
      toast.success('Preview generated!');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate preview';
      setError(message);
      toast.error(message);
    } finally {
      setGenerating(false);
    }
  };

  const handleConvert = async () => {
    if (!fileId) {
      toast.error('Please upload an image first');
      return;
    }

    setIsConverting(true);

    try {
      const request: any = {
        file_id: fileId,
        control_level: level,
        quality_mode: qualityMode,
        image_type: imageType,
        color_palette: colorPalette,
        denoise_strength: denoiseStrength,
        generate_preview: true,
      };

      // Include advanced configs for level 3
      if (level >= 3) {
        request.preprocessing = preprocessing;
        request.palette_config = paletteConfig;
        request.vectorization = vectorization;
        request.output_config = outputConfig;
      }

      const result = await advancedApi.enhancedConvert(request);
      
      toast.success('Conversion started!');
      
      // Return job info for parent component
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Conversion failed';
      toast.error(message);
    } finally {
      setIsConverting(false);
    }
  };

  const canConvert = fileId && !isConverting;

  return (
    <div className="space-y-6">
      {/* Control Level Selector - Always visible */}
      <ControlLevelSelector />

      {/* Analysis Results */}
      {analysis && (
        <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
          <div className="flex items-start space-x-3">
            <Wand2 className="w-5 h-5 text-blue-500 mt-0.5" />
            <div>
              <h4 className="font-medium text-blue-900">Image Analysis</h4>
              <p className="text-sm text-blue-700 mt-1">
                This looks like {analysis.is_photo ? 'a photo' : analysis.is_line_art ? 'line art' : 'an image'} 
                {' '}with {analysis.unique_colors} colors. 
                We recommend using <strong className="capitalize">{analysis.recommended_mode} mode</strong>.
              </p>
              {analysis.suggested_filters.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {analysis.suggested_filters.map((filter) => (
                    <span
                      key={filter}
                      className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full"
                    >
                      Suggested: {filter.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Level 2: Guided Controls */}
      {level >= 2 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="p-4 border-b border-gray-100 bg-gray-50/50">
            <div className="flex items-center space-x-2">
              <SlidersHorizontal className="w-5 h-5 text-gray-500" />
              <h3 className="font-semibold text-gray-900">Conversion Options</h3>
            </div>
          </div>

          <div className="p-4 space-y-4">
            {/* Quality Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Quality Mode
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(['fast', 'standard', 'high'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setQualityMode(mode)}
                    className={`
                      px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                      ${qualityMode === mode
                        ? 'bg-blue-50 border-blue-500 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                      }
                    `}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            {/* Image Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Image Type
              </label>
              <div className="flex space-x-2">
                {(['auto', 'color', 'monochrome'] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setImageType(type)}
                    className={`
                      flex-1 px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                      ${imageType === type
                        ? 'bg-blue-50 border-blue-500 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                      }
                    `}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Color Palette */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Color Palette
                </label>
                <span className="text-sm text-blue-600 font-medium">{colorPalette} colors</span>
              </div>
              <input
                type="range"
                min={8}
                max={256}
                step={8}
                value={colorPalette}
                onChange={(e) => setColorPalette(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>8 colors</span>
                <span>256 colors</span>
              </div>
            </div>

            {/* Denoise Strength */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Denoise Strength
              </label>
              <div className="flex space-x-2">
                {(['light', 'medium', 'heavy'] as const).map((strength) => (
                  <button
                    key={strength}
                    onClick={() => setDenoiseStrength(strength)}
                    className={`
                      flex-1 px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                      ${denoiseStrength === strength
                        ? 'bg-blue-50 border-blue-500 text-blue-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                      }
                    `}
                  >
                    {strength}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Level 3: Advanced Controls */}
      {level >= 3 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full p-4 flex items-center justify-between bg-gray-50/50 hover:bg-gray-100/50 transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Settings2 className="w-5 h-5 text-gray-500" />
              <h3 className="font-semibold text-gray-900">Advanced Controls</h3>
            </div>
            {showAdvanced ? (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            )}
          </button>

          {showAdvanced && (
            <div className="p-4">
              {/* Tabs */}
              <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg mb-4 overflow-x-auto">
                {[
                  { id: 'presets', label: 'Presets' },
                  { id: 'filters', label: 'Filters' },
                  { id: 'colors', label: 'Colors' },
                  { id: 'vectorization', label: 'Vector' },
                  { id: 'output', label: 'Output' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as typeof activeTab)}
                    className={`
                      flex-1 py-2 text-sm font-medium rounded-md transition-all whitespace-nowrap px-3
                      ${activeTab === tab.id
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                      }
                    `}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              {activeTab === 'presets' && <PresetSelector />}
              {activeTab === 'filters' && <PreprocessingPipelineBuilder />}
              {activeTab === 'colors' && <ColorPaletteEditor />}
              {activeTab === 'vectorization' && <VectorizationConfig />}
              {activeTab === 'output' && <SVGOutputConfigPanel />}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      {level >= 2 && (
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setShowComparison(true)}
            disabled={!fileId}
            className={`
              py-3 rounded-xl font-medium flex items-center justify-center space-x-2
              transition-all duration-200 border-2
              ${fileId
                ? 'border-purple-200 text-purple-700 hover:bg-purple-50 hover:border-purple-300'
                : 'border-gray-100 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            <GitCompare className="w-5 h-5" />
            <span>Compare Modes</span>
          </button>
          
          <button
            onClick={handleGeneratePreview}
            disabled={!fileId}
            className={`
              py-3 rounded-xl font-medium flex items-center justify-center space-x-2
              transition-all duration-200 border-2
              ${fileId
                ? 'border-blue-200 text-blue-700 hover:bg-blue-50 hover:border-blue-300'
                : 'border-gray-100 text-gray-400 cursor-not-allowed'
              }
            `}
          >
            <Eye className="w-5 h-5" />
            <span>Preview</span>
          </button>
        </div>
      )}

      {/* Comparison Modal */}
      {showComparison && (
        <ComparisonMode onClose={() => setShowComparison(false)} />
      )}

      {/* Convert Button */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <button
          onClick={handleConvert}
          disabled={!canConvert}
          className={`
            w-full py-4 rounded-xl font-semibold text-lg flex items-center justify-center
            transition-all duration-200
            ${canConvert
              ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg hover:shadow-xl'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }
          `}
        >
          {isConverting ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Converting...
            </>
          ) : (
            <>
              <Play className="w-5 h-5 mr-2" />
              Convert to SVG
            </>
          )}
        </button>

        {!fileId && (
          <p className="mt-3 text-center text-sm text-gray-500">
            Upload an image to start conversion
          </p>
        )}

        <div className="mt-4 p-4 bg-blue-50 rounded-lg">
          <h4 className="font-medium text-blue-900 mb-2">What happens next?</h4>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Your image is processed in the background</li>
            <li>• Track progress in real-time</li>
            <li>• Download the SVG when complete</li>
            <li>• Results are stored for 30 days</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

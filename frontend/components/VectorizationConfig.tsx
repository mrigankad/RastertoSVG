'use client';

import React from 'react';
import { 
  GitBranch, 
  Palette, 
  Scissors, 
  Maximize,
  Layers,
  CornerUpRight,
  Target,
  Trash2
} from 'lucide-react';
import { useAdvancedConversionStore } from '@/lib/advanced-store';

export function VectorizationConfig() {
  const { vectorization, setVectorization } = useAdvancedConversionStore();

  const updateParam = <K extends keyof typeof vectorization>(
    key: K,
    value: typeof vectorization[K]
  ) => {
    setVectorization({ ...vectorization, [key]: value });
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center space-x-2">
          <GitBranch className="w-5 h-5 text-purple-500" />
          <h3 className="font-semibold text-gray-900">Vectorization Parameters</h3>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Fine-tune how the image is converted to vector paths
        </p>
      </div>

      <div className="p-4 space-y-5">
        {/* Engine Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Conversion Engine
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'vtracer', 'potrace'] as const).map((engine) => (
              <button
                key={engine}
                onClick={() => updateParam('engine', engine)}
                className={`
                  px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                  ${vectorization.engine === engine
                    ? 'bg-purple-50 border-purple-500 text-purple-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                {engine}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1.5">
            {vectorization.engine === 'auto' && 'Automatically selects best engine based on image type'}
            {vectorization.engine === 'vtracer' && 'Best for color images and photographs'}
            {vectorization.engine === 'potrace' && 'Best for monochrome and line art'}
          </p>
        </div>

        {/* Curve Fitting */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Curve Fitting
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'tight', 'smooth'] as const).map((fitting) => (
              <button
                key={fitting}
                onClick={() => updateParam('curve_fitting', fitting)}
                className={`
                  px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                  ${vectorization.curve_fitting === fitting
                    ? 'bg-purple-50 border-purple-500 text-purple-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                {fitting}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1.5">
            {vectorization.curve_fitting === 'tight' && 'Follows edges more precisely, more nodes'}
            {vectorization.curve_fitting === 'smooth' && 'Smoother curves, fewer nodes'}
            {vectorization.curve_fitting === 'auto' && 'Balanced approach'}
          </p>
        </div>

        {/* Corner Threshold */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              <CornerUpRight className="w-4 h-4 mr-1.5 text-gray-400" />
              Corner Threshold
            </label>
            <span className="text-sm text-purple-600 font-medium">{vectorization.corner_threshold}°</span>
          </div>
          <input
            type="range"
            min={0}
            max={180}
            step={5}
            value={vectorization.corner_threshold}
            onChange={(e) => updateParam('corner_threshold', parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0° (Sharp)</span>
            <span>90°</span>
            <span>180° (Smooth)</span>
          </div>
        </div>

        {/* Path Precision */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              <Target className="w-4 h-4 mr-1.5 text-gray-400" />
              Path Precision (Decimals)
            </label>
            <span className="text-sm text-purple-600 font-medium">{vectorization.path_precision}</span>
          </div>
          <input
            type="range"
            min={0}
            max={5}
            step={1}
            value={vectorization.path_precision}
            onChange={(e) => updateParam('path_precision', parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0 (Small file)</span>
            <span>2-3 (Balanced)</span>
            <span>5 (High precision)</span>
          </div>
        </div>

        {/* Color Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
            <Palette className="w-4 h-4 mr-1.5 text-gray-400" />
            Color Mode
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['color', 'monochrome', 'grayscale'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => updateParam('color_mode', mode)}
                className={`
                  px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                  ${vectorization.color_mode === mode
                    ? 'bg-purple-50 border-purple-500 text-purple-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Toggles */}
        <div className="space-y-3 pt-2 border-t border-gray-100">
          {/* Hierarchical Grouping */}
          <label className="flex items-center justify-between cursor-pointer group">
            <div className="flex items-center">
              <Layers className="w-4 h-4 text-gray-400 mr-2 group-hover:text-gray-600" />
              <span className="text-sm text-gray-700">Hierarchical Grouping</span>
            </div>
            <button
              onClick={() => updateParam('hierarchical', !vectorization.hierarchical)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${vectorization.hierarchical ? 'bg-purple-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${vectorization.hierarchical ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>

          {/* Simplify Paths */}
          <label className="flex items-center justify-between cursor-pointer group">
            <div className="flex items-center">
              <Scissors className="w-4 h-4 text-gray-400 mr-2 group-hover:text-gray-600" />
              <span className="text-sm text-gray-700">Simplify Paths</span>
            </div>
            <button
              onClick={() => updateParam('simplify_paths', !vectorization.simplify_paths)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${vectorization.simplify_paths ? 'bg-purple-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${vectorization.simplify_paths ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>

          {/* Remove Small Paths */}
          <label className="flex items-center justify-between cursor-pointer group">
            <div className="flex items-center">
              <Trash2 className="w-4 h-4 text-gray-400 mr-2 group-hover:text-gray-600" />
              <span className="text-sm text-gray-700">Remove Small Paths</span>
            </div>
            <button
              onClick={() => updateParam('remove_small_paths', !vectorization.remove_small_paths)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${vectorization.remove_small_paths ? 'bg-purple-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${vectorization.remove_small_paths ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>
        </div>

        {/* Min Path Area (only if remove_small_paths is enabled) */}
        {vectorization.remove_small_paths && (
          <div className="pl-6">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-medium text-gray-600">
                Minimum Path Area (pixels)
              </label>
              <span className="text-xs text-purple-600 font-medium">{vectorization.min_path_area}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={vectorization.min_path_area}
              onChange={(e) => updateParam('min_path_area', parseFloat(e.target.value))}
              className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
            />
          </div>
        )}
      </div>
    </div>
  );
}

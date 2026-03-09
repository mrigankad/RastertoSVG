'use client';

import React from 'react';
import { 
  FileCode, 
  Maximize, 
  Palette, 
  Zap,
  Tag,
  Code,
  FileJson,
  Check
} from 'lucide-react';
import { useAdvancedConversionStore } from '@/lib/advanced-store';

export function SVGOutputConfigPanel() {
  const { outputConfig, setOutputConfig } = useAdvancedConversionStore();

  const updateParam = <K extends keyof typeof outputConfig>(
    key: K,
    value: typeof outputConfig[K]
  ) => {
    setOutputConfig({ ...outputConfig, [key]: value });
  };

  const optimizationOptions = [
    { 
      value: 'none' as const, 
      label: 'None', 
      description: 'No optimization, human-readable',
      icon: FileCode
    },
    { 
      value: 'light' as const, 
      label: 'Light', 
      description: 'Remove metadata and comments only',
      icon: Zap
    },
    { 
      value: 'standard' as const, 
      label: 'Standard', 
      description: 'Path simplification and ID shortening',
      icon: Check
    },
    { 
      value: 'aggressive' as const, 
      label: 'Aggressive', 
      description: 'Maximum compression, smallest file',
      icon: Zap
    },
  ];

  const styleModeOptions = [
    { value: 'inline' as const, label: 'Inline', description: 'Styles embedded in elements' },
    { value: 'css' as const, label: 'CSS Classes', description: 'Styles in <style> block' },
    { value: 'attributes' as const, label: 'Attributes', description: 'SVG presentation attributes' },
  ];

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center space-x-2">
          <FileCode className="w-5 h-5 text-green-500" />
          <h3 className="font-semibold text-gray-900">SVG Output Options</h3>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Configure the generated SVG file format and structure
        </p>
      </div>

      <div className="p-4 space-y-5">
        {/* Optimization Level */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
            <Zap className="w-4 h-4 mr-1.5 text-gray-400" />
            Optimization Level
          </label>
          <div className="space-y-2">
            {optimizationOptions.map((option) => {
              const Icon = option.icon;
              return (
                <button
                  key={option.value}
                  onClick={() => updateParam('optimization_level', option.value)}
                  className={`
                    w-full px-3 py-2.5 rounded-lg border text-left transition-all
                    ${outputConfig.optimization_level === option.value
                      ? 'bg-green-50 border-green-500 ring-1 ring-green-500'
                      : 'bg-white border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <div className="flex items-center">
                    <Icon className={`
                      w-4 h-4 mr-2
                      ${outputConfig.optimization_level === option.value ? 'text-green-600' : 'text-gray-400'}
                    `} />
                    <div>
                      <span className={`
                        text-sm font-medium
                        ${outputConfig.optimization_level === option.value ? 'text-green-900' : 'text-gray-900'}
                      `}>
                        {option.label}
                      </span>
                      <p className="text-xs text-gray-500">{option.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ViewBox Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
            <Maximize className="w-4 h-4 mr-1.5 text-gray-400" />
            ViewBox & Dimensions
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['auto', 'custom', 'percentage'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => updateParam('viewbox_mode', mode)}
                className={`
                  px-3 py-2 rounded-lg border text-sm font-medium capitalize transition-all
                  ${outputConfig.viewbox_mode === mode
                    ? 'bg-green-50 border-green-500 text-green-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                {mode}
              </button>
            ))}
          </div>
          
          {/* Custom dimensions inputs */}
          {outputConfig.viewbox_mode === 'custom' && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Width (px)</label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={outputConfig.custom_width || ''}
                  onChange={(e) => updateParam('custom_width', e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="Auto"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Height (px)</label>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={outputConfig.custom_height || ''}
                  onChange={(e) => updateParam('custom_height', e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="Auto"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
              </div>
            </div>
          )}
        </div>

        {/* Coordinate Precision */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              <Code className="w-4 h-4 mr-1.5 text-gray-400" />
              Coordinate Precision
            </label>
            <span className="text-sm text-green-600 font-medium">{outputConfig.precision} decimals</span>
          </div>
          <input
            type="range"
            min={0}
            max={6}
            step={1}
            value={outputConfig.precision}
            onChange={(e) => updateParam('precision', parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0 (Integer)</span>
            <span>2 (Default)</span>
            <span>6 (Max)</span>
          </div>
        </div>

        {/* Style Mode */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
            <Palette className="w-4 h-4 mr-1.5 text-gray-400" />
            Style Mode
          </label>
          <div className="space-y-2">
            {styleModeOptions.map((mode) => (
              <button
                key={mode.value}
                onClick={() => updateParam('style_mode', mode.value)}
                className={`
                  w-full px-3 py-2 rounded-lg border text-left transition-all
                  ${outputConfig.style_mode === mode.value
                    ? 'bg-green-50 border-green-500 text-green-700'
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }
                `}
              >
                <span className="text-sm font-medium">{mode.label}</span>
                <p className="text-xs text-gray-500">{mode.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Class Prefix */}
        {outputConfig.style_mode === 'css' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
              <Tag className="w-4 h-4 mr-1.5 text-gray-400" />
              Class Prefix
            </label>
            <input
              type="text"
              value={outputConfig.class_prefix}
              onChange={(e) => updateParam('class_prefix', e.target.value)}
              placeholder="path-"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
        )}

        {/* Toggles */}
        <div className="space-y-3 pt-2 border-t border-gray-100">
          {/* Add Classes */}
          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm text-gray-700">Add CSS Classes</span>
            <button
              onClick={() => updateParam('add_classes', !outputConfig.add_classes)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${outputConfig.add_classes ? 'bg-green-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${outputConfig.add_classes ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>

          {/* Remove Metadata */}
          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm text-gray-700">Remove Metadata</span>
            <button
              onClick={() => updateParam('remove_metadata', !outputConfig.remove_metadata)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${outputConfig.remove_metadata ? 'bg-green-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${outputConfig.remove_metadata ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>

          {/* Minify */}
          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm text-gray-700">Minify Output</span>
            <button
              onClick={() => updateParam('minify', !outputConfig.minify)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${outputConfig.minify ? 'bg-green-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${outputConfig.minify ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>

          {/* Reuse Paths */}
          <label className="flex items-center justify-between cursor-pointer group">
            <span className="text-sm text-gray-700">Reuse Duplicate Paths</span>
            <button
              onClick={() => updateParam('reuse_paths', !outputConfig.reuse_paths)}
              className={`
                relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                ${outputConfig.reuse_paths ? 'bg-green-500' : 'bg-gray-200'}
              `}
            >
              <span
                className={`
                  inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                  ${outputConfig.reuse_paths ? 'translate-x-5' : 'translate-x-1'}
                `}
              />
            </button>
          </label>
        </div>

        {/* Output Format Info */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-start space-x-2">
            <FileJson className="w-4 h-4 text-gray-400 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-gray-700">Output Format</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {outputConfig.minify ? 'Minified SVG' : 'Pretty-printed SVG'} 
                {' • '}
                {outputConfig.optimization_level} optimization
                {' • '}
                {outputConfig.precision} decimal precision
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

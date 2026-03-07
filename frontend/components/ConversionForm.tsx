'use client';

import React, { useState } from 'react';
import { Settings, Zap, Gauge, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import { useConversionOptionsStore } from '@/lib/store';

export function ConversionForm() {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const {
    image_type,
    quality_mode,
    color_palette,
    denoise_strength,
    setImageType,
    setQualityMode,
    setColorPalette,
    setDenoiseStrength,
    reset,
  } = useConversionOptionsStore();

  const qualityOptions = [
    {
      value: 'fast' as const,
      label: 'Fast',
      description: 'Direct conversion, no preprocessing',
      icon: Zap,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      features: ['< 1 second', 'No preprocessing', 'Best for simple graphics'],
    },
    {
      value: 'standard' as const,
      label: 'Standard',
      description: 'Balanced preprocessing and quality',
      icon: Gauge,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200',
      features: ['1-3 seconds', 'Color reduction + denoise', 'Best for most images'],
    },
    {
      value: 'high' as const,
      label: 'High',
      description: 'Maximum quality with advanced preprocessing',
      icon: Sparkles,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200',
      features: ['3-10 seconds', 'Full preprocessing', 'Best for professional work'],
    },
  ];

  const getQualityDescription = () => {
    switch (quality_mode) {
      case 'fast':
        return 'No preprocessing is applied. The image is converted directly using VTracer (color) or Potrace (monochrome). Fastest option but may produce lower quality for complex images.';
      case 'standard':
        return 'Applies color reduction (32 colors), bilateral denoising, and CLAHE contrast enhancement. Best balance of speed and quality for most images.';
      case 'high':
        return 'Applies color reduction (128 colors), Non-Local Means denoising, CLAHE contrast, unsharp mask sharpening, and edge enhancement. Best quality for professional work.';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-100">
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900">
            Conversion Options
          </h3>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Quality Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Quality Mode
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {qualityOptions.map((option) => {
              const Icon = option.icon;
              const isSelected = quality_mode === option.value;

              return (
                <button
                  key={option.value}
                  onClick={() => setQualityMode(option.value)}
                  className={`
                    relative p-4 rounded-lg border-2 text-left transition-all
                    ${isSelected
                      ? `${option.borderColor} ${option.bgColor} ring-2 ring-offset-2 ring-blue-500`
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                    }
                  `}
                >
                  <div className="flex items-center space-x-2 mb-2">
                    <Icon className={`w-5 h-5 ${option.color}`} />
                    <span className={`font-semibold ${isSelected ? option.color : 'text-gray-900'}`}>
                      {option.label}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">
                    {option.description}
                  </p>
                  <ul className="space-y-1">
                    {option.features.map((feature, idx) => (
                      <li key={idx} className="text-xs text-gray-400 flex items-center">
                        <span className="w-1 h-1 bg-gray-300 rounded-full mr-2" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </button>
              );
            })}
          </div>

          <p className="mt-3 text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
            {getQualityDescription()}
          </p>
        </div>

        {/* Image Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Image Type
          </label>
          <div className="flex space-x-4">
            {(['auto', 'color', 'monochrome'] as const).map((type) => (
              <label
                key={type}
                className={`
                  flex items-center px-4 py-2 rounded-lg border cursor-pointer transition-all
                  ${image_type === type
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 hover:border-gray-300'
                  }
                `}
              >
                <input
                  type="radio"
                  name="image_type"
                  value={type}
                  checked={image_type === type}
                  onChange={() => setImageType(type)}
                  className="sr-only"
                />
                <span className="capitalize font-medium">{type}</span>
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {image_type === 'auto' && 'Automatically detect if the image is color or monochrome'}
            {image_type === 'color' && 'Force color mode - best for photos and colorful images'}
            {image_type === 'monochrome' && 'Force monochrome mode - best for line art and text'}
          </p>
        </div>

        {/* Advanced Options */}
        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            {showAdvanced ? (
              <ChevronUp className="w-4 h-4 mr-1" />
            ) : (
              <ChevronDown className="w-4 h-4 mr-1" />
            )}
            Advanced Options
          </button>

          {showAdvanced && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
              {/* Color Palette */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Color Palette Size (for color images)
                </label>
                <input
                  type="range"
                  min="8"
                  max="256"
                  step="8"
                  value={color_palette}
                  onChange={(e) => setColorPalette(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>8 colors</span>
                  <span className="font-medium text-blue-600">{color_palette} colors</span>
                  <span>256 colors</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Lower values produce smaller files but may reduce quality
                </p>
              </div>

              {/* Denoise Strength */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Denoise Strength
                </label>
                <select
                  value={denoise_strength}
                  onChange={(e) => setDenoiseStrength(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="light">Light - Minimal smoothing</option>
                  <option value="medium">Medium - Balanced (recommended)</option>
                  <option value="heavy">Heavy - Aggressive noise removal</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Higher values remove more noise but may smooth details
                </p>
              </div>

              {/* Reset button */}
              <button
                onClick={reset}
                className="text-sm text-red-600 hover:text-red-700"
              >
                Reset to defaults
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Palette,
  Plus,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  Sliders,
  Image as ImageIcon,
  Droplets,
  Grid3x3,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Lock,
  Unlock,
} from 'lucide-react';
import { advancedApi, ColorInfo } from '@/lib/advanced-api';
import { useAdvancedConversionStore, useUploadStore } from '@/lib/advanced-store';

interface ColorPaletteEditorProps {
  compact?: boolean;
}

export function ColorPaletteEditor({ compact = false }: ColorPaletteEditorProps) {
  const { fileId } = useUploadStore();
  const { paletteConfig, setPaletteConfig } = useAdvancedConversionStore();
  
  const [extractedColors, setExtractedColors] = useState<ColorInfo[]>([]);
  const [isExtracting, setIsExtracting] = useState(false);
  const [copiedColor, setCopiedColor] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customColorInput, setCustomColorInput] = useState('#000000');

  // Extract colors from image
  const extractColors = useCallback(async () => {
    if (!fileId) return;
    
    setIsExtracting(true);
    try {
      const result = await advancedApi.extractColors(fileId, paletteConfig.max_colors);
      setExtractedColors(result.palette);
      
      // Update extracted colors in config
      setPaletteConfig({
        ...paletteConfig,
        extracted_colors: result.palette.map((c) => c.hex),
      });
    } catch (err) {
      console.error('Failed to extract colors:', err);
    } finally {
      setIsExtracting(false);
    }
  }, [fileId, paletteConfig.max_colors, setPaletteConfig]);

  // Extract colors on mount if in extract mode
  useEffect(() => {
    if (paletteConfig.mode === 'extract' && fileId && extractedColors.length === 0) {
      extractColors();
    }
  }, [paletteConfig.mode, fileId, extractedColors.length, extractColors]);

  const handleModeChange = (mode: typeof paletteConfig.mode) => {
    setPaletteConfig({ ...paletteConfig, mode });
    if (mode === 'extract' && fileId) {
      extractColors();
    }
  };

  const handleMaxColorsChange = (value: number) => {
    setPaletteConfig({ ...paletteConfig, max_colors: value });
    if (paletteConfig.mode === 'extract') {
      extractColors();
    }
  };

  const handleDitheringChange = (dithering: typeof paletteConfig.dithering) => {
    setPaletteConfig({ ...paletteConfig, dithering });
  };

  const addCustomColor = () => {
    if (!paletteConfig.custom_colors.includes(customColorInput)) {
      setPaletteConfig({
        ...paletteConfig,
        custom_colors: [...paletteConfig.custom_colors, customColorInput],
      });
    }
  };

  const removeCustomColor = (color: string) => {
    setPaletteConfig({
      ...paletteConfig,
      custom_colors: paletteConfig.custom_colors.filter((c) => c !== color),
    });
  };

  const copyToClipboard = (color: string) => {
    navigator.clipboard.writeText(color);
    setCopiedColor(color);
    setTimeout(() => setCopiedColor(null), 2000);
  };

  const toggleColorLock = (color: string) => {
    // In a full implementation, this would lock the color during extraction
    // For now, just a visual indicator
  };

  // Generate shades of a color
  const generateShades = (hex: string): string[] => {
    const num = parseInt(hex.replace('#', ''), 16);
    const r = (num >> 16) & 255;
    const g = (num >> 8) & 255;
    const b = num & 255;
    
    const shades: string[] = [];
    for (let i = 0; i <= 4; i++) {
      const factor = 0.3 + (i * 0.175); // 0.3 to 1.0
      const newR = Math.round(r * factor);
      const newG = Math.round(g * factor);
      const newB = Math.round(b * factor);
      shades.push(`#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`);
    }
    return shades;
  };

  const currentColors = paletteConfig.mode === 'custom' 
    ? paletteConfig.custom_colors 
    : extractedColors.map((c) => c.hex);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {!compact && (
        <div className="p-4 border-b border-gray-100 bg-gray-50/50">
          <div className="flex items-center space-x-2">
            <Palette className="w-5 h-5 text-pink-500" />
            <h3 className="font-semibold text-gray-900">Color Palette Editor</h3>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Control how colors are extracted and reduced
          </p>
        </div>
      )}

      <div className={`${compact ? 'p-3' : 'p-4'} space-y-4`}>
        {/* Mode Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Palette Mode
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { value: 'auto' as const, label: 'Auto', icon: Sparkles, desc: 'Automatic' },
              { value: 'extract' as const, label: 'Extract', icon: ImageIcon, desc: 'From Image' },
              { value: 'custom' as const, label: 'Custom', icon: Palette, desc: 'Manual' },
              { value: 'preserve' as const, label: 'Preserve', icon: Lock, desc: 'Original' },
            ].map((mode) => {
              const Icon = mode.icon;
              return (
                <button
                  key={mode.value}
                  onClick={() => handleModeChange(mode.value)}
                  className={`
                    flex items-center px-3 py-2 rounded-lg border text-left transition-all
                    ${paletteConfig.mode === mode.value
                      ? 'bg-pink-50 border-pink-500 text-pink-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-4 h-4 mr-2" />
                  <div>
                    <span className="text-sm font-medium">{mode.label}</span>
                    <p className="text-[10px] opacity-75">{mode.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Max Colors */}
        {(paletteConfig.mode === 'auto' || paletteConfig.mode === 'extract') && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">
                Max Colors
              </label>
              <span className="text-sm text-pink-600 font-medium">
                {paletteConfig.max_colors}
              </span>
            </div>
            <input
              type="range"
              min={2}
              max={256}
              step={1}
              value={paletteConfig.max_colors}
              onChange={(e) => handleMaxColorsChange(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-pink-500"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>2</span>
              <span>64</span>
              <span>128</span>
              <span>256</span>
            </div>
          </div>
        )}

        {/* Dithering */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
            <Droplets className="w-4 h-4 mr-1.5 text-gray-400" />
            Dithering
          </label>
          <select
            value={paletteConfig.dithering}
            onChange={(e) => handleDitheringChange(e.target.value as typeof paletteConfig.dithering)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-pink-500 focus:border-transparent"
          >
            <option value="none">None - Hard edges</option>
            <option value="floyd_steinberg">Floyd-Steinberg - Smooth gradients</option>
            <option value="bayer">Bayer - Patterned</option>
            <option value="atkinson">Atkinson - Reduced artifacts</option>
            <option value="ordered">Ordered - Regular pattern</option>
          </select>
        </div>

        {/* Color Grid */}
        {currentColors.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                <Grid3x3 className="w-4 h-4 mr-1.5 text-gray-400" />
                {paletteConfig.mode === 'custom' ? 'Custom Colors' : 'Extracted Colors'}
              </label>
              {paletteConfig.mode === 'extract' && (
                <button
                  onClick={extractColors}
                  disabled={isExtracting || !fileId}
                  className="text-xs text-pink-600 hover:text-pink-700 flex items-center disabled:opacity-50"
                >
                  <RefreshCw className={`w-3 h-3 mr-1 ${isExtracting ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              )}
            </div>

            <div className="grid grid-cols-8 gap-1.5">
              {currentColors.map((color, index) => (
                <div
                  key={`${color}-${index}`}
                  className="group relative aspect-square rounded-lg overflow-hidden cursor-pointer shadow-sm hover:shadow-md transition-shadow"
                  style={{ backgroundColor: color }}
                  onClick={() => copyToClipboard(color)}
                >
                  {/* Hover overlay */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                    {copiedColor === color ? (
                      <Check className="w-4 h-4 text-white" />
                    ) : (
                      <Copy className="w-4 h-4 text-white" />
                    )}
                  </div>
                  
                  {/* Color percentage for extracted colors */}
                  {paletteConfig.mode === 'extract' && extractedColors[index]?.percentage && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[8px] text-center py-0.5">
                      {extractedColors[index].percentage.toFixed(1)}%
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Color Shades Preview (for first color) */}
            {currentColors.length > 0 && !compact && (
              <div className="mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-gray-500 mb-2">Shades of {currentColors[0]}</p>
                <div className="flex gap-1">
                  {generateShades(currentColors[0]).map((shade, i) => (
                    <div
                      key={shade}
                      className="flex-1 h-6 rounded"
                      style={{ backgroundColor: shade }}
                      title={shade}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Custom Color Input */}
        {paletteConfig.mode === 'custom' && (
          <div className="flex gap-2">
            <input
              type="color"
              value={customColorInput}
              onChange={(e) => setCustomColorInput(e.target.value)}
              className="w-10 h-10 rounded-lg cursor-pointer border border-gray-200"
            />
            <input
              type="text"
              value={customColorInput}
              onChange={(e) => setCustomColorInput(e.target.value)}
              placeholder="#000000"
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-pink-500 focus:border-transparent uppercase"
            />
            <button
              onClick={addCustomColor}
              disabled={!customColorInput.match(/^#[0-9A-Fa-f]{6}$/)}
              className="px-3 py-2 bg-pink-500 text-white rounded-lg hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Custom Colors List */}
        {paletteConfig.mode === 'custom' && paletteConfig.custom_colors.length > 0 && (
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {paletteConfig.custom_colors.map((color, index) => (
              <div
                key={`${color}-${index}`}
                className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg"
              >
                <div
                  className="w-6 h-6 rounded border border-gray-200"
                  style={{ backgroundColor: color }}
                />
                <code className="flex-1 text-sm text-gray-600">{color}</code>
                <button
                  onClick={() => copyToClipboard(color)}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  {copiedColor === color ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </button>
                <button
                  onClick={() => removeCustomColor(color)}
                  className="p-1 text-gray-400 hover:text-red-500"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Advanced Options */}
        {!compact && (
          <div>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center text-sm text-gray-600 hover:text-gray-900"
            >
              {showAdvanced ? (
                <ChevronUp className="w-4 h-4 mr-1" />
              ) : (
                <ChevronDown className="w-4 h-4 mr-1" />
              )}
              Advanced Options
            </button>

            {showAdvanced && (
              <div className="mt-3 p-3 bg-gray-50 rounded-lg space-y-3">
                <label className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">Preserve Transparency</span>
                  <button
                    onClick={() => setPaletteConfig({
                      ...paletteConfig,
                      preserve_transparency: !paletteConfig.preserve_transparency,
                    })}
                    className={`
                      relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                      ${paletteConfig.preserve_transparency ? 'bg-pink-500' : 'bg-gray-200'}
                    `}
                  >
                    <span
                      className={`
                        inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                        ${paletteConfig.preserve_transparency ? 'translate-x-5' : 'translate-x-1'}
                      `}
                    />
                  </button>
                </label>

                <div className="text-xs text-gray-500">
                  <p>Colors: {currentColors.length}</p>
                  <p>Mode: {paletteConfig.mode}</p>
                  <p>Dithering: {paletteConfig.dithering.replace('_', ' ')}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

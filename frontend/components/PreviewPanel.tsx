'use client';

import React, { useState } from 'react';
import { Eye, ZoomIn, ZoomOut, RefreshCw, Loader2, Split } from 'lucide-react';
import { usePreviewStore } from '@/lib/advanced-store';

export function PreviewPanel() {
  const { 
    isGenerating, 
    originalUrl, 
    processedUrl, 
    processingTime, 
    dimensions,
    error 
  } = usePreviewStore();
  
  const [viewMode, setViewMode] = useState<'side-by-side' | 'slider'>('side-by-side');
  const [sliderPosition, setSliderPosition] = useState(50);
  const [zoom, setZoom] = useState(1);

  if (isGenerating) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Generating preview...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-xl border border-red-200 p-4">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!originalUrl || !processedUrl) {
    return (
      <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-8">
        <div className="text-center">
          <Eye className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Preview will appear here</p>
          <p className="text-xs text-gray-400 mt-1">
            Configure preprocessing and click "Generate Preview"
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
        <div className="flex items-center space-x-2">
          <Eye className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Preview</span>
          {processingTime && (
            <span className="text-xs text-gray-400">
              ({processingTime.toFixed(2)}s)
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-1">
          {/* View Mode Toggle */}
          <button
            onClick={() => setViewMode(viewMode === 'side-by-side' ? 'slider' : 'side-by-side')}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
            title={viewMode === 'side-by-side' ? 'Slider view' : 'Side-by-side view'}
          >
            <Split className="w-4 h-4" />
          </button>
          
          {/* Zoom Controls */}
          <button
            onClick={() => setZoom(Math.max(0.5, zoom - 0.25))}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-500 w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom(Math.min(2, zoom + 0.25))}
            className="p-1.5 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="p-4">
        {viewMode === 'side-by-side' ? (
          <div className="grid grid-cols-2 gap-4">
            {/* Original */}
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2 text-center">Original</p>
              <div 
                className="bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center"
                style={{ minHeight: '200px' }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={originalUrl}
                  alt="Original"
                  className="max-w-full max-h-[300px] object-contain"
                  style={{ transform: `scale(${zoom})` }}
                />
              </div>
            </div>

            {/* Processed */}
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2 text-center">Processed</p>
              <div 
                className="bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center"
                style={{ minHeight: '200px' }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={processedUrl}
                  alt="Processed"
                  className="max-w-full max-h-[300px] object-contain"
                  style={{ transform: `scale(${zoom})` }}
                />
              </div>
            </div>
          </div>
        ) : (
          /* Slider View */
          <div className="relative">
            <p className="text-xs font-medium text-gray-500 mb-2 text-center">
              Drag to compare: Original → Processed
            </p>
            <div 
              className="relative bg-gray-100 rounded-lg overflow-hidden mx-auto"
              style={{ maxWidth: '400px', height: '300px' }}
            >
              {/* Processed (bottom layer) */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={processedUrl}
                alt="Processed"
                className="absolute inset-0 w-full h-full object-contain"
              />
              
              {/* Original (top layer, clipped) */}
              <div
                className="absolute inset-0 overflow-hidden"
                style={{ clipPath: `inset(0 ${100 - sliderPosition}% 0 0)` }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={originalUrl}
                  alt="Original"
                  className="absolute inset-0 w-full h-full object-contain"
                />
              </div>

              {/* Slider Handle */}
              <input
                type="range"
                min={0}
                max={100}
                value={sliderPosition}
                onChange={(e) => setSliderPosition(parseInt(e.target.value))}
                className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize"
              />
              
              {/* Visual Slider Line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg pointer-events-none"
                style={{ left: `${sliderPosition}%` }}
              >
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 bg-white rounded-full shadow-lg flex items-center justify-center">
                  <div className="w-0.5 h-3 bg-gray-400" />
                </div>
              </div>
            </div>
          </div>
        )}

        {dimensions && (
          <p className="text-xs text-gray-400 text-center mt-3">
            {dimensions.width} × {dimensions.height} px
          </p>
        )}
      </div>
    </div>
  );
}

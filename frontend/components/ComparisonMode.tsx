'use client';

import React, { useState, useEffect } from 'react';
import { 
  GitCompare, 
  X, 
  Loader2, 
  Download, 
  Clock, 
  FileSize,
  BarChart3,
  Image as ImageIcon,
  Check
} from 'lucide-react';
import { advancedApi, ComparisonResponse, ComparisonResult } from '@/lib/advanced-api';
import { useUploadStore } from '@/lib/store';
import toast from 'react-hot-toast';

interface ComparisonModeProps {
  onClose: () => void;
}

export function ComparisonMode({ onClose }: ComparisonModeProps) {
  const { fileId } = useUploadStore();
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModes, setSelectedModes] = useState<string[]>(['fast', 'standard', 'high']);
  const [viewMode, setViewMode] = useState<'grid' | 'slider'>('grid');
  const [sliderValues, setSliderValues] = useState<Record<string, number>>({});

  useEffect(() => {
    if (fileId && selectedModes.length > 0) {
      createComparison();
    }
  }, [fileId]);

  const createComparison = async () => {
    if (!fileId) return;
    
    setIsLoading(true);
    try {
      const result = await advancedApi.createComparison(
        fileId,
        selectedModes as ('fast' | 'standard' | 'high' | 'custom')[]
      );
      setComparison(result);
      
      // Initialize slider values
      const initialSliders: Record<string, number> = {};
      result.results.forEach((r) => {
        initialSliders[r.job_id] = 50;
      });
      setSliderValues(initialSliders);
    } catch (err) {
      toast.error('Failed to create comparison');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleMode = (mode: string) => {
    if (selectedModes.includes(mode)) {
      if (selectedModes.length > 1) {
        setSelectedModes(selectedModes.filter((m) => m !== mode));
      }
    } else {
      setSelectedModes([...selectedModes, mode]);
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
    return `${seconds.toFixed(1)}s`;
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900">Creating Comparison</h3>
            <p className="text-sm text-gray-500 mt-2">
              Running all quality modes side by side...
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between bg-gray-50/50">
          <div className="flex items-center space-x-3">
            <GitCompare className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Compare Quality Modes</h2>
              <p className="text-sm text-gray-500">Side-by-side comparison of all quality modes</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {/* View Mode Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`
                  px-3 py-1.5 rounded-md text-sm font-medium transition-all
                  ${viewMode === 'grid' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}
                `}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('slider')}
                className={`
                  px-3 py-1.5 rounded-md text-sm font-medium transition-all
                  ${viewMode === 'slider' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}
                `}
              >
                Slider
              </button>
            </div>
            
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700 mr-2">Compare:</span>
            {['fast', 'standard', 'high'].map((mode) => (
              <button
                key={mode}
                onClick={() => toggleMode(mode)}
                disabled={selectedModes.includes(mode) && selectedModes.length === 1}
                className={`
                  px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-all
                  ${selectedModes.includes(mode)
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-gray-100 text-gray-500 border border-transparent'
                  }
                  ${selectedModes.includes(mode) && selectedModes.length === 1 ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <div className="flex items-center space-x-1.5">
                  {selectedModes.includes(mode) && <Check className="w-3.5 h-3.5" />}
                  <span>{mode}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {comparison && (
            <>
              {viewMode === 'grid' ? (
                <div className={`grid gap-4 ${
                  comparison.results.length === 2 ? 'grid-cols-2' : 
                  comparison.results.length === 3 ? 'grid-cols-3' : 'grid-cols-1'
                }`}>
                  {comparison.results.map((result) => (
                    <ComparisonCard 
                      key={result.job_id} 
                      result={result}
                      isSelected={selectedModes.includes(result.mode)}
                    />
                  ))}
                </div>
              ) : (
                <SliderComparison 
                  results={comparison.results.filter((r) => selectedModes.includes(r.mode))}
                  sliderValues={sliderValues}
                  setSliderValues={setSliderValues}
                />
              )}

              {/* Metrics Table */}
              <div className="mt-6 bg-gray-50 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Detailed Metrics
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-3 font-medium text-gray-700">Mode</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-700">File Size</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-700">Time</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-700">SSIM</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-700">Path Count</th>
                        <th className="text-right py-2 px-3 font-medium text-gray-700">Node Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {comparison.results
                        .filter((r) => selectedModes.includes(r.mode))
                        .map((result) => (
                        <tr key={result.job_id} className="border-b border-gray-100 last:border-0">
                          <td className="py-2 px-3 capitalize font-medium text-gray-900">{result.mode}</td>
                          <td className="text-right py-2 px-3 text-gray-600">{formatFileSize(result.file_size)}</td>
                          <td className="text-right py-2 px-3 text-gray-600">{formatTime(result.processing_time)}</td>
                          <td className="text-right py-2 px-3 text-gray-600">
                            {result.metrics?.ssim ? result.metrics.ssim.toFixed(3) : 'N/A'}
                          </td>
                          <td className="text-right py-2 px-3 text-gray-600">
                            {result.metrics?.path_count || 'N/A'}
                          </td>
                          <td className="text-right py-2 px-3 text-gray-600">
                            {result.metrics?.node_count || 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {comparison?.results.length || 0} modes compared
          </p>
          <button
            onClick={createComparison}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            Refresh Comparison
          </button>
        </div>
      </div>
    </div>
  );
}

interface ComparisonCardProps {
  result: ComparisonResult;
  isSelected: boolean;
}

function ComparisonCard({ result, isSelected }: ComparisonCardProps) {
  const [imageLoaded, setImageLoaded] = useState(false);

  if (!isSelected) return null;

  const modeColors: Record<string, string> = {
    fast: 'border-green-200 bg-green-50',
    standard: 'border-blue-200 bg-blue-50',
    high: 'border-purple-200 bg-purple-50',
    custom: 'border-orange-200 bg-orange-50',
  };

  return (
    <div className={`rounded-xl border-2 overflow-hidden ${modeColors[result.mode] || 'border-gray-200'}`}>
      {/* Header */}
      <div className="p-3 border-b border-black/5 flex items-center justify-between">
        <h3 className="font-semibold capitalize text-gray-900">{result.mode} Mode</h3>
        <span className="text-xs px-2 py-1 bg-white/50 rounded-full text-gray-600">
          {result.processing_time?.toFixed(1)}s
        </span>
      </div>

      {/* Preview */}
      <div className="aspect-square bg-gray-100 relative">
        {!imageLoaded && (
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
          </div>
        )}
        {result.svg_url && (
          <img
            src={result.svg_url}
            alt={`${result.mode} result`}
            className={`w-full h-full object-contain transition-opacity ${imageLoaded ? 'opacity-100' : 'opacity-0'}`}
            onLoad={() => setImageLoaded(true)}
          />
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">File Size</span>
          <span className="font-medium text-gray-900">
            {result.file_size ? `${(result.file_size / 1024).toFixed(1)} KB` : 'Pending...'}
          </span>
        </div>
        
        {result.metrics && (
          <>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Quality Score</span>
              <span className="font-medium text-gray-900">
                {result.metrics.quality_score?.toFixed(1) || 'N/A'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Paths</span>
              <span className="font-medium text-gray-900">
                {result.metrics.path_count || 'N/A'}
              </span>
            </div>
          </>
        )}

        {/* Download Button */}
        {result.svg_url && (
          <a
            href={result.svg_url}
            download={`${result.mode}.svg`}
            className="w-full mt-2 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center justify-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </a>
        )}
      </div>
    </div>
  );
}

interface SliderComparisonProps {
  results: ComparisonResult[];
  sliderValues: Record<string, number>;
  setSliderValues: (values: Record<string, number>) => void;
}

function SliderComparison({ results, sliderValues, setSliderValues }: SliderComparisonProps) {
  if (results.length < 2) {
    return (
      <div className="text-center py-12 text-gray-500">
        Select at least 2 modes to use slider comparison
      </div>
    );
  }

  const [leftResult, rightResult] = results.slice(0, 2);
  const sliderValue = sliderValues[leftResult.job_id] || 50;

  return (
    <div className="space-y-4">
      <div className="relative aspect-video bg-gray-100 rounded-xl overflow-hidden">
        {/* Left Image (bottom) */}
        {leftResult.svg_url && (
          <img
            src={leftResult.svg_url}
            alt={leftResult.mode}
            className="absolute inset-0 w-full h-full object-contain"
          />
        )}
        
        {/* Right Image (top, clipped) */}
        {rightResult.svg_url && (
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 ${100 - sliderValue}% 0 0)` }}
          >
            <img
              src={rightResult.svg_url}
              alt={rightResult.mode}
              className="absolute inset-0 w-full h-full object-contain"
            />
          </div>
        )}

        {/* Slider Handle */}
        <input
          type="range"
          min={0}
          max={100}
          value={sliderValue}
          onChange={(e) => {
            const value = parseInt(e.target.value);
            setSliderValues({ ...sliderValues, [leftResult.job_id]: value });
          }}
          className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize"
        />
        
        {/* Visual Slider Line */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-white shadow-lg pointer-events-none"
          style={{ left: `${sliderValue}%` }}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-8 bg-white rounded-full shadow-lg flex items-center justify-center">
            <div className="flex space-x-0.5">
              <div className="w-0.5 h-4 bg-gray-400" />
              <div className="w-0.5 h-4 bg-gray-400" />
            </div>
          </div>
        </div>

        {/* Labels */}
        <div className="absolute bottom-4 left-4 px-3 py-1.5 bg-black/70 text-white text-sm rounded-lg">
          {leftResult.mode}
        </div>
        <div className="absolute bottom-4 right-4 px-3 py-1.5 bg-black/70 text-white text-sm rounded-lg">
          {rightResult.mode}
        </div>
      </div>

      {/* Slider Control */}
      <div className="px-4">
        <input
          type="range"
          min={0}
          max={100}
          value={sliderValue}
          onChange={(e) => {
            const value = parseInt(e.target.value);
            setSliderValues({ ...sliderValues, [leftResult.job_id]: value });
          }}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span className="capitalize">{leftResult.mode}</span>
          <span>Drag to compare</span>
          <span className="capitalize">{rightResult.mode}</span>
        </div>
      </div>
    </div>
  );
}

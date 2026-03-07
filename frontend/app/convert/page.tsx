'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Play, Loader2 } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { ConversionForm } from '@/components/ConversionForm';
import { ProgressTracker } from '@/components/ProgressTracker';
import { useUploadStore, useConversionOptionsStore, useJobStore } from '@/lib/store';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

export default function ConvertPage() {
  const [activeJobs, setActiveJobs] = useState<string[]>([]);
  const [isConverting, setIsConverting] = useState(false);

  const { fileId, file, reset: resetUpload } = useUploadStore();
  const { image_type, quality_mode, color_palette, denoise_strength } = useConversionOptionsStore();
  const { addJob } = useJobStore();

  const handleConvert = async () => {
    if (!fileId) {
      toast.error('Please upload an image first');
      return;
    }

    setIsConverting(true);

    try {
      const response = await apiClient.convert(fileId, {
        image_type,
        quality_mode,
        color_palette,
        denoise_strength,
      });

      // Add to active jobs
      setActiveJobs((prev) => [...prev, response.job_id]);

      // Add to job store
      addJob({
        jobId: response.job_id,
        fileName: file?.name || 'unknown',
        status: 'pending',
        progress: 0,
        error: null,
        resultUrl: null,
        createdAt: new Date().toISOString(),
        completedAt: null,
        processingTime: null,
      });

      toast.success('Conversion started!');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to start conversion');
    } finally {
      setIsConverting(false);
    }
  };

  const handleComplete = (jobId: string) => {
    toast.success('Conversion completed!');
  };

  const handleError = (jobId: string, error: string) => {
    toast.error(`Conversion failed: ${error}`);
  };

  const handleNewConversion = () => {
    resetUpload();
    setActiveJobs([]);
  };

  const canConvert = fileId && !isConverting;

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back to Home
            </Link>
            <h1 className="text-xl font-bold text-gray-900">Convert Image</h1>
            <div className="w-24" />
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Upload */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                1. Upload Image
              </h2>
              <FileUpload />
            </div>

            {/* Active Conversions */}
            {activeJobs.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Conversions
                  </h2>
                  <button
                    onClick={handleNewConversion}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    New Conversion
                  </button>
                </div>
                <div className="space-y-4">
                  {activeJobs.map((jobId) => (
                    <ProgressTracker
                      key={jobId}
                      jobId={jobId}
                      fileName={file?.name || 'unknown'}
                      onComplete={() => handleComplete(jobId)}
                      onError={(error) => handleError(jobId, error)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Options */}
          <div className="space-y-6">
            <ConversionForm />

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
                    Starting...
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
        </div>
      </div>
    </main>
  );
}

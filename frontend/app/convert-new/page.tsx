'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { ProgressTracker } from '@/components/ProgressTracker';
import { EnhancedConversionForm } from '@/components/EnhancedConversionForm';
import { PreviewPanel } from '@/components/PreviewPanel';
import { useUploadStore, useJobStore } from '@/lib/store';
import { usePreviewStore } from '@/lib/advanced-store';
import toast from 'react-hot-toast';

export default function NewConvertPage() {
  const [activeJobs, setActiveJobs] = useState<string[]>([]);

  const { fileId, file, reset: resetUpload } = useUploadStore();
  const { addJob } = useJobStore();

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

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Back to Home
            </Link>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                New
              </span>
              <h1 className="text-xl font-bold text-gray-900">Enhanced Convert</h1>
            </div>
            <div className="w-24" />
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column - Upload and Preview */}
          <div className="lg:col-span-5 space-y-6">
            {/* Upload */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                1. Upload Image
              </h2>
              <FileUpload />
            </div>

            {/* Preview Panel */}
            {fileId && (
              <PreviewPanel />
            )}

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
          <div className="lg:col-span-7">
            <EnhancedConversionForm />
          </div>
        </div>
      </div>
    </main>
  );
}

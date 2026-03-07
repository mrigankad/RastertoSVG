'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle, XCircle, Loader2, Clock, Download } from 'lucide-react';
import { pollJobStatus, JobStatus } from '@/lib/api';
import { useJobStore, useHistoryStore } from '@/lib/store';

interface ProgressTrackerProps {
  jobId: string;
  fileName: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export function ProgressTracker({ jobId, fileName, onComplete, onError }: ProgressTrackerProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [cleanup, setCleanup] = useState<(() => void) | null>(null);

  const { updateJob, removeJob } = useJobStore();
  const { addToHistory } = useHistoryStore();

  // Format elapsed time
  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // Download result
  const handleDownload = useCallback(async () => {
    if (!status?.result_url) return;

    try {
      const { apiClient } = await import('@/lib/api');
      const blob = await apiClient.downloadResult(jobId);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${fileName.replace(/\.[^/.]+$/, '')}.svg`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  }, [jobId, fileName, status?.result_url]);

  // Start polling when component mounts
  useEffect(() => {
    if (!jobId) return;

    // Update store
    updateJob(jobId, { jobId, fileName, status: 'pending', progress: 0 });

    // Start polling
    const startPolling = async () => {
      const cleanupFn = await pollJobStatus(
        jobId,
        (newStatus: JobStatus) => {
          setStatus(newStatus);
          updateJob(jobId, {
            status: newStatus.status,
            progress: newStatus.progress,
            error: newStatus.error,
            resultUrl: newStatus.result_url || undefined,
            completedAt: newStatus.completed_at || undefined,
            processingTime: newStatus.processing_time || undefined,
          });
        },
        (completedStatus: JobStatus) => {
          // On complete
          onComplete?.();
          addToHistory({
            id: jobId,
            fileName,
            fileSize: 0, // Would need to get from upload
            quality: status?.options?.quality_mode || 'standard',
            imageType: status?.options?.image_type || 'auto',
            status: 'completed',
            createdAt: completedStatus.created_at,
            completedAt: completedStatus.completed_at || new Date().toISOString(),
            processingTime: completedStatus.processing_time || undefined,
          });
        },
        (error: string) => {
          // On error
          onError?.(error);
          addToHistory({
            id: jobId,
            fileName,
            fileSize: 0,
            quality: status?.options?.quality_mode || 'standard',
            imageType: status?.options?.image_type || 'auto',
            status: 'failed',
            createdAt: status?.created_at || new Date().toISOString(),
            completedAt: new Date().toISOString(),
          });
        }
      );

      setCleanup(() => cleanupFn);
    };

    startPolling();

    return () => {
      cleanup?.();
    };
  }, [jobId, fileName]);

  // Timer for elapsed time
  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed') {
      return;
    }

    const timer = setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [status?.status]);

  // Get status color and icon
  const getStatusDisplay = () => {
    switch (status?.status) {
      case 'pending':
        return {
          icon: Clock,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          text: 'Pending',
          description: 'Waiting to start...',
        };
      case 'processing':
        return {
          icon: Loader2,
          color: 'text-blue-500',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          text: 'Processing',
          description: 'Converting your image...',
        };
      case 'completed':
        return {
          icon: CheckCircle,
          color: 'text-green-500',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          text: 'Completed',
          description: status?.processing_time
            ? `Finished in ${status.processing_time.toFixed(1)}s`
            : 'Conversion complete!',
        };
      case 'failed':
        return {
          icon: XCircle,
          color: 'text-red-500',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          text: 'Failed',
          description: status?.error || 'Conversion failed',
        };
      default:
        return {
          icon: Clock,
          color: 'text-gray-400',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          text: 'Starting',
          description: 'Initializing...',
        };
    }
  };

  const display = getStatusDisplay();
  const Icon = display.icon;
  const isProcessing = status?.status === 'processing' || status?.status === 'pending';
  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed';

  return (
    <div className={`rounded-xl border-2 p-6 ${display.bgColor} ${display.borderColor}`}>
      <div className="flex items-start space-x-4">
        <div className={`
          p-3 rounded-full
          ${isProcessing ? 'animate-pulse' : ''}
        `}>
          <Icon className={`w-8 h-8 ${display.color} ${isProcessing ? 'animate-spin' : ''}`} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="font-semibold text-gray-900">
              {display.text}
            </h4>
            <span className="text-sm text-gray-500">
              {formatTime(elapsed)}
            </span>
          </div>

          <p className="text-sm text-gray-600 mb-3">
            {fileName}
          </p>

          <p className="text-sm text-gray-500">
            {display.description}
          </p>

          {/* Progress bar */}
          {isProcessing && (
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Progress</span>
                <span className="font-medium text-gray-900">
                  {Math.round((status?.progress || 0) * 100)}%
                </span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-500 rounded-full"
                  style={{ width: `${(status?.progress || 0) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Download button */}
          {isCompleted && (
            <div className="mt-4">
              <button
                onClick={handleDownload}
                className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Download className="w-4 h-4 mr-2" />
                Download SVG
              </button>
            </div>
          )}

          {/* Error message */}
          {isFailed && (
            <div className="mt-4">
              <button
                onClick={() => removeJob(jobId)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Dismiss
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

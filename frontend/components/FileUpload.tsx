'use client';

import React, { useCallback, useRef, useState } from 'react';
import { Upload, Image, X, FileCheck } from 'lucide-react';
import { useUploadStore } from '../lib/store';
import { apiClient } from '../lib/api';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/tiff', 'image/gif', 'image/webp'];

export function FileUpload() {
  const [isDragging, setIsDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    file,
    fileId,
    isUploading,
    uploadProgress,
    error,
    setFile,
    setFileId,
    setIsUploading,
    setUploadProgress,
    setError,
    reset,
  } = useUploadStore();

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return 'Invalid file type. Please upload PNG, JPG, BMP, TIFF, GIF, or WEBP.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 50MB.';
    }
    return null;
  };

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    // Validate
    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setFile(selectedFile);

    // Create preview
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);

    // Upload
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const response = await apiClient.upload(selectedFile, (progress: number) => {
        setUploadProgress(progress);
      });

      setFileId(response.file_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setFile(null);
      setPreviewUrl(null);
    } finally {
      setIsUploading(false);
    }
  }, [setFile, setFileId, setIsUploading, setUploadProgress, setError]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleClear = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    reset();
    setPreviewUrl(null);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full">
      {file && previewUrl ? (
        // File selected - show preview
        <div className="relative bg-white rounded-xl border-2 border-gray-200 overflow-hidden">
          <div className="aspect-video relative">
            <img
              src={previewUrl}
              alt="Preview"
              className="w-full h-full object-contain bg-gray-50"
            />
            <button
              onClick={handleClear}
              className="absolute top-2 right-2 p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
              disabled={isUploading}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileCheck className="w-5 h-5 text-green-500" />
                <div>
                  <p className="font-medium text-gray-900 truncate max-w-xs">
                    {file.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {formatFileSize(file.size)}
                  </p>
                </div>
              </div>

              {isUploading && (
                <div className="text-right">
                  <p className="text-sm font-medium text-blue-600">
                    {uploadProgress}%
                  </p>
                </div>
              )}

              {fileId && !isUploading && (
                <span className="text-sm text-green-600 font-medium">
                  Ready
                </span>
              )}
            </div>

            {isUploading && (
              <div className="mt-3">
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        // No file - show dropzone
        <div
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
            transition-all duration-200
            ${isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100'
            }
          `}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleInputChange}
            className="hidden"
          />

          <div className="flex flex-col items-center">
            <div className={`
              p-4 rounded-full mb-4
              ${isDragging ? 'bg-blue-100' : 'bg-gray-100'}
            `}>
              {isDragging ? (
                <Image className="w-8 h-8 text-blue-500" />
              ) : (
                <Upload className="w-8 h-8 text-gray-400" />
              )}
            </div>

            <p className="text-lg font-medium text-gray-900 mb-2">
              {isDragging ? 'Drop your image here' : 'Drop your image here'}
            </p>
            <p className="text-gray-500 mb-4">
              or click to browse
            </p>

            <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-400">
              <span className="px-2 py-1 bg-gray-100 rounded">PNG</span>
              <span className="px-2 py-1 bg-gray-100 rounded">JPG</span>
              <span className="px-2 py-1 bg-gray-100 rounded">BMP</span>
              <span className="px-2 py-1 bg-gray-100 rounded">TIFF</span>
              <span className="px-2 py-1 bg-gray-100 rounded">GIF</span>
              <span className="px-2 py-1 bg-gray-100 rounded">WEBP</span>
            </div>

            <p className="text-xs text-gray-400 mt-4">
              Maximum file size: 50MB
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}

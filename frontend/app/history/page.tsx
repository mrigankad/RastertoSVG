'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Download, Trash2, FileImage, Search, Filter, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useHistoryStore } from '@/lib/store';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';

export default function HistoryPage() {
  const { history, removeFromHistory, clearHistory } = useHistoryStore();
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed'>('all');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Filter and search history
  const filteredHistory = history.filter((item: any) => {
    const matchesSearch = item.fileName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filter === 'all' || item.status === filter;
    return matchesSearch && matchesFilter;
  });

  const handleDownload = async (jobId: string, fileName: string) => {
    setDownloadingId(jobId);
    try {
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

      toast.success('Download started');
    } catch (err) {
      toast.error('Download failed. The file may have expired.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to remove this item from history?')) {
      removeFromHistory(id);
      toast.success('Removed from history');
    }
  };

  const handleClearAll = () => {
    if (confirm('Are you sure you want to clear all history?')) {
      clearHistory();
      toast.success('History cleared');
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getQualityBadge = (quality: string) => {
    const colors: Record<string, string> = {
      fast: 'bg-green-100 text-green-700',
      standard: 'bg-blue-100 text-blue-700',
      high: 'bg-purple-100 text-purple-700',
    };
    return colors[quality] || 'bg-gray-100 text-gray-700';
  };

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
            <h1 className="text-xl font-bold text-gray-900">Conversion History</h1>
            <div className="w-24" />
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Controls */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by filename..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Filter */}
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as any)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="all">All</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            {/* Clear All */}
            {history.length > 0 && (
              <button
                onClick={handleClearAll}
                className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg font-medium transition-colors"
              >
                Clear All
              </button>
            )}
          </div>
        </div>

        {/* History List */}
        {filteredHistory.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <FileImage className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {history.length === 0 ? 'No conversions yet' : 'No matching results'}
            </h3>
            <p className="text-gray-500 mb-6">
              {history.length === 0
                ? 'Your conversion history will appear here'
                : 'Try adjusting your search or filter'}
            </p>
            <Link
              href="/convert"
              className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Start Converting
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-200 bg-gray-50">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-900">
                  {filteredHistory.length} {filteredHistory.length === 1 ? 'conversion' : 'conversions'}
                </h2>
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm('')}
                    className="text-sm text-blue-600 hover:text-blue-700"
                  >
                    Clear search
                  </button>
                )}
              </div>
            </div>

            <div className="divide-y divide-gray-100">
              {filteredHistory.map((item: any) => (
                <div
                  key={item.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 min-w-0">
                      <div className="flex-shrink-0">
                        {getStatusIcon(item.status)}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 truncate">
                          {item.fileName}
                        </p>
                        <div className="flex items-center space-x-3 mt-1 text-sm text-gray-500">
                          <span>{formatDate(item.createdAt)}</span>
                          <span className="w-1 h-1 bg-gray-300 rounded-full" />
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getQualityBadge(item.quality)}`}>
                            {item.quality}
                          </span>
                          <span className="text-gray-400 capitalize">
                            {item.imageType}
                          </span>
                          {item.processingTime && (
                            <>
                              <span className="w-1 h-1 bg-gray-300 rounded-full" />
                              <span>{item.processingTime.toFixed(1)}s</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-4">
                      {item.status === 'completed' && (
                        <button
                          onClick={() => handleDownload(item.id, item.fileName)}
                          disabled={downloadingId === item.id}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Download"
                        >
                          {downloadingId === item.id ? (
                            <span className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <Download className="w-5 h-5" />
                          )}
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(item.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Remove from history"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart3,
  TrendingUp,
  Clock,
  FileImage,
  Zap,
  Calendar,
  Download,
  ChevronDown,
  ChevronUp,
  Filter,
  RefreshCw,
  PieChart,
  Activity,
} from 'lucide-react';
import { useHistoryStore } from '@/lib/store';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: React.ElementType;
  color: string;
}

function MetricCard({ title, value, change, changeType = 'neutral', icon: Icon, color }: MetricCardProps) {
  const changeColors = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-500',
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change && (
            <p className={`text-sm mt-1 ${changeColors[changeType]}`}>
              {changeType === 'positive' && '↑ '}
              {changeType === 'negative' && '↓ '}
              {change}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}

interface ConversionTrend {
  date: string;
  count: number;
  successRate: number;
}

export function MetricsDashboard() {
  const { history } = useHistoryStore();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [showDetails, setShowDetails] = useState(false);

  // Filter history based on time range
  const filteredHistory = useMemo(() => {
    const now = new Date();
    const ranges = {
      '7d': 7,
      '30d': 30,
      '90d': 90,
      'all': 365 * 10,
    };
    
    const days = ranges[timeRange];
    const cutoff = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    
    return history.filter((item) => new Date(item.createdAt) >= cutoff);
  }, [history, timeRange]);

  // Calculate metrics
  const metrics = useMemo(() => {
    const total = filteredHistory.length;
    const completed = filteredHistory.filter((h) => h.status === 'completed').length;
    const failed = filteredHistory.filter((h) => h.status === 'failed').length;
    const successRate = total > 0 ? (completed / total) * 100 : 0;
    
    const avgTime = total > 0
      ? filteredHistory.reduce((sum, h) => sum + (h.processingTime || 0), 0) / total
      : 0;
    
    // Quality mode distribution
    const qualityDist = filteredHistory.reduce((acc, h) => {
      acc[h.quality] = (acc[h.quality] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    // Image type distribution
    const typeDist = filteredHistory.reduce((acc, h) => {
      acc[h.imageType] = (acc[h.imageType] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    // Daily trend
    const trend: Record<string, { count: number; completed: number }> = {};
    filteredHistory.forEach((h) => {
      const date = new Date(h.createdAt).toLocaleDateString();
      if (!trend[date]) {
        trend[date] = { count: 0, completed: 0 };
      }
      trend[date].count++;
      if (h.status === 'completed') {
        trend[date].completed++;
      }
    });
    
    const trendData: ConversionTrend[] = Object.entries(trend)
      .map(([date, data]) => ({
        date,
        count: data.count,
        successRate: data.count > 0 ? (data.completed / data.count) * 100 : 0,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .slice(-14); // Last 14 days
    
    return {
      total,
      completed,
      failed,
      successRate,
      avgTime,
      qualityDist,
      typeDist,
      trendData,
    };
  }, [filteredHistory]);

  // Calculate file size metrics
  const sizeMetrics = useMemo(() => {
    // Mock data - in real app would come from history
    return {
      totalInputSize: '1.2 GB',
      totalOutputSize: '45 MB',
      avgCompression: '85%',
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="w-6 h-6 mr-2 text-blue-500" />
            Conversion Metrics
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Track your conversion performance and statistics
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as typeof timeRange)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="all">All time</option>
          </select>
          
          <button
            onClick={() => window.location.reload()}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Conversions"
          value={metrics.total}
          change={`${metrics.trendData[metrics.trendData.length - 1]?.count || 0} today`}
          changeType="neutral"
          icon={FileImage}
          color="bg-blue-500"
        />
        <MetricCard
          title="Success Rate"
          value={`${metrics.successRate.toFixed(1)}%`}
          change={`${metrics.completed} successful`}
          changeType={metrics.successRate >= 90 ? 'positive' : 'neutral'}
          icon={TrendingUp}
          color="bg-green-500"
        />
        <MetricCard
          title="Avg. Processing Time"
          value={`${metrics.avgTime.toFixed(1)}s`}
          change="Per conversion"
          changeType="neutral"
          icon={Clock}
          color="bg-purple-500"
        />
        <MetricCard
          title="Compression Ratio"
          value={sizeMetrics.avgCompression}
          change={`${sizeMetrics.totalInputSize} → ${sizeMetrics.totalOutputSize}`}
          changeType="positive"
          icon={Zap}
          color="bg-orange-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trend Chart */}
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-blue-500" />
            Conversion Trend
          </h3>
          
          {metrics.trendData.length > 0 ? (
            <div className="space-y-2">
              {metrics.trendData.map((day, index) => (
                <div key={day.date} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16">{day.date}</span>
                  <div className="flex-1 h-8 bg-gray-100 rounded-lg overflow-hidden flex">
                    <div
                      className="h-full bg-blue-500 transition-all duration-500"
                      style={{ width: `${Math.min((day.count / 10) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-gray-700 w-8">{day.count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-400 py-8">No data available</p>
          )}
        </div>

        {/* Quality Distribution */}
        <div className="bg-white rounded-xl p-5 border border-gray-200 shadow-sm">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
            <PieChart className="w-5 h-5 mr-2 text-green-500" />
            Quality Mode Distribution
          </h3>
          
          <div className="space-y-3">
            {Object.entries(metrics.qualityDist).map(([quality, count]) => {
              const percentage = metrics.total > 0 ? (count / metrics.total) * 100 : 0;
              const colors: Record<string, string> = {
                fast: 'bg-green-500',
                standard: 'bg-blue-500',
                high: 'bg-purple-500',
              };
              
              return (
                <div key={quality}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700 capitalize">{quality}</span>
                    <span className="text-sm text-gray-500">{count} ({percentage.toFixed(1)}%)</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${colors[quality] || 'bg-gray-500'} transition-all duration-500`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
            
            {Object.keys(metrics.qualityDist).length === 0 && (
              <p className="text-center text-gray-400 py-8">No data available</p>
            )}
          </div>
        </div>
      </div>

      {/* Detailed Stats */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full p-4 flex items-center justify-between bg-gray-50/50 hover:bg-gray-100/50 transition-colors"
        >
          <div className="flex items-center">
            <Filter className="w-5 h-5 text-gray-500 mr-2" />
            <span className="font-semibold text-gray-900">Detailed Statistics</span>
          </div>
          {showDetails ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {showDetails && (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Image Type Distribution */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Image Type Distribution</h4>
                <div className="space-y-2">
                  {Object.entries(metrics.typeDist).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                      <span className="text-sm text-gray-600 capitalize">{type}</span>
                      <span className="text-sm font-medium text-gray-900">{count}</span>
                    </div>
                  ))}
                  {Object.keys(metrics.typeDist).length === 0 && (
                    <p className="text-sm text-gray-400">No data</p>
                  )}
                </div>
              </div>

              {/* Processing Stats */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-3">Processing Statistics</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-600">Completed</span>
                    <span className="text-sm font-medium text-green-600">{metrics.completed}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-600">Failed</span>
                    <span className="text-sm font-medium text-red-600">{metrics.failed}</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-600">Success Rate</span>
                    <span className="text-sm font-medium text-gray-900">{metrics.successRate.toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <span className="text-sm text-gray-600">Avg. Time</span>
                    <span className="text-sm font-medium text-gray-900">{metrics.avgTime.toFixed(2)}s</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Export */}
            <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => {
                  const data = JSON.stringify(metrics, null, 2);
                  const blob = new Blob([data], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `metrics-${new Date().toISOString().split('T')[0]}.json`;
                  a.click();
                }}
                className="flex items-center px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              >
                <Download className="w-4 h-4 mr-2" />
                Export Data
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tips */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
        <h4 className="font-medium text-blue-900 mb-2 flex items-center">
          <Zap className="w-4 h-4 mr-2" />
          Performance Tips
        </h4>
        <ul className="text-sm text-blue-700 space-y-1">
          {metrics.successRate < 90 && (
            <li>• Your success rate is below 90%. Try using Standard or High quality mode for better results.</li>
          )}
          {metrics.avgTime > 10 && (
            <li>• Average processing time is high. Consider using Fast mode for simpler images.</li>
          )}
          <li>• Use batch processing for multiple files to save time.</li>
          <li>• Enable comparison mode to find the best quality settings for your images.</li>
        </ul>
      </div>
    </div>
  );
}

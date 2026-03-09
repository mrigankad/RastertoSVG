/**
 * WebSocket hook for real-time job updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export type WebSocketMessage = 
  | { type: 'job.status'; job_id: string; data: any }
  | { type: 'job.progress'; job_id: string; progress: number; stage: string; timestamp: string }
  | { type: 'job.completed'; job_id: string; result: any; timestamp: string }
  | { type: 'job.failed'; job_id: string; error: string; timestamp: string }
  | { type: 'subscription.confirmed'; job_id: string }
  | { type: 'pong'; timestamp: string }
  | { type: 'notification'; data: any; timestamp: string }
  | { type: 'error'; message: string };

interface UseWebSocketOptions {
  jobIds?: string[];
  userId?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  sendMessage: (message: any) => void;
  subscribeToJob: (jobId: string) => void;
  unsubscribeFromJob: (jobId: string) => void;
  getJobStatus: (jobId: string) => void;
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export function useWebSocket({
  jobIds = [],
  userId,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketOptions = {}): UseWebSocketReturn {
  const ws = useRef<WebSocket | null>(null);
  const [connectionState, setConnectionState] = useState<UseWebSocketReturn['connectionState']>('disconnected');
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const subscribedJobs = useRef<Set<string>>(new Set());

  const isConnected = connectionState === 'connected';

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');

    // Build connection URL with query params
    const url = new URL('/ws', WS_URL);
    if (jobIds.length > 0) {
      url.searchParams.set('jobs', jobIds.join(','));
    }
    if (userId) {
      url.searchParams.set('user_id', userId);
    }

    ws.current = new WebSocket(url.toString());

    ws.current.onopen = () => {
      setConnectionState('connected');
      reconnectAttempts.current = 0;
      
      // Resubscribe to previously subscribed jobs
      subscribedJobs.current.forEach((jobId) => {
        sendMessage({ action: 'subscribe', job_id: jobId });
      });
      
      onConnect?.();
    };

    ws.current.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        onMessage?.(message);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.current.onclose = () => {
      setConnectionState('disconnected');
      onDisconnect?.();

      if (reconnect && reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current += 1;
        reconnectTimer.current = setTimeout(() => {
          console.log(`Reconnecting... Attempt ${reconnectAttempts.current}`);
          connect();
        }, reconnectInterval);
      }
    };

    ws.current.onerror = (error) => {
      setConnectionState('error');
      onError?.(error);
    };
  }, [jobIds, userId, onConnect, onDisconnect, onError, reconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const subscribeToJob = useCallback((jobId: string) => {
    subscribedJobs.current.add(jobId);
    sendMessage({ action: 'subscribe', job_id: jobId });
  }, [sendMessage]);

  const unsubscribeFromJob = useCallback((jobId: string) => {
    subscribedJobs.current.delete(jobId);
    sendMessage({ action: 'unsubscribe', job_id: jobId });
  }, [sendMessage]);

  const getJobStatus = useCallback((jobId: string) => {
    sendMessage({ action: 'get_status', job_id: jobId });
  }, [sendMessage]);

  // Connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      sendMessage({ action: 'ping' });
    }, 30000); // Ping every 30 seconds

    return () => {
      clearInterval(pingInterval);
    };
  }, [isConnected, sendMessage]);

  return {
    sendMessage,
    subscribeToJob,
    unsubscribeFromJob,
    getJobStatus,
    isConnected,
    connectionState,
  };
}

// Hook specifically for tracking a single job
interface UseJobTrackingOptions {
  jobId: string;
  onProgress?: (progress: number, stage: string) => void;
  onCompleted?: (result: any) => void;
  onFailed?: (error: string) => void;
}

export function useJobTracking({
  jobId,
  onProgress,
  onCompleted,
  onFailed,
}: UseJobTrackingOptions) {
  const [jobData, setJobData] = useState<any>(null);
  const [progress, setProgress] = useState<number>(0);
  const [stage, setStage] = useState<string>('');
  const [status, setStatus] = useState<string>('pending');

  const { subscribeToJob, unsubscribeFromJob, isConnected } = useWebSocket({
    jobIds: [jobId],
    onMessage: (message) => {
      switch (message.type) {
        case 'job.status':
          setJobData(message.data);
          setStatus(message.data?.status || 'pending');
          setProgress(message.data?.progress || 0);
          break;
        
        case 'job.progress':
          setProgress(message.progress);
          setStage(message.stage);
          onProgress?.(message.progress, message.stage);
          break;
        
        case 'job.completed':
          setStatus('completed');
          setProgress(1);
          setJobData((prev: any) => ({ ...prev, ...message.result }));
          onCompleted?.(message.result);
          break;
        
        case 'job.failed':
          setStatus('failed');
          onFailed?.(message.error);
          break;
      }
    },
  });

  useEffect(() => {
    if (jobId && isConnected) {
      subscribeToJob(jobId);
      
      return () => {
        unsubscribeFromJob(jobId);
      };
    }
  }, [jobId, isConnected, subscribeToJob, unsubscribeFromJob]);

  return {
    jobData,
    progress,
    stage,
    status,
    isConnected,
  };
}

// Hook for tracking multiple jobs
interface UseBatchTrackingOptions {
  jobIds: string[];
  onJobUpdate?: (jobId: string, data: any) => void;
  onJobCompleted?: (jobId: string, result: any) => void;
  onJobFailed?: (jobId: string, error: string) => void;
  onAllCompleted?: () => void;
}

export function useBatchTracking({
  jobIds,
  onJobUpdate,
  onJobCompleted,
  onJobFailed,
  onAllCompleted,
}: UseBatchTrackingOptions) {
  const [jobsData, setJobsData] = useState<Record<string, any>>({});
  const completedJobs = useRef<Set<string>>(new Set());

  const { isConnected } = useWebSocket({
    jobIds,
    onMessage: (message) => {
      switch (message.type) {
        case 'job.status':
          setJobsData((prev) => ({
            ...prev,
            [message.job_id]: message.data,
          }));
          onJobUpdate?.(message.job_id, message.data);
          break;
        
        case 'job.completed':
          completedJobs.current.add(message.job_id);
          setJobsData((prev) => ({
            ...prev,
            [message.job_id]: { ...prev[message.job_id], ...message.result, status: 'completed' },
          }));
          onJobCompleted?.(message.job_id, message.result);
          
          // Check if all jobs completed
          if (completedJobs.current.size === jobIds.length) {
            onAllCompleted?.();
          }
          break;
        
        case 'job.failed':
          completedJobs.current.add(message.job_id);
          setJobsData((prev) => ({
            ...prev,
            [message.job_id]: { ...prev[message.job_id], status: 'failed', error: message.error },
          }));
          onJobFailed?.(message.job_id, message.error);
          break;
      }
    },
  });

  const completedCount = completedJobs.current.size;
  const totalCount = jobIds.length;
  const isComplete = completedCount === totalCount;
  const progress = totalCount > 0 ? completedCount / totalCount : 0;

  return {
    jobsData,
    completedCount,
    totalCount,
    progress,
    isComplete,
    isConnected,
  };
}

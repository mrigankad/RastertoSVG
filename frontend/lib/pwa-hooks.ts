/**
 * PWA hooks — Phase 8
 *
 * Custom React hooks for PWA functionality:
 * - Service worker registration & lifecycle
 * - Install prompt handling
 * - Online/offline state
 * - Background sync notifications
 */

'use client';

import { useEffect, useCallback, useState } from 'react';
import { usePWAStore } from './wasm-store';

/**
 * Register the service worker and track its lifecycle.
 */
export function useServiceWorker() {
    const {
        setServiceWorkerStatus,
        setOnline,
        setInstallPrompt,
        setInstalled,
    } = usePWAStore();

    useEffect(() => {
        if (typeof window === 'undefined') return;
        if (!('serviceWorker' in navigator)) return;

        // Register service worker
        const registerSW = async () => {
            try {
                setServiceWorkerStatus('installing');

                const registration = await navigator.serviceWorker.register('/sw.js', {
                    scope: '/',
                });

                if (registration.installing) {
                    setServiceWorkerStatus('installing');
                } else if (registration.waiting) {
                    setServiceWorkerStatus('installed');
                } else if (registration.active) {
                    setServiceWorkerStatus('activated');
                }

                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    if (newWorker) {
                        newWorker.addEventListener('statechange', () => {
                            switch (newWorker.state) {
                                case 'installed':
                                    setServiceWorkerStatus('installed');
                                    break;
                                case 'activating':
                                    setServiceWorkerStatus('activating');
                                    break;
                                case 'activated':
                                    setServiceWorkerStatus('activated');
                                    break;
                            }
                        });
                    }
                });

                // Listen for messages from SW
                navigator.serviceWorker.addEventListener('message', (event) => {
                    if (event.data?.type === 'sync-complete') {
                        // Background sync completed
                        console.log('Background sync completed for:', event.data.id);
                    }
                });
            } catch (error) {
                console.error('SW registration failed:', error);
                setServiceWorkerStatus('error');
            }
        };

        registerSW();

        // Online/offline listeners
        const onOnline = () => setOnline(true);
        const onOffline = () => setOnline(false);
        window.addEventListener('online', onOnline);
        window.addEventListener('offline', onOffline);

        // Install prompt
        const onBeforeInstall = (e: Event) => {
            e.preventDefault();
            setInstallPrompt(e);
        };
        window.addEventListener('beforeinstallprompt', onBeforeInstall);

        // Detect if already installed
        if (window.matchMedia('(display-mode: standalone)').matches) {
            setInstalled(true);
        }

        return () => {
            window.removeEventListener('online', onOnline);
            window.removeEventListener('offline', onOffline);
            window.removeEventListener('beforeinstallprompt', onBeforeInstall);
        };
    }, [setServiceWorkerStatus, setOnline, setInstallPrompt, setInstalled]);
}

/**
 * Hook for PWA install prompt.
 */
export function useInstallPrompt() {
    const { canInstall, installPrompt, setInstallPrompt, setInstalled } = usePWAStore();

    const install = useCallback(async () => {
        if (!installPrompt) return false;

        const result = await installPrompt.prompt();

        if (result.outcome === 'accepted') {
            setInstalled(true);
            setInstallPrompt(null);
            return true;
        }

        return false;
    }, [installPrompt, setInstalled, setInstallPrompt]);

    return { canInstall, install };
}

/**
 * Hook for online/offline status.
 */
export function useOnlineStatus() {
    const { isOnline } = usePWAStore();
    return isOnline;
}

/**
 * Hook for WASM conversion with progress.
 */
export function useWasmConversion() {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        // Check WASM support on mount
        try {
            const supported = typeof WebAssembly === 'object';
            setIsReady(supported);
        } catch {
            setIsReady(false);
        }
    }, []);

    return { isReady };
}

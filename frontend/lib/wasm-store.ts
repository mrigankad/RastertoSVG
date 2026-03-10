/**
 * WASM & Hybrid processing state management — Phase 8.
 *
 * Zustand store for managing:
 * - WASM engine initialization state
 * - Processing route preferences
 * - Conversion history (WASM vs server)
 * - Offline state & PWA install prompt
 * - Client-side preprocessing settings
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
    WasmCapabilities,
} from './wasm-engine';
import { getWasmCapabilities } from './wasm-engine';
import type { ProcessingRoute, HybridConversionResult } from './hybrid-processor';

// =============================================================================
// WASM Engine Store
// =============================================================================

interface WasmEngineState {
    // Capabilities
    capabilities: WasmCapabilities;
    isInitialized: boolean;
    isInitializing: boolean;
    initError: string | null;

    // Processing preferences
    preferredRoute: ProcessingRoute;
    autoRouting: boolean;

    // Current conversion
    isConverting: boolean;
    conversionProgress: number;
    conversionStage: string;
    currentRoute: ProcessingRoute | null;

    // Results
    lastResult: HybridConversionResult | null;

    // Actions
    setCapabilities: (caps: WasmCapabilities) => void;
    setInitialized: (initialized: boolean) => void;
    setInitializing: (initializing: boolean) => void;
    setInitError: (error: string | null) => void;
    setPreferredRoute: (route: ProcessingRoute) => void;
    setAutoRouting: (auto: boolean) => void;
    setConversionProgress: (progress: number, stage: string, route: ProcessingRoute) => void;
    setIsConverting: (converting: boolean) => void;
    setLastResult: (result: HybridConversionResult | null) => void;
    reset: () => void;
}

export const useWasmStore = create<WasmEngineState>()((set) => ({
    capabilities: getWasmCapabilities(),
    isInitialized: false,
    isInitializing: false,
    initError: null,

    preferredRoute: 'wasm' as ProcessingRoute,
    autoRouting: true,

    isConverting: false,
    conversionProgress: 0,
    conversionStage: '',
    currentRoute: null,

    lastResult: null,

    setCapabilities: (capabilities: WasmCapabilities) => set({ capabilities }),
    setInitialized: (isInitialized: boolean) => set({ isInitialized }),
    setInitializing: (isInitializing: boolean) => set({ isInitializing }),
    setInitError: (initError: string | null) => set({ initError }),
    setPreferredRoute: (preferredRoute: ProcessingRoute) => set({ preferredRoute }),
    setAutoRouting: (autoRouting: boolean) => set({ autoRouting }),
    setConversionProgress: (conversionProgress: number, conversionStage: string, currentRoute: ProcessingRoute) =>
        set({ conversionProgress, conversionStage, currentRoute }),
    setIsConverting: (isConverting: boolean) => set({ isConverting }),
    setLastResult: (lastResult: HybridConversionResult | null) => set({ lastResult }),
    reset: () => set({
        isConverting: false,
        conversionProgress: 0,
        conversionStage: '',
        currentRoute: null,
        lastResult: null,
    }),
}));

// =============================================================================
// PWA Store
// =============================================================================

interface PWAState {
    isOnline: boolean;
    isInstalled: boolean;
    canInstall: boolean;
    installPrompt: any; // BeforeInstallPromptEvent
    serviceWorkerStatus: 'idle' | 'installing' | 'installed' | 'activating' | 'activated' | 'error';
    pendingConversions: number; // queued for background sync

    setOnline: (online: boolean) => void;
    setInstalled: (installed: boolean) => void;
    setCanInstall: (canInstall: boolean) => void;
    setInstallPrompt: (prompt: any) => void;
    setServiceWorkerStatus: (status: PWAState['serviceWorkerStatus']) => void;
    setPendingConversions: (count: number) => void;
}

export const usePWAStore = create<PWAState>()((set) => ({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isInstalled: false,
    canInstall: false,
    installPrompt: null,
    serviceWorkerStatus: 'idle' as const,
    pendingConversions: 0,

    setOnline: (isOnline: boolean) => set({ isOnline }),
    setInstalled: (isInstalled: boolean) => set({ isInstalled }),
    setCanInstall: (canInstall: boolean) => set({ canInstall }),
    setInstallPrompt: (installPrompt: any) => set({ installPrompt, canInstall: !!installPrompt }),
    setServiceWorkerStatus: (serviceWorkerStatus: PWAState['serviceWorkerStatus']) => set({ serviceWorkerStatus }),
    setPendingConversions: (pendingConversions: number) => set({ pendingConversions }),
}));

// =============================================================================
// Client Preprocessing Store
// =============================================================================

interface PreprocessingSettings {
    enabled: boolean;
    clientSide: boolean;
    denoise: boolean;
    denoiseStrength: number;
    contrast: boolean;
    contrastAmount: number;
    sharpen: boolean;
    sharpenAmount: number;
    colorReduce: boolean;
    maxColors: number;
    grayscale: boolean;
    threshold: boolean;
    thresholdValue: number;
    invert: boolean;
}

interface PreprocessingState extends PreprocessingSettings {
    setEnabled: (enabled: boolean) => void;
    setClientSide: (clientSide: boolean) => void;
    updateSetting: <K extends keyof PreprocessingSettings>(key: K, value: PreprocessingSettings[K]) => void;
    resetToDefaults: () => void;
}

const defaultPreprocessing: PreprocessingSettings = {
    enabled: false,
    clientSide: true,
    denoise: false,
    denoiseStrength: 5,
    contrast: false,
    contrastAmount: 1.5,
    sharpen: false,
    sharpenAmount: 1.5,
    colorReduce: false,
    maxColors: 32,
    grayscale: false,
    threshold: false,
    thresholdValue: 128,
    invert: false,
};

export const usePreprocessingStore = create<PreprocessingState>()(
    persist(
        (set) => ({
            ...defaultPreprocessing,

            setEnabled: (enabled: boolean) => set({ enabled }),
            setClientSide: (clientSide: boolean) => set({ clientSide }),
            updateSetting: <K extends keyof PreprocessingSettings>(key: K, value: PreprocessingSettings[K]) =>
                set({ [key]: value } as Partial<PreprocessingSettings>),
            resetToDefaults: () => set(defaultPreprocessing),
        }),
        {
            name: 'preprocessing-settings',
            storage: createJSONStorage(() => localStorage),
        }
    )
);

// =============================================================================
// Performance Stats Store
// =============================================================================

interface PerformanceEntry {
    id: string;
    timestamp: number;
    route: ProcessingRoute;
    conversionTime: number;
    totalTime: number;
    imageMegapixels: number;
    fileSize: number;
    success: boolean;
}

interface PerformanceState {
    entries: PerformanceEntry[];
    addEntry: (entry: PerformanceEntry) => void;
    clearEntries: () => void;
    getAverageTime: (route?: ProcessingRoute) => number;
    getSuccessRate: (route?: ProcessingRoute) => number;
}

export const usePerformanceStore = create<PerformanceState>()(
    persist(
        (set, get) => ({
            entries: [] as PerformanceEntry[],

            addEntry: (entry: PerformanceEntry) =>
                set((state) => ({
                    entries: [entry, ...state.entries].slice(0, 500),
                })),

            clearEntries: () => set({ entries: [] }),

            getAverageTime: (route?: ProcessingRoute): number => {
                let entries = get().entries.filter((e: PerformanceEntry) => e.success);
                if (route) entries = entries.filter((e: PerformanceEntry) => e.route === route);
                if (entries.length === 0) return 0;
                return entries.reduce((sum: number, e: PerformanceEntry) => sum + e.totalTime, 0) / entries.length;
            },

            getSuccessRate: (route?: ProcessingRoute): number => {
                let entries = get().entries;
                if (route) entries = entries.filter((e: PerformanceEntry) => e.route === route);
                if (entries.length === 0) return 0;
                return entries.filter((e: PerformanceEntry) => e.success).length / entries.length;
            },
        }),
        {
            name: 'performance-stats',
            storage: createJSONStorage(() => localStorage),
        }
    )
);

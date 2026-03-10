/**
 * Hybrid Processing Router — Phase 8
 *
 * Auto-routes conversion between client-side WASM and server-side
 * processing based on image size, complexity, and browser capabilities.
 *
 * Decision matrix:
 * ┌──────────────┬────────┬────────────────┐
 * │ Image Size   │ WASM?  │ Route          │
 * ├──────────────┼────────┼────────────────┤
 * │ < 1MP        │ Yes    │ WASM (client)  │
 * │ 1-5MP        │ Yes    │ WASM or Server │
 * │ > 5MP        │ Any    │ Server         │
 * │ Any          │ No     │ Server         │
 * └──────────────┴────────┴────────────────┘
 *
 * Complexity factors: color count, edge density, format
 */

import {
    WasmVectorEngine,
    WasmConversionOptions,
    WasmConversionResult,
    getWasmEngine,
    getWasmCapabilities,
    WasmCapabilities,
} from './wasm-engine';
import {
    ClientPreprocessor,
    PreprocessingOptions,
    getClientPreprocessor,
} from './client-preprocessor';
import { apiClient } from './api';

export type ProcessingRoute = 'wasm' | 'server' | 'hybrid';

export interface HybridConversionOptions {
    // Routing
    preferredRoute?: ProcessingRoute;
    forceRoute?: ProcessingRoute;

    // WASM options
    wasmOptions?: WasmConversionOptions;

    // Server options
    serverOptions?: {
        imageType?: 'auto' | 'color' | 'monochrome';
        qualityMode?: 'fast' | 'standard' | 'high';
        colorPalette?: number;
        denoiseStrength?: string;
    };

    // Preprocessing
    preprocessing?: PreprocessingOptions;

    // AI mode (Phase 7)
    aiMode?: 'auto' | 'speed' | 'balanced' | 'quality' | 'max_quality';

    // Callbacks
    onProgress?: (progress: number, stage: string, route: ProcessingRoute) => void;
    onRouteDecision?: (route: ProcessingRoute, reason: string) => void;
}

export interface HybridConversionResult {
    svgContent?: string;
    svgBlob?: Blob;
    svgUrl?: string;
    route: ProcessingRoute;
    routingReason: string;
    conversionTime: number;
    totalTime: number;
    metadata: {
        imageSize: { width: number; height: number };
        megapixels: number;
        wasmCapabilities: WasmCapabilities;
        preprocessingSteps?: string[];
        serverJobId?: string;
        fileSize: number;
    };
}

interface ImageAnalysis {
    width: number;
    height: number;
    megapixels: number;
    fileSize: number;
    format: string;
    isAnimated: boolean;
}

/**
 * Analyze an image file for routing decisions.
 */
async function analyzeImage(file: File): Promise<ImageAnalysis> {
    const bitmap = await createImageBitmap(file);
    const result: ImageAnalysis = {
        width: bitmap.width,
        height: bitmap.height,
        megapixels: (bitmap.width * bitmap.height) / 1_000_000,
        fileSize: file.size,
        format: file.type,
        isAnimated: file.type === 'image/gif' || file.type === 'image/webp',
    };
    bitmap.close();
    return result;
}

/**
 * Determine the optimal processing route.
 */
function decideRoute(
    analysis: ImageAnalysis,
    capabilities: WasmCapabilities,
    options: HybridConversionOptions
): { route: ProcessingRoute; reason: string } {
    // Forced route
    if (options.forceRoute) {
        return {
            route: options.forceRoute,
            reason: `Forced to ${options.forceRoute} by user preference`,
        };
    }

    // AI mode always goes to server
    if (options.aiMode && options.aiMode !== 'speed') {
        return {
            route: 'server',
            reason: `AI mode "${options.aiMode}" requires server-side processing`,
        };
    }

    // No WASM → server
    if (!capabilities.available) {
        return {
            route: 'server',
            reason: 'WebAssembly not supported in this browser',
        };
    }

    // Animated images → server
    if (analysis.isAnimated) {
        return {
            route: 'server',
            reason: 'Animated images require server-side processing',
        };
    }

    // Size-based routing
    if (analysis.megapixels <= 1) {
        return {
            route: 'wasm',
            reason: `Small image (${analysis.megapixels.toFixed(2)}MP) — WASM is fastest`,
        };
    }

    if (analysis.megapixels <= 5) {
        // Medium images: check SIMD & preferred route
        if (capabilities.simdSupported) {
            return {
                route: options.preferredRoute === 'server' ? 'server' : 'wasm',
                reason: `Medium image (${analysis.megapixels.toFixed(1)}MP) with SIMD — WASM viable`,
            };
        }
        return {
            route: 'server',
            reason: `Medium image (${analysis.megapixels.toFixed(1)}MP) without SIMD — server recommended`,
        };
    }

    // Large images → server
    return {
        route: 'server',
        reason: `Large image (${analysis.megapixels.toFixed(1)}MP) — server required for performance`,
    };
}

/**
 * HybridProcessor — Main class for Phase 8 hybrid processing.
 *
 * Usage:
 * ```ts
 * const processor = new HybridProcessor();
 * const result = await processor.convert(file, options);
 * ```
 */
export class HybridProcessor {
    private wasmEngine: WasmVectorEngine;
    private preprocessor: ClientPreprocessor;
    private capabilities: WasmCapabilities;

    constructor() {
        this.wasmEngine = getWasmEngine();
        this.preprocessor = getClientPreprocessor();
        this.capabilities = getWasmCapabilities();
    }

    /**
     * Convert an image file to SVG using the optimal route.
     */
    async convert(
        file: File,
        options: HybridConversionOptions = {}
    ): Promise<HybridConversionResult> {
        const totalStart = performance.now();
        const onProgress = options.onProgress;

        onProgress?.(0, 'analyzing', 'wasm');

        // Analyze the image
        const analysis = await analyzeImage(file);

        // Decide route
        const { route, reason } = decideRoute(analysis, this.capabilities, options);

        // Notify route decision
        options.onRouteDecision?.(route, reason);

        onProgress?.(5, 'route_decided', route);

        let result: HybridConversionResult;

        if (route === 'wasm') {
            result = await this._convertWasm(file, analysis, options, onProgress);
        } else if (route === 'hybrid') {
            result = await this._convertHybrid(file, analysis, options, onProgress);
        } else {
            result = await this._convertServer(file, analysis, options, onProgress);
        }

        result.totalTime = (performance.now() - totalStart) / 1000;
        result.route = route;
        result.routingReason = reason;
        result.metadata.wasmCapabilities = this.capabilities;
        result.metadata.megapixels = analysis.megapixels;
        result.metadata.fileSize = file.size;

        return result;
    }

    /**
     * WASM-only conversion (client-side).
     */
    private async _convertWasm(
        file: File,
        analysis: ImageAnalysis,
        options: HybridConversionOptions,
        onProgress?: HybridConversionOptions['onProgress']
    ): Promise<HybridConversionResult> {
        onProgress?.(10, 'preprocessing', 'wasm');

        let processedFile: File | Blob = file;
        let preprocessingSteps: string[] = [];

        // Client-side preprocessing
        if (options.preprocessing) {
            const ppResult = await this.preprocessor.processImage(file, options.preprocessing);
            const blob = await this.preprocessor.toBlob(ppResult.imageData);
            processedFile = blob;
            preprocessingSteps = ppResult.stepsApplied;
        }

        onProgress?.(30, 'converting', 'wasm');

        try {
            const wasmResult = await this.wasmEngine.convertFileToSvg(
                processedFile,
                options.wasmOptions || {},
                (progress, stage) => {
                    onProgress?.(30 + progress * 0.7, stage, 'wasm');
                }
            );

            onProgress?.(100, 'complete', 'wasm');

            return {
                svgContent: wasmResult.svgContent,
                svgBlob: this.wasmEngine.svgToBlob(wasmResult.svgContent),
                svgUrl: this.wasmEngine.svgToDataUrl(wasmResult.svgContent),
                route: 'wasm',
                routingReason: '',
                conversionTime: wasmResult.conversionTime,
                totalTime: 0,
                metadata: {
                    imageSize: wasmResult.imageSize,
                    megapixels: 0,
                    wasmCapabilities: this.capabilities,
                    preprocessingSteps,
                    fileSize: file.size,
                },
            };
        } catch (error) {
            // Fallback to server
            console.warn('WASM conversion failed, falling back to server:', error);
            onProgress?.(40, 'fallback_to_server', 'server');
            return this._convertServer(file, analysis, options, onProgress);
        }
    }

    /**
     * Server-side conversion via API.
     */
    private async _convertServer(
        file: File,
        analysis: ImageAnalysis,
        options: HybridConversionOptions,
        onProgress?: HybridConversionOptions['onProgress']
    ): Promise<HybridConversionResult> {
        onProgress?.(10, 'uploading', 'server');

        const conversionStart = performance.now();

        // Upload file
        const uploadResult = await apiClient.upload(file, (progress) => {
            onProgress?.(10 + progress * 0.3, 'uploading', 'server');
        });

        onProgress?.(40, 'converting', 'server');

        // Start conversion
        const serverOpts = options.serverOptions || {};
        const conversionResult = await apiClient.convert(uploadResult.file_id, {
            image_type: serverOpts.imageType || 'auto',
            quality_mode: serverOpts.qualityMode || 'standard',
            color_palette: serverOpts.colorPalette,
            denoise_strength: serverOpts.denoiseStrength,
        });

        onProgress?.(50, 'processing', 'server');

        // Poll for completion
        return new Promise<HybridConversionResult>((resolve, reject) => {
            const pollInterval = setInterval(async () => {
                try {
                    const status = await apiClient.getStatus(conversionResult.job_id);

                    if (status.status === 'completed') {
                        clearInterval(pollInterval);
                        onProgress?.(90, 'downloading', 'server');

                        // Download result
                        const blob = await apiClient.downloadResult(conversionResult.job_id);
                        const svgContent = await blob.text();
                        const svgUrl = URL.createObjectURL(blob);

                        onProgress?.(100, 'complete', 'server');

                        resolve({
                            svgContent,
                            svgBlob: blob,
                            svgUrl,
                            route: 'server',
                            routingReason: '',
                            conversionTime: (performance.now() - conversionStart) / 1000,
                            totalTime: 0,
                            metadata: {
                                imageSize: { width: analysis.width, height: analysis.height },
                                megapixels: analysis.megapixels,
                                wasmCapabilities: getWasmCapabilities(),
                                serverJobId: conversionResult.job_id,
                                fileSize: file.size,
                            },
                        });
                    } else if (status.status === 'failed') {
                        clearInterval(pollInterval);
                        reject(new Error(status.error || 'Server conversion failed'));
                    } else {
                        onProgress?.(
                            50 + (status.progress || 0) * 0.4,
                            'processing',
                            'server'
                        );
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    reject(error);
                }
            }, 1000);

            // Timeout after 5 minutes
            setTimeout(() => {
                clearInterval(pollInterval);
                reject(new Error('Server conversion timed out (5min)'));
            }, 300_000);
        });
    }

    /**
     * Hybrid conversion: preprocess client-side, convert server-side.
     */
    private async _convertHybrid(
        file: File,
        analysis: ImageAnalysis,
        options: HybridConversionOptions,
        onProgress?: HybridConversionOptions['onProgress']
    ): Promise<HybridConversionResult> {
        onProgress?.(5, 'client_preprocessing', 'hybrid');

        // Step 1: Client-side preprocessing
        let processedBlob: Blob = file;
        let preprocessingSteps: string[] = [];

        if (options.preprocessing) {
            const ppResult = await this.preprocessor.processImage(file, options.preprocessing);
            processedBlob = await this.preprocessor.toBlob(ppResult.imageData);
            preprocessingSteps = ppResult.stepsApplied;
            onProgress?.(20, 'preprocessing_done', 'hybrid');
        }

        // Step 2: Upload preprocessed image to server for conversion
        const processedFile = new File(
            [processedBlob],
            file.name.replace(/\.[^.]+$/, '_preprocessed.png'),
            { type: 'image/png' }
        );

        onProgress?.(25, 'uploading_preprocessed', 'hybrid');

        const serverResult = await this._convertServer(
            processedFile,
            analysis,
            options,
            (p, s, r) => onProgress?.(25 + p * 0.75, s, 'hybrid')
        );

        serverResult.metadata.preprocessingSteps = preprocessingSteps;
        return serverResult;
    }

    /**
     * Get current processing capabilities.
     */
    getCapabilities(): {
        wasm: WasmCapabilities;
        clientPreprocessing: boolean;
        hybridMode: boolean;
        maxWasmMegapixels: number;
        maxServerMegapixels: number;
    } {
        return {
            wasm: this.capabilities,
            clientPreprocessing: true,
            hybridMode: true,
            maxWasmMegapixels: this.capabilities.simdSupported ? 5 : 1,
            maxServerMegapixels: 50,
        };
    }

    /**
     * Destroy the processor and free resources.
     */
    destroy(): void {
        this.wasmEngine.destroy();
    }
}

// Singleton
let _processor: HybridProcessor | null = null;

export function getHybridProcessor(): HybridProcessor {
    if (!_processor) {
        _processor = new HybridProcessor();
    }
    return _processor;
}

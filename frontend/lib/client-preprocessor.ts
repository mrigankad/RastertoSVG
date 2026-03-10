/**
 * Client-side Image Preprocessing using Canvas API.
 *
 * Phase 8: Performs preprocessing entirely in the browser:
 * - Noise reduction (bilateral-like filter via convolution)
 * - Contrast enhancement (histogram equalization)
 * - Color quantization (k-means in browser)
 * - Edge enhancement (unsharp mask)
 * - Grayscale conversion
 * - Image resizing with quality interpolation
 *
 * No server round-trip needed for basic enhancements.
 */

export interface PreprocessingOptions {
    denoise?: boolean;
    denoiseStrength?: number;       // 1–10
    contrast?: boolean;
    contrastAmount?: number;        // 0.5–2.0
    sharpen?: boolean;
    sharpenAmount?: number;         // 0.5–3.0
    colorReduce?: boolean;
    maxColors?: number;             // 2–256
    grayscale?: boolean;
    resize?: boolean;
    maxDimension?: number;          // pixels
    brightness?: number;            // -100 to 100
    saturation?: number;            // 0.0 to 3.0
    threshold?: boolean;
    thresholdValue?: number;        // 0–255
    invert?: boolean;
}

export interface PreprocessingResult {
    imageData: ImageData;
    processingTime: number;
    stepsApplied: string[];
    originalSize: { width: number; height: number };
    processedSize: { width: number; height: number };
}

/**
 * Client-side image preprocessor using Canvas API.
 */
export class ClientPreprocessor {
    /**
     * Apply preprocessing pipeline to an image.
     */
    async processImage(
        source: File | Blob | HTMLImageElement | ImageBitmap,
        options: PreprocessingOptions
    ): Promise<PreprocessingResult> {
        const startTime = performance.now();
        const stepsApplied: string[] = [];

        // Load image 
        let imageBitmap: ImageBitmap;
        if (source instanceof ImageBitmap) {
            imageBitmap = source;
        } else if (source instanceof HTMLImageElement) {
            imageBitmap = await createImageBitmap(source);
        } else {
            imageBitmap = await createImageBitmap(source);
        }

        let { width, height } = imageBitmap;
        const originalSize = { width, height };

        // Step 0: Resize if needed (do first to reduce work)
        if (options.resize && options.maxDimension) {
            const maxDim = options.maxDimension;
            if (width > maxDim || height > maxDim) {
                const scale = maxDim / Math.max(width, height);
                width = Math.round(width * scale);
                height = Math.round(height * scale);
                stepsApplied.push(`resize_${width}x${height}`);
            }
        }

        // Render to canvas
        const canvas = new OffscreenCanvas(width, height);
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(imageBitmap, 0, 0, width, height);
        let imageData = ctx.getImageData(0, 0, width, height);

        // Step 1: Grayscale
        if (options.grayscale) {
            imageData = this.toGrayscale(imageData);
            stepsApplied.push('grayscale');
        }

        // Step 2: Brightness adjustment
        if (options.brightness && options.brightness !== 0) {
            imageData = this.adjustBrightness(imageData, options.brightness);
            stepsApplied.push(`brightness_${options.brightness}`);
        }

        // Step 3: Contrast enhancement
        if (options.contrast) {
            const amount = options.contrastAmount ?? 1.5;
            imageData = this.enhanceContrast(imageData, amount);
            stepsApplied.push(`contrast_${amount.toFixed(1)}`);
        }

        // Step 4: Saturation
        if (options.saturation !== undefined && options.saturation !== 1.0) {
            imageData = this.adjustSaturation(imageData, options.saturation);
            stepsApplied.push(`saturation_${options.saturation.toFixed(1)}`);
        }

        // Step 5: Noise reduction
        if (options.denoise) {
            const strength = options.denoiseStrength ?? 5;
            imageData = this.denoise(imageData, strength);
            stepsApplied.push(`denoise_${strength}`);
        }

        // Step 6: Sharpening
        if (options.sharpen) {
            const amount = options.sharpenAmount ?? 1.5;
            imageData = this.sharpen(imageData, amount);
            stepsApplied.push(`sharpen_${amount.toFixed(1)}`);
        }

        // Step 7: Color reduction
        if (options.colorReduce) {
            const maxColors = options.maxColors ?? 32;
            imageData = this.reduceColors(imageData, maxColors);
            stepsApplied.push(`color_reduce_${maxColors}`);
        }

        // Step 8: Threshold (binary)
        if (options.threshold) {
            const value = options.thresholdValue ?? 128;
            imageData = this.applyThreshold(imageData, value);
            stepsApplied.push(`threshold_${value}`);
        }

        // Step 9: Invert
        if (options.invert) {
            imageData = this.invert(imageData);
            stepsApplied.push('invert');
        }

        // Clean up
        if (!(source instanceof ImageBitmap)) {
            imageBitmap.close();
        }

        return {
            imageData,
            processingTime: (performance.now() - startTime) / 1000,
            stepsApplied,
            originalSize,
            processedSize: { width: imageData.width, height: imageData.height },
        };
    }

    /**
     * Convert to grayscale.
     */
    toGrayscale(imageData: ImageData): ImageData {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            // ITU-R BT.601 luma weights
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            data[i] = gray;
            data[i + 1] = gray;
            data[i + 2] = gray;
        }
        return imageData;
    }

    /**
     * Adjust brightness.
     */
    adjustBrightness(imageData: ImageData, amount: number): ImageData {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.max(0, Math.min(255, data[i] + amount));
            data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + amount));
            data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + amount));
        }
        return imageData;
    }

    /**
     * Enhance contrast using histogram stretching.
     */
    enhanceContrast(imageData: ImageData, amount: number): ImageData {
        const data = imageData.data;
        const factor = (259 * (amount * 128 + 255)) / (255 * (259 - amount * 128));

        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.max(0, Math.min(255, factor * (data[i] - 128) + 128));
            data[i + 1] = Math.max(0, Math.min(255, factor * (data[i + 1] - 128) + 128));
            data[i + 2] = Math.max(0, Math.min(255, factor * (data[i + 2] - 128) + 128));
        }
        return imageData;
    }

    /**
     * Adjust saturation.
     */
    adjustSaturation(imageData: ImageData, amount: number): ImageData {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            data[i] = Math.max(0, Math.min(255, gray + amount * (data[i] - gray)));
            data[i + 1] = Math.max(0, Math.min(255, gray + amount * (data[i + 1] - gray)));
            data[i + 2] = Math.max(0, Math.min(255, gray + amount * (data[i + 2] - gray)));
        }
        return imageData;
    }

    /**
     * Denoise using box blur (approximation of bilateral filter).
     */
    denoise(imageData: ImageData, strength: number): ImageData {
        const { width, height, data } = imageData;
        const radius = Math.max(1, Math.min(5, Math.ceil(strength / 2)));
        const output = new Uint8ClampedArray(data);

        for (let y = radius; y < height - radius; y++) {
            for (let x = radius; x < width - radius; x++) {
                let rSum = 0, gSum = 0, bSum = 0, count = 0;
                const centerIdx = (y * width + x) * 4;
                const cr = data[centerIdx];
                const cg = data[centerIdx + 1];
                const cb = data[centerIdx + 2];

                for (let dy = -radius; dy <= radius; dy++) {
                    for (let dx = -radius; dx <= radius; dx++) {
                        const idx = ((y + dy) * width + (x + dx)) * 4;
                        const dr = Math.abs(data[idx] - cr);
                        const dg = Math.abs(data[idx + 1] - cg);
                        const db = Math.abs(data[idx + 2] - cb);

                        // Bilateral-like: only include similar pixels
                        const colorDist = dr + dg + db;
                        if (colorDist < strength * 30) {
                            rSum += data[idx];
                            gSum += data[idx + 1];
                            bSum += data[idx + 2];
                            count++;
                        }
                    }
                }

                if (count > 0) {
                    output[centerIdx] = rSum / count;
                    output[centerIdx + 1] = gSum / count;
                    output[centerIdx + 2] = bSum / count;
                }
            }
        }

        return new ImageData(output, width, height);
    }

    /**
     * Sharpen using unsharp mask.
     */
    sharpen(imageData: ImageData, amount: number): ImageData {
        const { width, height, data } = imageData;
        const output = new Uint8ClampedArray(data);

        // 3x3 blur kernel
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                for (let c = 0; c < 3; c++) {
                    const idx = (y * width + x) * 4 + c;

                    // Box blur (3x3)
                    let blur =
                        data[((y - 1) * width + (x - 1)) * 4 + c] +
                        data[((y - 1) * width + x) * 4 + c] +
                        data[((y - 1) * width + (x + 1)) * 4 + c] +
                        data[(y * width + (x - 1)) * 4 + c] +
                        data[(y * width + x) * 4 + c] +
                        data[(y * width + (x + 1)) * 4 + c] +
                        data[((y + 1) * width + (x - 1)) * 4 + c] +
                        data[((y + 1) * width + x) * 4 + c] +
                        data[((y + 1) * width + (x + 1)) * 4 + c];
                    blur /= 9;

                    // Unsharp mask: original + amount * (original - blur)
                    const sharp = data[idx] + amount * (data[idx] - blur);
                    output[idx] = Math.max(0, Math.min(255, sharp));
                }
            }
        }

        return new ImageData(output, width, height);
    }

    /**
     * Reduce colors using median-cut quantization.
     */
    reduceColors(imageData: ImageData, maxColors: number): ImageData {
        const { width, height, data } = imageData;

        // Sample pixels
        const pixels: [number, number, number][] = [];
        const step = Math.max(1, Math.floor(data.length / 4 / 10000));
        for (let i = 0; i < data.length; i += 4 * step) {
            pixels.push([data[i], data[i + 1], data[i + 2]]);
        }

        // Simple median-cut
        const palette = this._medianCut(pixels, maxColors);

        // Remap all pixels to nearest palette color
        const output = new Uint8ClampedArray(data);
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            let bestDist = Infinity;
            let bestColor = palette[0];

            for (const color of palette) {
                const dist =
                    (r - color[0]) ** 2 +
                    (g - color[1]) ** 2 +
                    (b - color[2]) ** 2;
                if (dist < bestDist) {
                    bestDist = dist;
                    bestColor = color;
                }
            }

            output[i] = bestColor[0];
            output[i + 1] = bestColor[1];
            output[i + 2] = bestColor[2];
        }

        return new ImageData(output, width, height);
    }

    /**
     * Apply binary threshold.
     */
    applyThreshold(imageData: ImageData, value: number): ImageData {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            const val = gray >= value ? 255 : 0;
            data[i] = val;
            data[i + 1] = val;
            data[i + 2] = val;
        }
        return imageData;
    }

    /**
     * Invert colors.
     */
    invert(imageData: ImageData): ImageData {
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 255 - data[i];
            data[i + 1] = 255 - data[i + 1];
            data[i + 2] = 255 - data[i + 2];
        }
        return imageData;
    }

    /**
     * Get a preview canvas for processed image data.
     */
    toCanvas(imageData: ImageData): OffscreenCanvas {
        const canvas = new OffscreenCanvas(imageData.width, imageData.height);
        const ctx = canvas.getContext('2d')!;
        ctx.putImageData(imageData, 0, 0);
        return canvas;
    }

    /**
     * Convert processed ImageData to a Blob.
     */
    async toBlob(imageData: ImageData, type = 'image/png'): Promise<Blob> {
        const canvas = this.toCanvas(imageData);
        return await canvas.convertToBlob({ type: type as any });
    }

    /**
     * Median-cut color quantization.
     */
    private _medianCut(
        pixels: [number, number, number][],
        maxColors: number
    ): [number, number, number][] {
        if (pixels.length === 0) return [[0, 0, 0]];

        let buckets: [number, number, number][][] = [pixels];

        while (buckets.length < maxColors) {
            // Find the bucket with the largest color range
            let maxRange = 0;
            let maxBucketIdx = 0;

            for (let i = 0; i < buckets.length; i++) {
                const bucket = buckets[i];
                if (bucket.length < 2) continue;

                for (let ch = 0; ch < 3; ch++) {
                    const values = bucket.map(p => p[ch]);
                    const range = Math.max(...values) - Math.min(...values);
                    if (range > maxRange) {
                        maxRange = range;
                        maxBucketIdx = i;
                    }
                }
            }

            if (maxRange === 0) break;

            const bucket = buckets[maxBucketIdx];

            // Find the channel with the largest range
            let splitChannel = 0;
            let bestRange = 0;
            for (let ch = 0; ch < 3; ch++) {
                const values = bucket.map(p => p[ch]);
                const range = Math.max(...values) - Math.min(...values);
                if (range > bestRange) {
                    bestRange = range;
                    splitChannel = ch;
                }
            }

            // Sort by that channel and split
            bucket.sort((a, b) => a[splitChannel] - b[splitChannel]);
            const mid = Math.floor(bucket.length / 2);

            buckets.splice(maxBucketIdx, 1, bucket.slice(0, mid), bucket.slice(mid));
        }

        // Average each bucket to get palette colors
        return buckets.map(bucket => {
            const r = Math.round(bucket.reduce((s, p) => s + p[0], 0) / bucket.length);
            const g = Math.round(bucket.reduce((s, p) => s + p[1], 0) / bucket.length);
            const b = Math.round(bucket.reduce((s, p) => s + p[2], 0) / bucket.length);
            return [r, g, b] as [number, number, number];
        });
    }
}

// Singleton instance
let _preprocessor: ClientPreprocessor | null = null;

export function getClientPreprocessor(): ClientPreprocessor {
    if (!_preprocessor) {
        _preprocessor = new ClientPreprocessor();
    }
    return _preprocessor;
}

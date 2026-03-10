'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { WifiOff, Zap, Upload, ArrowLeft } from 'lucide-react';

export default function OfflinePage() {
    const [wasmAvailable, setWasmAvailable] = useState(false);

    useEffect(() => {
        try {
            setWasmAvailable(typeof WebAssembly === 'object');
        } catch {
            setWasmAvailable(false);
        }
    }, []);

    return (
        <main className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 text-white flex flex-col items-center justify-center px-4">
            <div className="max-w-lg text-center">
                {/* Icon */}
                <div className="w-24 h-24 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-8 ring-4 ring-slate-600/30">
                    <WifiOff className="w-12 h-12 text-amber-400" />
                </div>

                {/* Title */}
                <h1 className="text-4xl font-bold mb-4">
                    You&apos;re Offline
                </h1>

                <p className="text-slate-300 text-lg mb-8">
                    No internet connection detected, but don&apos;t worry —
                    you can still convert images using our client-side WASM engine.
                </p>

                {/* WASM Status */}
                {wasmAvailable ? (
                    <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6 mb-8">
                        <div className="flex items-center justify-center gap-3 mb-3">
                            <Zap className="w-6 h-6 text-emerald-400" />
                            <h2 className="text-xl font-semibold text-emerald-300">
                                WASM Engine Available
                            </h2>
                        </div>
                        <p className="text-slate-300 text-sm">
                            Client-side conversion is active. Images under 5MP can be converted
                            entirely in your browser without any server connection.
                        </p>
                    </div>
                ) : (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 mb-8">
                        <h2 className="text-xl font-semibold text-red-300 mb-2">
                            WASM Not Available
                        </h2>
                        <p className="text-slate-300 text-sm">
                            Your browser doesn&apos;t support WebAssembly.
                            Please reconnect to the internet for server-side conversion.
                        </p>
                    </div>
                )}

                {/* Features available offline */}
                {wasmAvailable && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                        <div className="bg-slate-700/30 rounded-xl p-4 border border-slate-600/30">
                            <Upload className="w-6 h-6 text-blue-400 mb-2" />
                            <h3 className="font-semibold text-sm">Local Conversion</h3>
                            <p className="text-slate-400 text-xs mt-1">
                                Convert images using the WASM engine
                            </p>
                        </div>
                        <div className="bg-slate-700/30 rounded-xl p-4 border border-slate-600/30">
                            <Zap className="w-6 h-6 text-purple-400 mb-2" />
                            <h3 className="font-semibold text-sm">Client Preprocessing</h3>
                            <p className="text-slate-400 text-xs mt-1">
                                Denoise, sharpen, and adjust locally
                            </p>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <Link
                        href="/convert-new"
                        className="inline-flex items-center justify-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-all"
                    >
                        <Zap className="w-4 h-4 mr-2" />
                        Convert Offline
                    </Link>
                    <button
                        onClick={() => window.location.reload()}
                        className="inline-flex items-center justify-center px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-xl transition-all"
                    >
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Try Reconnecting
                    </button>
                </div>
            </div>
        </main>
    );
}

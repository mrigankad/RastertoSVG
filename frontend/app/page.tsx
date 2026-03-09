'use client';

import Link from 'next/link';
import { ArrowRight, Image, Zap, Gauge, Sparkles, FileType, Clock, Shield } from 'lucide-react';

export default function Home() {
  const features = [
    {
      icon: Zap,
      title: 'Fast Mode',
      description: 'Direct conversion with no preprocessing. Perfect for simple graphics and screenshots.',
      time: '< 1 second',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      icon: Gauge,
      title: 'Standard Mode',
      description: 'Balanced preprocessing for better quality. Ideal for most images and photographs.',
      time: '1-3 seconds',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      icon: Sparkles,
      title: 'High Mode',
      description: 'Advanced preprocessing with edge enhancement. Best for professional work.',
      time: '3-10 seconds',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
  ];

  const capabilities = [
    {
      icon: FileType,
      title: 'Multiple Formats',
      description: 'Supports PNG, JPG, BMP, TIFF, GIF, and WEBP',
    },
    {
      icon: Clock,
      title: 'Async Processing',
      description: 'Background conversion with real-time progress tracking',
    },
    {
      icon: Shield,
      title: 'Privacy First',
      description: 'Files are automatically deleted after 30 days',
    },
  ];

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Image className="w-8 h-8 text-blue-600" />
              <h1 className="text-xl font-bold text-gray-900">
                Raster to SVG
              </h1>
            </div>
            <nav className="hidden md:flex items-center space-x-6">
              <Link
                href="/convert-new"
                className="text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                Enhanced Convert
              </Link>
              <Link
                href="/convert"
                className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                Classic
              </Link>
              <Link
                href="/history"
                className="text-gray-600 hover:text-gray-900 font-medium transition-colors"
              >
                History
              </Link>
            </nav>
            <Link
              href="/convert"
              className="md:hidden p-2 text-gray-600 hover:text-gray-900"
            >
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24">
        <div className="text-center">
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-gray-900 mb-6">
            Convert Images to{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
              SVG
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-10">
            Transform your raster images into scalable vector graphics with our
            powerful conversion engine. Three quality modes to suit every need.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/convert-new"
              className="inline-flex items-center px-8 py-4 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all shadow-lg hover:shadow-xl"
            >
              Try Enhanced Mode
              <ArrowRight className="ml-2 w-5 h-5" />
            </Link>
            <Link
              href="/convert"
              className="inline-flex items-center px-8 py-4 bg-white text-gray-700 font-semibold rounded-xl border-2 border-gray-200 hover:border-gray-300 transition-all"
            >
              Classic Mode
            </Link>
          </div>
        </div>
      </section>

      {/* Quality Modes Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h3 className="text-3xl font-bold text-gray-900 mb-4">
            Three Quality Modes
          </h3>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Choose the right balance of speed and quality for your needs
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className={`${feature.bgColor} rounded-2xl p-6 border-2 border-transparent hover:border-opacity-50 transition-all`}
              >
                <div className={`w-12 h-12 ${feature.bgColor} rounded-xl flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${feature.color}`} />
                </div>
                <h4 className="text-lg font-bold text-gray-900 mb-2">
                  {feature.title}
                </h4>
                <p className="text-gray-600 mb-4">
                  {feature.description}
                </p>
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${feature.bgColor} ${feature.color}`}>
                  {feature.time}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      {/* Capabilities Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 md:p-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {capabilities.map((cap) => {
              const Icon = cap.icon;
              return (
                <div key={cap.title} className="text-center md:text-left">
                  <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto md:mx-0 mb-4">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-2">
                    {cap.title}
                  </h4>
                  <p className="text-gray-600">
                    {cap.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Supported Formats Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Supported Input Formats
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            {['PNG', 'JPG', 'JPEG', 'BMP', 'TIFF', 'GIF', 'WEBP'].map((format) => (
              <span
                key={format}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium"
              >
                {format}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Preprocessing Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 md:p-12 text-white">
          <div className="text-center">
            <h3 className="text-3xl font-bold mb-4">
              Advanced Preprocessing
            </h3>
            <p className="text-blue-100 max-w-2xl mx-auto mb-8">
              Our preprocessing pipeline includes noise reduction, color optimization,
              contrast enhancement, edge detection, and more.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                'Noise Reduction',
                'Color Reduction',
                'Contrast Enhancement',
                'Edge Sharpening',
              ].map((item) => (
                <div
                  key={item}
                  className="bg-white/10 backdrop-blur-sm rounded-lg p-4"
                >
                  <span className="text-sm font-medium">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h3 className="text-3xl font-bold text-gray-900 mb-4">
            Ready to convert your images?
          </h3>
          <p className="text-gray-600 mb-8">
            Get started in seconds with our free online converter
          </p>
          <Link
            href="/convert-new"
            className="inline-flex items-center px-8 py-4 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-all shadow-lg hover:shadow-xl"
          >
            Try Enhanced Mode
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <Image className="w-6 h-6 text-blue-600" />
              <span className="font-semibold text-gray-900">Raster to SVG</span>
            </div>
            <p className="text-gray-500 text-sm">
              Built with Next.js, FastAPI, and Celery
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}

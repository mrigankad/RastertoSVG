'use client';

import React from 'react';
import { 
  Zap, 
  SlidersHorizontal, 
  Settings2, 
  ChevronRight,
  Sparkles,
  Check
} from 'lucide-react';
import { useControlLevelStore, ControlLevel } from '@/lib/advanced-store';

interface ControlLevelOption {
  level: ControlLevel;
  name: string;
  description: string;
  icon: React.ElementType;
  features: string[];
  color: string;
  bgColor: string;
  borderColor: string;
}

const controlLevels: ControlLevelOption[] = [
  {
    level: 1,
    name: 'Simple',
    description: 'One-click conversion with smart defaults',
    icon: Zap,
    features: [
      'Quality presets only',
      'Automatic settings',
      'Fastest workflow',
    ],
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
  },
  {
    level: 2,
    name: 'Guided',
    description: 'Balance of control and convenience',
    icon: SlidersHorizontal,
    features: [
      'Quality mode selection',
      'Basic preprocessing options',
      'Color palette control',
    ],
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  {
    level: 3,
    name: 'Advanced',
    description: 'Full control over every parameter',
    icon: Settings2,
    features: [
      'Custom preprocessing pipeline',
      'Color palette editor',
      'Vectorization parameters',
      'Save custom presets',
    ],
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
  },
];

export function ControlLevelSelector() {
  const { level, setLevel } = useControlLevelStore();

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold text-gray-900">Control Level</h3>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Choose how much control you want over the conversion process
        </p>
      </div>

      <div className="p-4 space-y-3">
        {controlLevels.map((option) => {
          const Icon = option.icon;
          const isSelected = level === option.level;

          return (
            <button
              key={option.level}
              onClick={() => setLevel(option.level)}
              className={`
                w-full p-4 rounded-xl border-2 text-left transition-all duration-200
                ${isSelected
                  ? `${option.borderColor} ${option.bgColor} ring-2 ring-offset-1 ring-blue-500`
                  : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50'
                }
              `}
            >
              <div className="flex items-start space-x-3">
                <div
                  className={`
                    p-2 rounded-lg transition-colors
                    ${isSelected ? 'bg-white shadow-sm' : 'bg-gray-100'}
                  `}
                >
                  <Icon className={`w-5 h-5 ${isSelected ? option.color : 'text-gray-500'}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4
                      className={`font-semibold ${
                        isSelected ? option.color : 'text-gray-900'
                      }`}
                    >
                      {option.name}
                    </h4>
                    {isSelected && (
                      <Check className={`w-5 h-5 ${option.color}`} />
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {option.description}
                  </p>

                  <ul className="mt-3 space-y-1">
                    {option.features.map((feature, idx) => (
                      <li
                        key={idx}
                        className="text-xs text-gray-400 flex items-center"
                      >
                        <span className="w-1 h-1 bg-gray-300 rounded-full mr-2" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>

                <ChevronRight
                  className={`
                    w-5 h-5 transition-colors
                    ${isSelected ? option.color : 'text-gray-300'}
                  `}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

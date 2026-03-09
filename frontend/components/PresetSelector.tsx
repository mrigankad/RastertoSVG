'use client';

import React, { useEffect, useState } from 'react';
import { Bookmark, Plus, Search, Trash2, Edit2, Check, Sparkles, Image, FileText, Pencil, ScanLine } from 'lucide-react';
import { advancedApi, ConversionPreset } from '@/lib/advanced-api';
import { usePresetStore, useAdvancedConversionStore } from '@/lib/advanced-store';

const categoryIcons: Record<string, React.ElementType> = {
  'built_in': Sparkles,
  'user': Bookmark,
  'shared': Image,
};

const presetIcons: Record<string, React.ElementType> = {
  'logo-professional': Sparkles,
  'photo-standard': Image,
  'line-art': Pencil,
  'document-scan': ScanLine,
  'sketch-preserve': FileText,
};

export function PresetSelector() {
  const { presets, selectedPreset, setPresets, setSelectedPreset, setLoading, removePreset } = usePresetStore();
  const { applyPreset, selectedPresetId } = useAdvancedConversionStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Load presets on mount
  useEffect(() => {
    const loadPresets = async () => {
      setLoading(true);
      setIsLoading(true);
      try {
        const data = await advancedApi.getPresets();
        setPresets(data.presets);
      } catch (err) {
        console.error('Failed to load presets:', err);
      } finally {
        setLoading(false);
        setIsLoading(false);
      }
    };

    if (presets.length === 0) {
      loadPresets();
    }
  }, [presets.length, setPresets, setLoading]);

  const filteredPresets = presets.filter((preset) => {
    const query = searchQuery.toLowerCase();
    return (
      preset.name.toLowerCase().includes(query) ||
      preset.description.toLowerCase().includes(query) ||
      preset.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  });

  const builtInPresets = filteredPresets.filter((p) => p.category === 'built_in');
  const userPresets = filteredPresets.filter((p) => p.category === 'user');

  const handleSelectPreset = (preset: ConversionPreset) => {
    setSelectedPreset(preset);
    applyPreset(preset);
  };

  const handleDeletePreset = async (e: React.MouseEvent, preset: ConversionPreset) => {
    e.stopPropagation();
    if (preset.category === 'built_in') return;
    
    try {
      await advancedApi.deletePreset(preset.id);
      removePreset(preset.id);
      if (selectedPreset?.id === preset.id) {
        setSelectedPreset(null);
      }
    } catch (err) {
      console.error('Failed to delete preset:', err);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center space-x-2">
          <Bookmark className="w-5 h-5 text-blue-500" />
          <h3 className="font-semibold text-gray-900">Presets</h3>
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Quick-start with optimized settings for your image type
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search presets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Built-in Presets */}
        {builtInPresets.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Built-in
            </h4>
            <div className="space-y-2">
              {builtInPresets.map((preset) => (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  isSelected={selectedPresetId === preset.id}
                  onSelect={() => handleSelectPreset(preset)}
                  onDelete={(e) => handleDeletePreset(e, preset)}
                />
              ))}
            </div>
          </div>
        )}

        {/* User Presets */}
        {userPresets.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              My Presets
            </h4>
            <div className="space-y-2">
              {userPresets.map((preset) => (
                <PresetCard
                  key={preset.id}
                  preset={preset}
                  isSelected={selectedPresetId === preset.id}
                  onSelect={() => handleSelectPreset(preset)}
                  onDelete={(e) => handleDeletePreset(e, preset)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {filteredPresets.length === 0 && !isLoading && (
          <div className="text-center py-6">
            <Bookmark className="w-10 h-10 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No presets found</p>
          </div>
        )}

        {/* Create New */}
        <button className="w-full py-2 border-2 border-dashed border-gray-200 rounded-lg text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-center space-x-2">
          <Plus className="w-4 h-4" />
          <span>Save Current as Preset</span>
        </button>
      </div>
    </div>
  );
}

interface PresetCardProps {
  preset: ConversionPreset;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}

function PresetCard({ preset, isSelected, onSelect, onDelete }: PresetCardProps) {
  const Icon = presetIcons[preset.id] || categoryIcons[preset.category] || Bookmark;

  return (
    <button
      onClick={onSelect}
      className={`
        w-full p-3 rounded-lg border text-left transition-all group
        ${isSelected
          ? 'bg-blue-50 border-blue-500 ring-1 ring-blue-500'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
        }
      `}
    >
      <div className="flex items-start space-x-3">
        <div
          className={`
            p-2 rounded-lg
            ${isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'}
          `}
        >
          <Icon className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h5 className={`font-medium text-sm ${isSelected ? 'text-blue-900' : 'text-gray-900'}`}>
              {preset.name}
            </h5>
            {isSelected && <Check className="w-4 h-4 text-blue-500" />}
          </div>
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{preset.description}</p>
          
          {preset.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {preset.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className={`
                    px-1.5 py-0.5 text-[10px] rounded-full
                    ${isSelected ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}
                  `}
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center space-x-1">
          {preset.category !== 'built_in' && (
            <button
              onClick={onDelete}
              className="p-1 text-gray-400 hover:text-red-500 rounded"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </button>
  );
}

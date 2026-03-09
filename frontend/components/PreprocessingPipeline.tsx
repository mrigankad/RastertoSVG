'use client';

import React, { useEffect, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus,
  GripVertical,
  Trash2,
  ChevronDown,
  ChevronUp,
  Settings,
  Waves,
  Zap,
  Sun,
  Palette,
  Droplet,
  Hexagon,
  Eraser,
  RotateCcw,
  Power,
  Eye,
  EyeOff,
} from 'lucide-react';
import { advancedApi, FilterInfo, PreprocessingStep } from '@/lib/advanced-api';
import { useAdvancedConversionStore, useFilterRegistryStore } from '@/lib/advanced-store';

// Icon mapping
const filterIcons: Record<string, React.ElementType> = {
  denoise: Waves,
  sharpen: Zap,
  contrast: Sun,
  color_reduce: Palette,
  blur: Droplet,
  edge_enhance: Hexagon,
  despeckle: Eraser,
  deskew: RotateCcw,
};

interface SortableFilterCardProps {
  step: PreprocessingStep;
  filter: FilterInfo | undefined;
  onToggle: () => void;
  onRemove: () => void;
  onUpdate: (updates: Partial<PreprocessingStep>) => void;
}

function SortableFilterCard({ step, filter, onToggle, onRemove, onUpdate }: SortableFilterCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: step.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const Icon = filter ? filterIcons[filter.id] || Settings : Settings;

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        bg-white rounded-lg border transition-all
        ${step.enabled ? 'border-gray-200' : 'border-gray-100 bg-gray-50/50'}
        ${isDragging ? 'shadow-lg' : 'shadow-sm'}
      `}
    >
      <div className="p-3 flex items-center space-x-2">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="p-1 text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing"
        >
          <GripVertical className="w-4 h-4" />
        </button>

        {/* Toggle */}
        <button
          onClick={onToggle}
          className={`
            p-1.5 rounded transition-colors
            ${step.enabled ? 'text-green-500 hover:bg-green-50' : 'text-gray-300 hover:bg-gray-100'}
          `}
        >
          {step.enabled ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
        </button>

        {/* Icon */}
        <div
          className={`
            p-1.5 rounded transition-colors
            ${step.enabled ? 'bg-blue-50 text-blue-500' : 'bg-gray-100 text-gray-400'}
          `}
        >
          <Icon className="w-4 h-4" />
        </div>

        {/* Name */}
        <span
          className={`
            flex-1 font-medium text-sm
            ${step.enabled ? 'text-gray-900' : 'text-gray-400'}
          `}
        >
          {filter?.name || step.name}
        </span>

        {/* Expand */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 text-gray-400 hover:text-gray-600"
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Remove */}
        <button
          onClick={onRemove}
          className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Parameters */}
      {isExpanded && filter && (
        <div className="px-4 pb-4 border-t border-gray-100 pt-3">
          <FilterParamsForm
            filter={filter}
            params={step.params}
            onChange={(params) => onUpdate({ params })}
          />
        </div>
      )}
    </div>
  );
}

interface FilterParamsFormProps {
  filter: FilterInfo;
  params: Record<string, any>;
  onChange: (params: Record<string, any>) => void;
}

function FilterParamsForm({ filter, params, onChange }: FilterParamsFormProps) {
  const updateParam = (key: string, value: any) => {
    onChange({ ...params, [key]: value });
  };

  return (
    <div className="space-y-3">
      {Object.entries(filter.param_schema).map(([key, schema]: [string, any]) => {
        const value = params[key] ?? filter.default_params[key];

        if (schema.enum) {
          return (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-600 mb-1.5 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              <div className="flex flex-wrap gap-2">
                {schema.enum.map((option: string) => (
                  <button
                    key={option}
                    onClick={() => updateParam(key, option)}
                    className={`
                      px-3 py-1.5 text-xs rounded-lg border transition-all
                      ${value === option
                        ? 'bg-blue-50 border-blue-500 text-blue-700 font-medium'
                        : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                      }
                    `}
                  >
                    {option.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          );
        }

        if (schema.type === 'number') {
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-gray-600 capitalize">
                  {key.replace(/_/g, ' ')}
                </label>
                <span className="text-xs text-gray-400">{Number(value).toFixed(1)}</span>
              </div>
              <input
                type="range"
                min={schema.minimum}
                max={schema.maximum}
                step={schema.maximum > 10 ? 1 : 0.1}
                value={value}
                onChange={(e) => updateParam(key, parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
            </div>
          );
        }

        if (schema.type === 'boolean') {
          return (
            <div key={key} className="flex items-center justify-between">
              <label className="text-xs font-medium text-gray-600 capitalize">
                {key.replace(/_/g, ' ')}
              </label>
              <button
                onClick={() => updateParam(key, !value)}
                className={`
                  relative inline-flex h-5 w-9 items-center rounded-full transition-colors
                  ${value ? 'bg-blue-500' : 'bg-gray-200'}
                `}
              >
                <span
                  className={`
                    inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform
                    ${value ? 'translate-x-5' : 'translate-x-1'}
                  `}
                />
              </button>
            </div>
          );
        }

        return null;
      })}
    </div>
  );
}

export function PreprocessingPipelineBuilder() {
  const { preprocessing, setPreprocessing, addPreprocessingStep, updatePreprocessingStep, removePreprocessingStep, togglePreprocessingStep } = useAdvancedConversionStore();
  const { filters, setFilters, setLoading, setError } = useFilterRegistryStore();
  const [showAddMenu, setShowAddMenu] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Load filters on mount
  useEffect(() => {
    const loadFilters = async () => {
      setLoading(true);
      try {
        const data = await advancedApi.getFilters();
        setFilters(data.filters, data.categories);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load filters');
      } finally {
        setLoading(false);
      }
    };

    if (filters.length === 0) {
      loadFilters();
    }
  }, [filters.length, setFilters, setLoading, setError]);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = preprocessing.steps.findIndex((s) => s.id === active.id);
      const newIndex = preprocessing.steps.findIndex((s) => s.id === over.id);
      
      const newSteps = arrayMove(preprocessing.steps, oldIndex, newIndex);
      
      // Update order numbers
      newSteps.forEach((step, index) => {
        step.order = index;
      });
      
      setPreprocessing({ steps: newSteps });
    }
  };

  const handleAddFilter = (filter: FilterInfo) => {
    const newStep: PreprocessingStep = {
      id: `step-${Date.now()}`,
      name: filter.id,
      enabled: true,
      order: preprocessing.steps.length,
      params: { ...filter.default_params },
    };

    addPreprocessingStep(newStep);
    setShowAddMenu(false);
  };

  const handleClearAll = () => {
    setPreprocessing({ steps: [] });
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5 text-gray-500" />
            <h3 className="font-semibold text-gray-900">Preprocessing Pipeline</h3>
          </div>
          {preprocessing.steps.length > 0 && (
            <button
              onClick={handleClearAll}
              className="text-xs text-red-600 hover:text-red-700 font-medium"
            >
              Clear All
            </button>
          )}
        </div>
        <p className="text-sm text-gray-500 mt-1">
          Drag and drop filters to build your preprocessing chain
        </p>
      </div>

      <div className="p-4">
        {preprocessing.steps.length === 0 ? (
          <div className="text-center py-8 border-2 border-dashed border-gray-200 rounded-xl">
            <Settings className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No filters added yet</p>
            <button
              onClick={() => setShowAddMenu(!showAddMenu)}
              className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Add your first filter
            </button>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={preprocessing.steps.map((s) => s.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {preprocessing.steps.map((step) => (
                  <SortableFilterCard
                    key={step.id}
                    step={step}
                    filter={filters.find((f) => f.id === step.name)}
                    onToggle={() => togglePreprocessingStep(step.id)}
                    onRemove={() => removePreprocessingStep(step.id)}
                    onUpdate={(updates) => updatePreprocessingStep(step.id, updates)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}

        {/* Add Filter Button */}
        <div className="relative mt-3">
          <button
            onClick={() => setShowAddMenu(!showAddMenu)}
            className="w-full py-2.5 border-2 border-dashed border-gray-200 rounded-lg text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Add Filter</span>
          </button>

          {/* Add Menu */}
          {showAddMenu && (
            <div className="absolute z-10 left-0 right-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-xl max-h-64 overflow-y-auto">
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => handleAddFilter(filter)}
                  className="w-full px-4 py-3 flex items-center space-x-3 hover:bg-gray-50 text-left border-b border-gray-100 last:border-0"
                >
                  {(() => {
                    const Icon = filterIcons[filter.id] || Settings;
                    return <Icon className="w-4 h-4 text-gray-400" />;
                  })()}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{filter.name}</p>
                    <p className="text-xs text-gray-500 truncate">{filter.description}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

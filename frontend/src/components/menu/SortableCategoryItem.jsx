import { Edit2, Trash2, GripVertical, Eye, EyeOff, LayoutGrid, List } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableCategoryItem({ category, isSelected, itemCount, sectionName, onSelect, onEdit, onDelete, onToggleActive, onToggleDisplay }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: category.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : (category.is_active !== false ? 1 : 0.5),
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex flex-col gap-1 p-2.5 rounded-xl cursor-pointer transition-all ${
        isSelected 
          ? 'bg-mint-500 text-white shadow-md' 
          : 'hover:bg-accent'
      } ${isDragging ? 'shadow-lg' : ''}`}
      onClick={() => onSelect(category.id)}
      data-testid={`category-${category.id}`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <button
          className={`cursor-grab active:cursor-grabbing p-1 rounded hover:bg-black/10 flex-shrink-0 ${isSelected ? 'hover:bg-white/20' : ''}`}
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <span className="font-medium block text-sm leading-tight" title={category.name}>{category.name}</span>
          {sectionName && (
            <span className={`text-xs ${isSelected ? 'text-white/70' : 'text-muted-foreground'}`}>{sectionName}</span>
          )}
        </div>
        <div className="flex items-center gap-0.5 flex-shrink-0 ml-1">
          <span className={`text-xs w-5 text-center ${isSelected ? 'text-white/80' : 'text-muted-foreground'}`}>
            {itemCount}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className={`h-6 w-6 ${isSelected ? 'hover:bg-white/20' : ''}`}
            onClick={(e) => { e.stopPropagation(); onEdit(category); }}
          >
            <Edit2 className="w-3 h-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={`h-6 w-6 ${isSelected ? 'hover:bg-white/20' : 'hover:text-destructive'}`}
            onClick={(e) => { e.stopPropagation(); onDelete(category); }}
          >
            <Trash2 className="w-3 h-3" />
          </Button>
        </div>
      </div>
      {/* Quick controls row */}
      <div className="flex items-center gap-1.5 pl-8" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onToggleActive(category)}
          className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
            category.is_active !== false
              ? (isSelected ? 'bg-white/20 text-white' : 'bg-green-500/10 text-green-600')
              : (isSelected ? 'bg-white/10 text-white/50' : 'bg-red-500/10 text-red-500')
          }`}
          title={category.is_active !== false ? 'Категория видна в меню' : 'Категория скрыта'}
          data-testid={`category-active-toggle-${category.id}`}
        >
          {category.is_active !== false ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
          {category.is_active !== false ? 'Видна' : 'Скрыта'}
        </button>
        <button
          onClick={() => onToggleDisplay(category)}
          className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors ${
            isSelected ? 'bg-white/20 text-white' : 'bg-muted text-muted-foreground hover:bg-accent'
          }`}
          title={category.display_mode === 'card' ? 'Режим: Карточки' : 'Режим: Список'}
          data-testid={`category-display-toggle-${category.id}`}
        >
          {category.display_mode === 'card' ? <LayoutGrid className="w-3 h-3" /> : <List className="w-3 h-3" />}
          {category.display_mode === 'card' ? 'Карточки' : 'Список'}
        </button>
      </div>
    </div>
  );
}

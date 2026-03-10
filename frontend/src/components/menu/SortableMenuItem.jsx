import { GripVertical, ImageIcon, Edit2, Trash2, Image } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

export function SortableMenuItem({ item, onEdit, onDelete, onToggleAvailability, currency }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Banner item
  if (item.is_banner) {
    return (
      <Card 
        ref={setNodeRef}
        style={style}
        className={`border-none shadow-md transition-all ${!item.is_available ? 'opacity-60' : ''} ${isDragging ? 'shadow-xl z-50' : ''}`}
        data-testid={`banner-${item.id}`}
      >
        <CardContent className="p-4">
          <div className="flex gap-4">
            <button
              className="cursor-grab active:cursor-grabbing p-1 self-start text-muted-foreground hover:text-foreground"
              {...attributes}
              {...listeners}
            >
              <GripVertical className="w-5 h-5" />
            </button>

            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <Badge className="bg-purple-500 text-white">
                  <Image className="w-3 h-3 mr-1" />
                  Баннер
                </Badge>
                <div className="flex items-center gap-1">
                  <Switch
                    checked={item.is_available}
                    onCheckedChange={() => onToggleAvailability(item)}
                  />
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(item)}>
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => onDelete(item)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {item.image_url && (
                <img src={item.image_url} alt={item.name} className="w-full h-32 object-cover rounded-lg mb-2" />
              )}
              
              {item.name && <h3 className="font-heading font-semibold text-foreground">{item.name}</h3>}
              {item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Regular menu item
  return (
    <Card 
      ref={setNodeRef}
      style={style}
      className={`border-none shadow-md transition-all ${!item.is_available ? 'opacity-60' : ''} ${isDragging ? 'shadow-xl z-50' : ''}`}
      data-testid={`menu-item-${item.id}`}
    >
      <CardContent className="p-4">
        <div className="flex gap-4">
          <button
            className="cursor-grab active:cursor-grabbing p-1 self-center text-muted-foreground hover:text-foreground"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="w-5 h-5" />
          </button>

          <div className="w-20 h-20 rounded-xl bg-muted flex-shrink-0 overflow-hidden">
            {item.image_url ? (
              <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <ImageIcon className="w-6 h-6 text-muted-foreground/50" />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-heading font-semibold text-foreground truncate text-sm">{item.name}</h3>
                <div className="flex flex-wrap gap-1 mt-1">
                  {item.is_hit && <Badge className="bg-red-500 text-white text-xs px-1.5 py-0">Хит</Badge>}
                  {item.is_new && <Badge className="bg-emerald-500 text-white text-xs px-1.5 py-0">Новинка</Badge>}
                  {item.is_spicy && <Badge className="bg-orange-500 text-white text-xs px-1.5 py-0">Острое</Badge>}
                  {item.is_promotion && <Badge className="bg-purple-500 text-white text-xs px-1.5 py-0">Акция</Badge>}
                  {item.is_business_lunch && <Badge className="bg-blue-500 text-white text-xs px-1.5 py-0">Бизнес-ланч</Badge>}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Switch checked={item.is_available} onCheckedChange={() => onToggleAvailability(item)} />
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(item)}>
                  <Edit2 className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => onDelete(item)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {item.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{item.description}</p>
            )}
            
            <div className="flex items-center justify-between mt-2">
              <span className="text-base font-bold text-mint-500">{item.price} {currency}</span>
              {item.weight && <span className="text-xs text-muted-foreground">{item.weight}</span>}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

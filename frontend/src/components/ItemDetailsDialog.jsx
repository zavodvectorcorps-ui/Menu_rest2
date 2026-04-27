import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, Star, Sparkles, Flame, Image as ImageIcon, X } from 'lucide-react';

export default function ItemDetailsDialog({ open, onOpenChange, item, currency, labelsMap, ordersEnabled, onAdd }) {
  if (!item) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md p-0 overflow-hidden max-h-[92vh] flex flex-col" data-testid="item-details-dialog">
        {/* Image */}
        <div className="relative w-full bg-muted">
          {item.image_url ? (
            <img
              src={item.image_url}
              alt={item.name}
              className="w-full h-auto object-cover max-h-[55vh]"
              data-testid="item-details-image"
            />
          ) : (
            <div className="w-full aspect-square flex items-center justify-center">
              <ImageIcon className="w-16 h-16 text-muted-foreground/30" />
            </div>
          )}
          <button
            onClick={() => onOpenChange(false)}
            className="absolute top-3 right-3 w-9 h-9 rounded-full bg-black/50 hover:bg-black/70 backdrop-blur text-white flex items-center justify-center transition-colors"
            aria-label="Закрыть"
            data-testid="item-details-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-3">
          <div className="flex items-start gap-2 flex-wrap">
            <h2 className="text-xl font-heading font-bold text-foreground flex-1" data-testid="item-details-name">
              {item.name}
            </h2>
            {item.is_hit && (
              <Badge className="bg-red-500 text-white text-xs"><Star className="w-3 h-3 mr-0.5" />Хит</Badge>
            )}
            {item.is_new && (
              <Badge className="bg-emerald-500 text-white text-xs"><Sparkles className="w-3 h-3 mr-0.5" />Новинка</Badge>
            )}
            {item.is_spicy && (
              <Badge className="bg-orange-500 text-white text-xs"><Flame className="w-3 h-3 mr-0.5" />Острое</Badge>
            )}
            {(item.label_ids || []).map((lid) => {
              const lbl = labelsMap?.[lid];
              return lbl ? (
                <Badge key={lid} className="text-white text-xs" style={{ backgroundColor: lbl.color }}>
                  {lbl.name}
                </Badge>
              ) : null;
            })}
          </div>

          {item.weight && (
            <div className="text-sm text-muted-foreground" data-testid="item-details-weight">{item.weight}</div>
          )}

          {item.description && (
            <p className="text-sm text-foreground/80 whitespace-pre-line" data-testid="item-details-description">
              {item.description}
            </p>
          )}

          <div className="flex items-center justify-between pt-3 border-t border-border">
            <div className="text-2xl font-heading font-bold text-mint-500" data-testid="item-details-price">
              {item.price} {currency}
            </div>
            {ordersEnabled && (
              <Button
                className="rounded-full bg-mint-500 hover:bg-mint-600 text-white gap-2 h-11 px-5"
                onClick={() => { onAdd(item); onOpenChange(false); }}
                data-testid="item-details-add"
              >
                <Plus className="w-4 h-4" />
                Добавить
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

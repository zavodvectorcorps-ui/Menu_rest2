import { useState } from 'react';
import { Flame, Star, Sparkles, Tag, Plus, Loader2, RefreshCw, Edit2, Trash2, Check, ChevronsUpDown, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { cn } from '@/lib/utils';
import { ImageUpload } from './ImageUpload';

export function CategoryDialog({ open, onOpenChange, editing, form, setForm, menuSections, onSave }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading">
            {editing ? 'Редактировать категорию' : 'Новая категория'}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Название</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Например: Горячие блюда"
            />
          </div>
          <div className="space-y-2">
            <Label>Раздел меню</Label>
            <Select value={form.section_id} onValueChange={(value) => setForm({ ...form, section_id: value })}>
              <SelectTrigger><SelectValue placeholder="Выберите раздел" /></SelectTrigger>
              <SelectContent>
                {menuSections.map((section) => (
                  <SelectItem key={section.id} value={section.id}>{section.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Режим отображения</Label>
            <Select value={form.display_mode} onValueChange={(value) => setForm({ ...form, display_mode: value })}>
              <SelectTrigger><SelectValue placeholder="Выберите режим" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="card">Карточка с картинкой</SelectItem>
                <SelectItem value="compact">Компактный список</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {form.display_mode === 'card' 
                ? 'Позиции будут отображаться с картинками (для коктейлей, блюд)' 
                : 'Позиции будут отображаться строкой: название, цена, объём (для виски, вина)'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Switch checked={form.is_active} onCheckedChange={(checked) => setForm({ ...form, is_active: checked })} />
            <Label>Активна</Label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button onClick={onSave} className="bg-mint-500 hover:bg-mint-600" disabled={!form.name}>Сохранить</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ItemDialog({ open, onOpenChange, editing, form, setForm, categories, labels, currency, onSave, onToggleLabel, caffestaProducts = [] }) {
  const [caffestaOpen, setCaffestaOpen] = useState(false);

  const selectedCafProduct = caffestaProducts.find(p => p.product_id === Number(form.caffesta_product_id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading">
            {editing ? (form.is_banner ? 'Редактировать баннер' : 'Редактировать позицию') : (form.is_banner ? 'Новый баннер' : 'Новая позиция')}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Категория</Label>
              <Select value={form.category_id} onValueChange={(value) => setForm({ ...form, category_id: value })}>
                <SelectTrigger><SelectValue placeholder="Выберите категорию" /></SelectTrigger>
                <SelectContent>
                  {categories.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>{form.is_banner ? 'Заголовок (опционально)' : 'Название'}</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder={form.is_banner ? 'Заголовок баннера' : 'Название блюда'}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Описание</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder={form.is_banner ? 'Текст баннера' : 'Описание блюда, состав...'}
              rows={3}
            />
          </div>

          {!form.is_banner && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Цена ({currency})</Label>
                <Input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} placeholder="0" />
              </div>
              <div className="space-y-2">
                <Label>Объём / Выход</Label>
                <Input value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} placeholder="200 г" />
              </div>
            </div>
          )}

          {!form.is_banner && (
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Привязка к Caffesta</Label>
              {caffestaProducts.length > 0 ? (
                <div className="flex items-center gap-2">
                  <Popover open={caffestaOpen} onOpenChange={setCaffestaOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        className="w-full justify-between font-normal h-9 text-sm"
                        data-testid="caffesta-product-combobox"
                      >
                        {selectedCafProduct
                          ? `${selectedCafProduct.title} (ID: ${selectedCafProduct.product_id})`
                          : 'Выберите товар из Caffesta...'}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Поиск товара..." />
                        <CommandList>
                          <CommandEmpty>Товар не найден</CommandEmpty>
                          <CommandGroup className="max-h-[200px] overflow-y-auto">
                            {caffestaProducts.map((p) => (
                              <CommandItem
                                key={p.product_id}
                                value={`${p.title} ${p.product_id}`}
                                onSelect={() => {
                                  setForm({ ...form, caffesta_product_id: String(p.product_id) });
                                  setCaffestaOpen(false);
                                }}
                              >
                                <Check className={cn("mr-2 h-4 w-4", Number(form.caffesta_product_id) === p.product_id ? "opacity-100" : "opacity-0")} />
                                <span className="truncate">{p.title}</span>
                                <span className="ml-auto text-xs text-muted-foreground">ID: {p.product_id}</span>
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
                  {form.caffesta_product_id && (
                    <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={() => setForm({ ...form, caffesta_product_id: '' })} data-testid="caffesta-product-clear">
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ) : (
                <Input
                  type="number"
                  value={form.caffesta_product_id}
                  onChange={(e) => setForm({ ...form, caffesta_product_id: e.target.value })}
                  placeholder="ID товара в Caffesta (настройте интеграцию для автозагрузки)"
                  data-testid="caffesta-product-id-input"
                />
              )}
            </div>
          )}

          <ImageUpload value={form.image_url} onChange={(url) => setForm({ ...form, image_url: url })} />

          {!form.is_banner && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2">
              <div className="flex items-center gap-2">
                <Switch checked={form.is_available} onCheckedChange={(checked) => setForm({ ...form, is_available: checked })} />
                <Label>В наличии</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.is_hit} onCheckedChange={(checked) => setForm({ ...form, is_hit: checked })} />
                <Label className="flex items-center gap-1"><Star className="w-4 h-4" /> Хит</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.is_new} onCheckedChange={(checked) => setForm({ ...form, is_new: checked })} />
                <Label className="flex items-center gap-1"><Sparkles className="w-4 h-4" /> Новинка</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.is_spicy} onCheckedChange={(checked) => setForm({ ...form, is_spicy: checked })} />
                <Label className="flex items-center gap-1"><Flame className="w-4 h-4" /> Острое</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.is_promotion} onCheckedChange={(checked) => setForm({ ...form, is_promotion: checked })} />
                <Label className="flex items-center gap-1"><Tag className="w-4 h-4" /> Акция</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={form.is_business_lunch} onCheckedChange={(checked) => setForm({ ...form, is_business_lunch: checked })} />
                <Label>Бизнес-ланч</Label>
              </div>
            </div>
          )}

          {!form.is_banner && labels.length > 0 && (
            <div className="space-y-2 pt-2">
              <Label>Ярлыки</Label>
              <div className="flex flex-wrap gap-2" data-testid="item-labels-selector">
                {labels.map((label) => (
                  <button
                    key={label.id}
                    type="button"
                    onClick={() => onToggleLabel(label.id)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-all border-2 ${
                      form.label_ids.includes(label.id) ? 'border-transparent text-white' : 'border-dashed opacity-50 hover:opacity-80'
                    }`}
                    style={{
                      backgroundColor: form.label_ids.includes(label.id) ? label.color : 'transparent',
                      borderColor: form.label_ids.includes(label.id) ? label.color : label.color,
                      color: form.label_ids.includes(label.id) ? 'white' : label.color
                    }}
                    data-testid={`label-toggle-${label.id}`}
                  >
                    {label.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {form.is_banner && (
            <div className="flex items-center gap-2">
              <Switch checked={form.is_available} onCheckedChange={(checked) => setForm({ ...form, is_available: checked })} />
              <Label>Показывать баннер</Label>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button onClick={onSave} className="bg-mint-500 hover:bg-mint-600" disabled={!form.category_id || (!form.is_banner && !form.name)}>
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DeleteDialog({ open, onOpenChange, target, onConfirm }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="font-heading">Подтверждение удаления</DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground py-4">
          Вы уверены, что хотите удалить {target?.type === 'category' ? 'категорию' : 'позицию'}{' '}
          <strong>"{target?.name}"</strong>?
          {target?.type === 'category' && (
            <span className="block mt-2 text-destructive">Все позиции в этой категории также будут удалены!</span>
          )}
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button variant="destructive" onClick={onConfirm}>Удалить</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ImportJsonDialog({ open, onOpenChange, importJson, setImportJson, importing, onImport }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading">Импорт меню из JSON</DialogTitle>
          <DialogDescription>
            Вставьте или отредактируйте JSON-данные меню. Формат: {"{"}"categories": [{"{"}"name": "...", "items": [...]{"}"}{"]"}{"}"} 
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <Textarea
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            placeholder='{"categories": [{"name": "Закуски", "items": [{"name": "Цезарь", "price": 15.0}]}]}'
            className="font-mono text-sm min-h-[250px]"
            data-testid="import-json-textarea"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { onOpenChange(false); setImportJson(''); }}>Отмена</Button>
          <Button
            onClick={onImport}
            className="bg-mint-500 hover:bg-mint-600 gap-2"
            disabled={importing || !importJson.trim()}
            data-testid="import-json-submit"
          >
            {importing && <Loader2 className="w-4 h-4 animate-spin" />}
            {importing ? 'Импорт...' : 'Импортировать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ImportModeDialog({ open, onOpenChange, pendingFile, importing, onExecute }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="font-heading">Режим импорта</DialogTitle>
          <DialogDescription>
            {pendingFile?.name && <span className="block mb-2 text-sm font-medium">{pendingFile.name}</span>}
            Как обработать импортируемое меню?
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-4">
          <button
            onClick={() => onExecute('replace')}
            className="flex items-start gap-4 p-4 rounded-xl border-2 border-border hover:border-destructive/50 hover:bg-destructive/5 transition-all text-left group"
            disabled={importing}
            data-testid="import-mode-replace"
          >
            <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-red-500/20">
              <RefreshCw className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h4 className="font-medium text-sm">Полное обновление</h4>
              <p className="text-xs text-muted-foreground mt-0.5">Удалить всё текущее меню и загрузить новое из файла</p>
            </div>
          </button>
          <button
            onClick={() => onExecute('append')}
            className="flex items-start gap-4 p-4 rounded-xl border-2 border-border hover:border-mint-500/50 hover:bg-mint-500/5 transition-all text-left group"
            disabled={importing}
            data-testid="import-mode-append"
          >
            <div className="w-10 h-10 rounded-xl bg-mint-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-mint-500/20">
              <Plus className="w-5 h-5 text-mint-500" />
            </div>
            <div>
              <h4 className="font-medium text-sm">Дополнить меню</h4>
              <p className="text-xs text-muted-foreground mt-0.5">Сохранить текущее меню и добавить новые позиции</p>
            </div>
          </button>
        </div>
        {importing && (
          <div className="flex items-center justify-center gap-2 py-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm text-muted-foreground">Импорт...</span>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function LabelDialog({ open, onOpenChange, editing, setEditing, form, setForm, labels, onSave, onDelete }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-heading">{editing ? 'Редактировать ярлык' : 'Ярлыки'}</DialogTitle>
          <DialogDescription>Ярлыки отображаются на карточках блюд в клиентском меню</DialogDescription>
        </DialogHeader>

        {!editing && labels.length > 0 && (
          <div className="space-y-2 py-2">
            {labels.map((label) => (
              <div key={label.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/50" data-testid={`label-item-${label.id}`}>
                <div className="flex items-center gap-2">
                  <span className="w-4 h-4 rounded-full" style={{ backgroundColor: label.color }} />
                  <span className="text-sm font-medium">{label.name}</span>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setEditing(label); setForm({ name: label.name, color: label.color }); }}>
                    <Edit2 className="w-3.5 h-3.5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => onDelete(label.id)}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="space-y-3 py-2">
          <div className="space-y-2">
            <Label>Название</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Хит, Сезонное, Выбор гостей..."
              data-testid="label-name-input"
            />
          </div>
          <div className="space-y-2">
            <Label>Цвет</Label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
                className="w-10 h-10 rounded-lg cursor-pointer border border-border"
                data-testid="label-color-input"
              />
              <div className="flex gap-2 flex-wrap">
                {['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'].map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setForm({ ...form, color: c })}
                    className={`w-7 h-7 rounded-full transition-transform ${form.color === c ? 'ring-2 ring-offset-2 ring-offset-background scale-110' : ''}`}
                    style={{ backgroundColor: c, ringColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <span className="text-sm text-muted-foreground">Предпросмотр:</span>
            <span className="px-3 py-1 rounded-full text-xs font-medium text-white" style={{ backgroundColor: form.color }}>
              {form.name || 'Ярлык'}
            </span>
          </div>
        </div>
        <DialogFooter>
          {editing && (
            <Button variant="outline" onClick={() => { setEditing(null); setForm({ name: '', color: '#ef4444' }); }}>
              Назад
            </Button>
          )}
          <Button onClick={onSave} className="bg-mint-500 hover:bg-mint-600" disabled={!form.name.trim()} data-testid="save-label-btn">
            {editing ? 'Сохранить' : 'Создать ярлык'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

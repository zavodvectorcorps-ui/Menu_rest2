import { useState, useEffect } from 'react';
import { Flame, Star, Sparkles, Tag, Plus, Loader2, RefreshCw, Edit2, Trash2, Check, ChevronsUpDown, X, ShoppingBag } from 'lucide-react';
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
                <SelectItem value="tiles">Крупные плитки (квадраты 2×2)</SelectItem>
                <SelectItem value="compact">Компактный список</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {form.display_mode === 'card'
                ? 'Позиции будут отображаться с картинками (для коктейлей, блюд)'
                : form.display_mode === 'tiles'
                  ? 'Крупные квадратные плитки в 2 колонки — для визуально насыщенного меню (десерты, пицца)'
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
  const typeLabel = (t) => t === 'tech_map' ? 'Тех.карта' : 'Товар';

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
            <div className="space-y-2 border border-border/60 rounded-lg p-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold text-foreground">Пищевая ценность <span className="text-muted-foreground font-normal">(на 100 г, необязательно)</span></Label>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Белки, г</Label>
                  <Input
                    type="number" step="0.1" inputMode="decimal"
                    value={form.nutrition_protein ?? ''}
                    onChange={(e) => setForm({ ...form, nutrition_protein: e.target.value })}
                    placeholder="20"
                    className="h-9"
                    data-testid="nutrition-protein-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Жиры, г</Label>
                  <Input
                    type="number" step="0.1" inputMode="decimal"
                    value={form.nutrition_fat ?? ''}
                    onChange={(e) => setForm({ ...form, nutrition_fat: e.target.value })}
                    placeholder="12"
                    className="h-9"
                    data-testid="nutrition-fat-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Углеводы, г</Label>
                  <Input
                    type="number" step="0.1" inputMode="decimal"
                    value={form.nutrition_carbs ?? ''}
                    onChange={(e) => setForm({ ...form, nutrition_carbs: e.target.value })}
                    placeholder="5"
                    className="h-9"
                    data-testid="nutrition-carbs-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">Ккал</Label>
                  <Input
                    type="number" step="0.1" inputMode="decimal"
                    value={form.nutrition_kcal ?? ''}
                    onChange={(e) => setForm({ ...form, nutrition_kcal: e.target.value })}
                    placeholder="210"
                    className="h-9"
                    data-testid="nutrition-kcal-input"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[11px] text-muted-foreground">кДж</Label>
                  <Input
                    type="number" step="0.1" inputMode="decimal"
                    value={form.nutrition_kj ?? ''}
                    onChange={(e) => setForm({ ...form, nutrition_kj: e.target.value })}
                    placeholder="880"
                    className="h-9"
                    data-testid="nutrition-kj-input"
                  />
                </div>
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
                          ? `[${typeLabel(selectedCafProduct.type)}] ${selectedCafProduct.title} (ID: ${selectedCafProduct.product_id})`
                          : 'Выберите товар или тех.карту из Caffesta...'}
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
                                value={`${p.title} ${p.product_id} ${p.type === 'tech_map' ? 'тех.карта техкарта' : 'товар'}`}
                                onSelect={() => {
                                  setForm({ ...form, caffesta_product_id: String(p.product_id) });
                                  setCaffestaOpen(false);
                                }}
                              >
                                <Check className={cn("mr-2 h-4 w-4", Number(form.caffesta_product_id) === p.product_id ? "opacity-100" : "opacity-0")} />
                                <span className={`mr-1.5 text-[10px] px-1 py-0.5 rounded ${p.type === 'tech_map' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                  {p.type === 'tech_map' ? 'ТК' : 'Т'}
                                </span>
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
                <Switch checked={!!form.is_takeaway} onCheckedChange={(checked) => setForm({ ...form, is_takeaway: checked })} />
                <Label className="flex items-center gap-1"><ShoppingBag className="w-4 h-4" /> На вынос</Label>
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

export function BulkRenameCategoriesDialog({ open, onOpenChange, categories, saving, onSave }) {
  // Map id -> draft name
  const [drafts, setDrafts] = useState({});
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');

  // Initialise drafts when the dialog is opened (or when categories change while open)
  useEffect(() => {
    if (open) {
      const initial = {};
      categories.forEach((c) => { initial[c.id] = c.name; });
      setDrafts(initial);
      setFindText('');
      setReplaceText('');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleClose = (val) => {
    if (!val) {
      setDrafts({});
      setFindText('');
      setReplaceText('');
    }
    onOpenChange(val);
  };

  const applyFindReplace = () => {
    if (!findText) return;
    const next = { ...drafts };
    let changed = 0;
    categories.forEach((c) => {
      const current = next[c.id] ?? c.name;
      if (current.includes(findText)) {
        next[c.id] = current.split(findText).join(replaceText);
        changed++;
      }
    });
    setDrafts(next);
    return changed;
  };

  const clearPrefix = (prefix) => {
    const next = { ...drafts };
    categories.forEach((c) => {
      const current = next[c.id] ?? c.name;
      if (current.startsWith(prefix)) {
        next[c.id] = current.slice(prefix.length).trim();
      }
    });
    setDrafts(next);
  };

  const resetAll = () => {
    const initial = {};
    categories.forEach((c) => { initial[c.id] = c.name; });
    setDrafts(initial);
  };

  // Build payload of actually changed entries
  const changedEntries = categories
    .map((c) => ({ id: c.id, original: c.name, name: (drafts[c.id] ?? c.name).trim() }))
    .filter((e) => e.name && e.name !== e.original);

  const handleSubmit = () => {
    if (changedEntries.length === 0) {
      onOpenChange(false);
      return;
    }
    onSave(changedEntries.map(({ id, name }) => ({ id, name })));
  };

  // Suggest a quick prefix from longest common prefix containing " — "
  const suggestedPrefixes = (() => {
    const prefixes = new Set();
    categories.forEach((c) => {
      const parts = c.name.split(' — ');
      if (parts.length >= 2) {
        prefixes.add(parts[0] + ' — ');
      }
    });
    return Array.from(prefixes).filter((p) => {
      const count = categories.filter((c) => c.name.startsWith(p)).length;
      return count >= 2;
    }).sort();
  })();

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col" data-testid="bulk-rename-dialog">
        <DialogHeader>
          <DialogTitle>Массовое переименование категорий</DialogTitle>
          <DialogDescription>
            Найдите и замените подстроку во всех названиях или редактируйте поля вручную.
            Сохранятся только изменённые строки.
          </DialogDescription>
        </DialogHeader>

        {/* Find/Replace */}
        <div className="flex flex-col gap-2 border-b pb-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              placeholder="Найти…"
              value={findText}
              onChange={(e) => setFindText(e.target.value)}
              className="flex-1"
              data-testid="bulk-rename-find-input"
            />
            <Input
              placeholder="Заменить на…"
              value={replaceText}
              onChange={(e) => setReplaceText(e.target.value)}
              className="flex-1"
              data-testid="bulk-rename-replace-input"
            />
            <Button
              variant="outline"
              onClick={applyFindReplace}
              disabled={!findText}
              data-testid="bulk-rename-apply-btn"
            >
              Применить
            </Button>
          </div>
          {suggestedPrefixes.length > 0 && (
            <div className="flex flex-wrap gap-2 items-center">
              <span className="text-xs text-muted-foreground">Быстро убрать префикс:</span>
              {suggestedPrefixes.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => clearPrefix(p)}
                  className="text-xs px-2 py-1 rounded-full border bg-muted hover:bg-accent transition-colors"
                  data-testid={`bulk-rename-prefix-${p.trim().replace(/\s+/g, '-')}`}
                >
                  «{p}»
                </button>
              ))}
              <button
                type="button"
                onClick={resetAll}
                className="text-xs px-2 py-1 rounded-full border bg-muted hover:bg-accent transition-colors ml-auto"
                data-testid="bulk-rename-reset-btn"
              >
                Сбросить
              </button>
            </div>
          )}
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto -mx-6 px-6">
          <div className="grid grid-cols-[1fr,1fr] gap-x-3 gap-y-2 text-sm">
            <div className="text-xs font-medium text-muted-foreground sticky top-0 bg-background pb-1">
              Текущее название
            </div>
            <div className="text-xs font-medium text-muted-foreground sticky top-0 bg-background pb-1">
              Новое название
            </div>
            {categories.map((c) => {
              const draft = drafts[c.id] ?? c.name;
              const isChanged = draft.trim() && draft.trim() !== c.name;
              return (
                <div key={c.id} className="contents">
                  <div
                    className="py-1.5 text-muted-foreground break-words border-b border-border/50"
                    title={c.name}
                  >
                    {c.name}
                  </div>
                  <div className="py-1 border-b border-border/50">
                    <Input
                      value={draft}
                      onChange={(e) => setDrafts({ ...drafts, [c.id]: e.target.value })}
                      className={cn('h-8', isChanged && 'border-mint-500 ring-1 ring-mint-500/30')}
                      data-testid={`bulk-rename-input-${c.id}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2 sm:gap-2">
          <div className="text-sm text-muted-foreground mr-auto" data-testid="bulk-rename-counter">
            Изменено: <b>{changedEntries.length}</b> из {categories.length}
          </div>
          <Button variant="outline" onClick={() => handleClose(false)}>Отмена</Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || changedEntries.length === 0}
            data-testid="bulk-rename-save-btn"
          >
            {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Сохранение…</> : `Сохранить ${changedEntries.length || ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}




export function NutritionImportDialog({ open, onOpenChange, onImport }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);   // { matched, ambiguous, unmatched, records_total }
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [checkedMatched, setCheckedMatched] = useState({});      // { [source_key]: true/false }
  const [ambiguousChoice, setAmbiguousChoice] = useState({});   // { [source_key]: item_id }

  useEffect(() => {
    if (!open) {
      setFile(null); setPreview(null); setLoading(false); setApplying(false);
      setCheckedMatched({}); setAmbiguousChoice({});
    }
  }, [open]);

  // On preview: default all matched checked, no ambiguous selected
  useEffect(() => {
    if (preview) {
      const cm = {};
      preview.matched.forEach((m) => { cm[m.source] = true; });
      setCheckedMatched(cm);
      setAmbiguousChoice({});
    }
  }, [preview]);

  const runPreview = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const result = await onImport({ file, dryRun: true });
      setPreview(result);
    } catch (e) {
      // handled by parent toast
    } finally {
      setLoading(false);
    }
  };

  // Rows the user will actually apply
  const finalRows = (() => {
    if (!preview) return [];
    const rows = [];
    preview.matched.forEach((m) => {
      if (checkedMatched[m.source]) {
        rows.push({ item_id: m.item_id, source: m.source, item_name: m.item_name, score: m.score });
      }
    });
    preview.ambiguous.forEach((a) => {
      const chosen = ambiguousChoice[a.source];
      if (chosen) {
        const cand = a.candidates.find((c) => c.item_id === chosen);
        rows.push({ item_id: chosen, source: a.source, item_name: cand?.name, score: cand?.score });
      }
    });
    return rows;
  })();

  const applyImport = async () => {
    if (!file || finalRows.length === 0) return;
    setApplying(true);
    try {
      const ids = finalRows.map((r) => r.item_id).join(',');
      await onImport({ file, dryRun: false, applyIds: ids, finalCount: finalRows.length });
      onOpenChange(false);
    } finally {
      setApplying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[92vh] flex flex-col" data-testid="nutrition-import-dialog">
        <DialogHeader>
          <DialogTitle>Импорт БЖУ из .docx</DialogTitle>
          <DialogDescription>
            Загрузите документ с таблицами Белки/Жиры/Углеводы/Ккал/кДж на 100 г. Система найдёт блюда в вашем меню по названию и предложит проставить значения.
          </DialogDescription>
        </DialogHeader>

        {!preview && (
          <div className="flex flex-col items-center gap-4 py-8">
            <input
              type="file"
              accept=".docx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block text-sm file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:bg-mint-500 file:text-white file:font-semibold hover:file:bg-mint-600 cursor-pointer"
              data-testid="nutrition-file-input"
            />
            {file && (
              <div className="text-xs text-muted-foreground">Выбран: {file.name} ({Math.round(file.size / 1024)} KB)</div>
            )}
            <Button onClick={runPreview} disabled={!file || loading} data-testid="nutrition-preview-btn">
              {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Разбираю…</> : 'Показать предпросмотр'}
            </Button>
          </div>
        )}

        {preview && (
          <div className="flex-1 overflow-y-auto -mx-6 px-6 space-y-4">
            <div className="text-xs text-muted-foreground">
              Всего строк в файле: <b>{preview.records_total}</b> · Найдено точно: <b>{preview.matched.length}</b> · Требуют выбора: <b>{preview.ambiguous.length}</b> · Не найдено: <b>{preview.unmatched.length}</b>
            </div>

            {preview.matched.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <Check className="w-4 h-4 text-mint-500" />
                  Автоматически сматчено ({preview.matched.length})
                </h3>
                <div className="border border-border rounded-lg divide-y">
                  {preview.matched.map((m) => (
                    <label key={m.source} className="flex items-center gap-3 px-3 py-2 hover:bg-muted/40 cursor-pointer text-sm">
                      <input
                        type="checkbox"
                        checked={!!checkedMatched[m.source]}
                        onChange={(e) => setCheckedMatched({ ...checkedMatched, [m.source]: e.target.checked })}
                        className="w-4 h-4"
                        data-testid={`nutrition-match-cb-${m.item_id}`}
                      />
                      <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-2 gap-x-3">
                        <div className="truncate">
                          <span className="text-muted-foreground text-xs">Из файла:</span> {m.source}
                        </div>
                        <div className="truncate">
                          <span className="text-muted-foreground text-xs">Блюдо:</span> {m.item_name}
                        </div>
                      </div>
                      <span className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full font-semibold whitespace-nowrap",
                        m.score >= 95 ? 'bg-mint-500 text-white' : m.score >= 80 ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'
                      )}>{m.score}%</span>
                    </label>
                  ))}
                </div>
              </section>
            )}

            {preview.ambiguous.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2 text-amber-600">
                  <Sparkles className="w-4 h-4" />
                  Требуется выбор ({preview.ambiguous.length})
                </h3>
                <div className="border border-amber-300/50 rounded-lg divide-y">
                  {preview.ambiguous.map((a) => (
                    <div key={a.source} className="px-3 py-2 text-sm">
                      <div className="mb-1.5 text-muted-foreground">
                        Из файла: <b className="text-foreground">{a.source}</b>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => setAmbiguousChoice({ ...ambiguousChoice, [a.source]: '__skip__' })}
                          className={cn(
                            "px-2 py-1 rounded-full text-xs border transition-colors",
                            ambiguousChoice[a.source] === '__skip__' ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-100'
                          )}
                        >
                          Пропустить
                        </button>
                        {a.candidates.map((c) => (
                          <button
                            key={c.item_id}
                            type="button"
                            onClick={() => setAmbiguousChoice({ ...ambiguousChoice, [a.source]: c.item_id })}
                            className={cn(
                              "px-2 py-1 rounded-full text-xs border transition-colors",
                              ambiguousChoice[a.source] === c.item_id ? 'bg-mint-500 text-white border-mint-500' : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-100'
                            )}
                            data-testid={`nutrition-ambig-choice-${c.item_id}`}
                          >
                            {c.name} <span className="opacity-60">({c.score}%)</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {preview.unmatched.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2 text-muted-foreground">
                  <X className="w-4 h-4" />
                  Не найдены в меню ({preview.unmatched.length})
                </h3>
                <div className="text-xs text-muted-foreground">
                  Добавьте эти позиции в меню вручную или переименуйте существующие, чтобы совпало с файлом.
                </div>
                <ul className="mt-1.5 text-sm space-y-0.5">
                  {preview.unmatched.map((u) => (
                    <li key={u.source} className="text-muted-foreground">• {u.source}</li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {preview && (
            <div className="text-sm text-muted-foreground mr-auto" data-testid="nutrition-final-counter">
              Будет применено: <b>{finalRows.length}</b>
            </div>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          {preview && (
            <Button
              onClick={applyImport}
              disabled={applying || finalRows.length === 0}
              data-testid="nutrition-apply-btn"
            >
              {applying ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Применяю…</> : `Применить ${finalRows.length || ''}`}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

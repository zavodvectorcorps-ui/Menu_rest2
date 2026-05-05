import { useEffect, useMemo, useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import {
  ChefHat, Plus, Trash2, RefreshCw, Search, AlertTriangle,
  Loader2, Save, X,
} from 'lucide-react';
import { useApp } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Helper: compute line cost qty * unit_factor * unit_cost
function lineCost(ing) {
  const qty = Number(ing.qty) || 0;
  const fac = Number(ing.unit_factor) || 1;
  const uc = Number(ing.unit_cost) || 0;
  return qty * fac * uc;
}

// Helper: margin coloring. <40% red, 40-55% amber, >=55% green.
function marginClass(pct) {
  if (pct == null || isNaN(pct)) return 'text-muted-foreground';
  if (pct < 40) return 'text-rose-600 font-semibold';
  if (pct < 55) return 'text-amber-600 font-semibold';
  return 'text-emerald-600 font-semibold';
}

export default function RecipeCalculatorPage() {
  const { currentRestaurantId, settings } = useApp();
  const currency = settings?.currency || 'BYN';
  const authHeaders = { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } };

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [catalog, setCatalog] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [includeTechCards, setIncludeTechCards] = useState(false);
  const [costSource, setCostSource] = useState('avgInvoicedSelfCost');
  const [recomputing, setRecomputing] = useState(false);
  const [search, setSearch] = useState('');
  const [editItem, setEditItem] = useState(null);

  const loadItems = useCallback(async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const r = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/costs/analysis`,
        authHeaders,
      );
      setItems(r.data?.items || []);
    } catch {
      toast.error('Не удалось загрузить меню');
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRestaurantId]);

  const loadCatalog = useCallback(async () => {
    if (!currentRestaurantId) return;
    setCatalogLoading(true);
    try {
      const r = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/cost-catalog?include_tech_cards=${includeTechCards}`,
        authHeaders,
      );
      setCatalog(r.data?.data || []);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(
        typeof detail === 'string' ? detail : 'Не удалось получить каталог Caffesta',
      );
      setCatalog([]);
    } finally {
      setCatalogLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRestaurantId, includeTechCards]);

  useEffect(() => { loadItems(); }, [loadItems]);
  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  const recomputeAll = async () => {
    if (!currentRestaurantId) return;
    setRecomputing(true);
    try {
      const r = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/recipes/recompute-all?cost_source=${costSource}`,
        {},
        authHeaders,
      );
      toast.success(`Обновлено ${r.data?.updated || 0} рецептов (источник: ${costSource})`);
      await loadItems();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Ошибка пересчёта');
    } finally {
      setRecomputing(false);
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => (it.name || '').toLowerCase().includes(q));
  }, [items, search]);

  const summary = useMemo(() => {
    let totalCost = 0;
    let totalPrice = 0;
    let noRecipe = 0;
    let lowMargin = 0;
    for (const it of items) {
      const p = Number(it.price) || 0;
      const c = Number(it.cost_price) || 0;
      if (!c) { noRecipe += 1; continue; }
      totalCost += c;
      totalPrice += p;
      if (p > 0 && ((p - c) / p) * 100 < 40) lowMargin += 1;
    }
    const avgMargin = totalPrice > 0 ? ((totalPrice - totalCost) / totalPrice) * 100 : 0;
    return { totalCost, totalPrice, noRecipe, lowMargin, avgMargin };
  }, [items]);

  return (
    <div className="space-y-6" data-testid="recipe-calculator-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold flex items-center gap-2">
            <ChefHat className="w-6 h-6 text-mint-500" />
            Калькуляция блюд
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Состав каждого блюда подтягивает себестоимость из Caffesta. Маржа, Food Cost и
            наценка считаются автоматически.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={costSource}
            onChange={(e) => setCostSource(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
            data-testid="cost-source-select"
          >
            <option value="avgInvoicedSelfCost">Источник: средняя закупочная</option>
            <option value="self_cost">Источник: текущая себестоимость</option>
          </select>
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer h-10">
            <input
              type="checkbox"
              checked={includeTechCards}
              onChange={(e) => setIncludeTechCards(e.target.checked)}
              data-testid="include-tech-cards-toggle"
            />
            Включая тех. карты
          </label>
          <Button
            variant="outline"
            onClick={recomputeAll}
            disabled={recomputing}
            data-testid="recompute-all-btn"
          >
            {recomputing
              ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Пересчитываем…</>
              : <><RefreshCw className="w-4 h-4 mr-2" />Пересчитать все рецепты</>}
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryCard label="Блюд всего" value={items.length} />
        <SummaryCard
          label="Без рецепта"
          value={summary.noRecipe}
          hint="Себестоимость не посчитана"
          tone={summary.noRecipe > 0 ? 'amber' : 'muted'}
        />
        <SummaryCard
          label="Средняя маржа"
          value={`${summary.avgMargin.toFixed(1)}%`}
          tone={summary.avgMargin >= 55 ? 'emerald' : summary.avgMargin >= 40 ? 'amber' : 'rose'}
        />
        <SummaryCard
          label="Низкая маржа"
          value={summary.lowMargin}
          hint="< 40%"
          tone={summary.lowMargin > 0 ? 'rose' : 'muted'}
        />
      </div>

      {/* Search */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Поиск по блюду…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            data-testid="recipe-search"
          />
        </div>
        {catalogLoading && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> Загружаем каталог Caffesta…
          </span>
        )}
        {!catalogLoading && catalog.length === 0 && (
          <span className="text-xs text-amber-600 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            Каталог Caffesta пуст — проверьте интеграцию
          </span>
        )}
      </div>

      {/* Items table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Блюда и себестоимость</CardTitle>
          <CardDescription>
            Клик по строке — редактирование состава. Цвет маржи: &gt;55% зелёный,
            40-55% жёлтый, &lt;40% красный.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-10 text-center text-muted-foreground">Загрузка…</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/30 border-y border-border">
                  <tr className="text-left">
                    <th className="px-4 py-2 font-medium">Блюдо</th>
                    <th className="px-4 py-2 font-medium text-right">Цена</th>
                    <th className="px-4 py-2 font-medium text-right">Себест.</th>
                    <th className="px-4 py-2 font-medium text-right">Маржа</th>
                    <th className="px-4 py-2 font-medium text-right">Маржа %</th>
                    <th className="px-4 py-2 font-medium text-right">Food Cost %</th>
                    <th className="px-4 py-2 font-medium text-right">Наценка %</th>
                    <th className="px-4 py-2 font-medium text-right">Состав</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 && (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">Нет блюд</td></tr>
                  )}
                  {filtered.map((it) => {
                    const price = Number(it.price) || 0;
                    const cost = Number(it.cost_price) || 0;
                    const hasCost = cost > 0;
                    const profit = hasCost && price > 0 ? price - cost : null;
                    const marginPct = hasCost && price > 0 ? ((price - cost) / price) * 100 : null;
                    const foodCostPct = hasCost && price > 0 ? (cost / price) * 100 : null;
                    const markupPct = hasCost && cost > 0 ? ((price - cost) / cost) * 100 : null;
                    return (
                      <tr
                        key={it.id}
                        className="border-b border-border/50 hover:bg-muted/20 cursor-pointer"
                        onClick={() => setEditItem(it)}
                        data-testid={`recipe-row-${it.id}`}
                      >
                        <td className="px-4 py-2">
                          <div className="font-medium">{it.name}</div>
                          {it.category_name && (
                            <div className="text-xs text-muted-foreground">{it.category_name}</div>
                          )}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">{price.toFixed(2)} {currency}</td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {hasCost ? <span>{cost.toFixed(2)} {currency}</span> : <span className="text-amber-600">нет</span>}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">
                          {profit != null ? `${profit.toFixed(2)} ${currency}` : '—'}
                        </td>
                        <td className={`px-4 py-2 text-right tabular-nums ${marginClass(marginPct)}`}>
                          {marginPct != null ? `${marginPct.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
                          {foodCostPct != null ? `${foodCostPct.toFixed(1)}%` : '—'}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
                          {markupPct != null ? `${markupPct.toFixed(0)}%` : '—'}
                        </td>
                        <td className="px-4 py-2 text-right text-xs text-muted-foreground">
                          {(it.recipe || []).length > 0
                            ? `${it.recipe.length} ингр.`
                            : <span className="text-muted-foreground/60">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {editItem && (
        <RecipeEditorDialog
          item={editItem}
          catalog={catalog}
          costSource={costSource}
          currency={currency}
          restaurantId={currentRestaurantId}
          onClose={() => setEditItem(null)}
          onSaved={async () => {
            setEditItem(null);
            await loadItems();
          }}
        />
      )}
    </div>
  );
}


function SummaryCard({ label, value, hint, tone = 'muted' }) {
  const toneMap = {
    muted: 'bg-muted/30',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-200/50',
    amber: 'bg-amber-50 dark:bg-amber-900/10 border-amber-200/50',
    rose: 'bg-rose-50 dark:bg-rose-900/10 border-rose-200/50',
  };
  return (
    <div className={`rounded-lg border p-4 ${toneMap[tone]}`}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-2xl font-semibold mt-1 tabular-nums">{value}</div>
      {hint && <div className="text-xs text-muted-foreground mt-0.5">{hint}</div>}
    </div>
  );
}


function RecipeEditorDialog({ item, catalog, costSource, currency, restaurantId, onClose, onSaved }) {
  const authHeaders = { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } };
  const [ingredients, setIngredients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSearch, setPickerSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(
          `${API}/restaurants/${restaurantId}/menu-items/${item.id}/recipe`,
          authHeaders,
        );
        if (!cancelled) setIngredients(r.data?.recipe || []);
      } catch {
        if (!cancelled) toast.error('Не удалось загрузить состав');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  const total = useMemo(
    () => ingredients.reduce((s, ing) => s + lineCost(ing), 0),
    [ingredients],
  );
  const price = Number(item.price) || 0;
  const marginPct = price > 0 && total > 0 ? ((price - total) / price) * 100 : null;

  const addIngredient = (p) => {
    const source = costSource === 'self_cost' ? p.self_cost : (p.avgInvoicedSelfCost || p.self_cost);
    setIngredients((prev) => [
      ...prev,
      {
        caffesta_product_id: p.caffesta_product_id,
        name: p.name,
        qty: 0,
        unit: 'шт',
        unit_factor: 1,
        unit_cost: Number(source) || 0,
      },
    ]);
    setPickerOpen(false);
    setPickerSearch('');
  };

  const updateIng = (idx, patch) => {
    setIngredients((prev) => prev.map((ing, i) => i === idx ? { ...ing, ...patch } : ing));
  };

  const removeIng = (idx) => {
    setIngredients((prev) => prev.filter((_, i) => i !== idx));
  };

  const save = async () => {
    setSaving(true);
    try {
      await axios.put(
        `${API}/restaurants/${restaurantId}/menu-items/${item.id}/recipe`,
        { ingredients, cost_source: costSource },
        authHeaders,
      );
      toast.success('Состав сохранён');
      onSaved();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const pickerFiltered = useMemo(() => {
    const q = pickerSearch.trim().toLowerCase();
    if (!q) return catalog.slice(0, 100);
    return catalog.filter((p) => (p.name || '').toLowerCase().includes(q)).slice(0, 200);
  }, [catalog, pickerSearch]);

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Состав: {item.name}</DialogTitle>
          <DialogDescription>
            Цена: {price.toFixed(2)} {currency} · Источник себестоимости:{' '}
            <code className="text-xs">{costSource}</code>
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="py-10 text-center text-muted-foreground">Загрузка…</div>
        ) : (
          <div className="space-y-3">
            {ingredients.length === 0 && (
              <p className="text-sm text-muted-foreground">Ингредиентов пока нет.</p>
            )}
            {ingredients.map((ing, idx) => {
              const lc = lineCost(ing);
              return (
                <div key={idx} className="border rounded-md p-3 bg-muted/10 space-y-2" data-testid={`ingredient-row-${idx}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="font-medium truncate">{ing.name}</div>
                      <div className="text-xs text-muted-foreground">
                        ID: {ing.caffesta_product_id} · unit_cost: {Number(ing.unit_cost).toFixed(2)} {currency}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => removeIng(idx)} data-testid={`remove-ingredient-${idx}`}>
                      <Trash2 className="w-4 h-4 text-rose-500" />
                    </Button>
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    <div>
                      <Label className="text-xs">Кол-во</Label>
                      <Input
                        type="number"
                        step="any"
                        value={ing.qty}
                        onChange={(e) => updateIng(idx, { qty: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Единица</Label>
                      <Input
                        value={ing.unit || ''}
                        placeholder="г, мл, шт"
                        onChange={(e) => updateIng(idx, { unit: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Множитель</Label>
                      <Input
                        type="number"
                        step="any"
                        value={ing.unit_factor}
                        onChange={(e) => updateIng(idx, { unit_factor: e.target.value })}
                        title="Коэффициент пересчёта к единице Caffesta (1 для шт, 0.001 для г если Caffesta хранит кг)"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">Строка, {currency}</Label>
                      <div className="h-10 flex items-center px-3 text-sm font-medium tabular-nums">
                        {lc.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}

            <Button variant="outline" className="w-full" onClick={() => setPickerOpen(true)} data-testid="add-ingredient-btn">
              <Plus className="w-4 h-4 mr-2" /> Добавить ингредиент из Caffesta
            </Button>

            {/* Totals */}
            <div className="mt-2 rounded-md bg-muted/40 p-3 grid grid-cols-3 gap-3 text-sm">
              <div>
                <div className="text-xs text-muted-foreground">Итого себест.</div>
                <div className="text-lg font-semibold tabular-nums">{total.toFixed(2)} {currency}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Маржа</div>
                <div className="text-lg font-semibold tabular-nums">
                  {price > 0 ? `${(price - total).toFixed(2)} ${currency}` : '—'}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Маржа %</div>
                <div className={`text-lg tabular-nums ${marginClass(marginPct)}`}>
                  {marginPct != null ? `${marginPct.toFixed(1)}%` : '—'}
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={saving}>
            <X className="w-4 h-4 mr-2" /> Отмена
          </Button>
          <Button onClick={save} disabled={saving} className="bg-mint-500 hover:bg-mint-600 text-white" data-testid="save-recipe-btn">
            {saving ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Сохраняем…</> : <><Save className="w-4 h-4 mr-2" />Сохранить</>}
          </Button>
        </DialogFooter>

        {/* Ingredient picker overlay */}
        {pickerOpen && (
          <Dialog open onOpenChange={(o) => { if (!o) setPickerOpen(false); }}>
            <DialogContent className="max-w-xl max-h-[80vh] overflow-hidden flex flex-col">
              <DialogHeader>
                <DialogTitle>Каталог Caffesta</DialogTitle>
                <DialogDescription>
                  Всего доступно: {catalog.length}. Выберите сырьё/полуфабрикат/тех.карту.
                </DialogDescription>
              </DialogHeader>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  autoFocus
                  placeholder="Введите название…"
                  value={pickerSearch}
                  onChange={(e) => setPickerSearch(e.target.value)}
                  className="pl-9"
                  data-testid="ingredient-picker-search"
                />
              </div>
              <div className="flex-1 overflow-y-auto divide-y">
                {pickerFiltered.length === 0 && (
                  <div className="text-center py-6 text-muted-foreground text-sm">Ничего не найдено</div>
                )}
                {pickerFiltered.map((p) => {
                  const source = costSource === 'self_cost' ? p.self_cost : (p.avgInvoicedSelfCost || p.self_cost);
                  return (
                    <button
                      key={p.caffesta_product_id}
                      type="button"
                      onClick={() => addIngredient(p)}
                      className="w-full text-left px-3 py-2 hover:bg-muted/40 flex items-start justify-between gap-3"
                      data-testid={`pick-${p.caffesta_product_id}`}
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{p.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {p.is_tech_card ? 'Тех. карта' : 'Сырьё'} · ID {p.caffesta_product_id}
                        </div>
                      </div>
                      <div className="text-sm tabular-nums whitespace-nowrap">
                        {Number(source || 0).toFixed(2)} {currency}
                      </div>
                    </button>
                  );
                })}
              </div>
            </DialogContent>
          </Dialog>
        )}
      </DialogContent>
    </Dialog>
  );
}

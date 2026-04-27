import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Check, X, Loader2, RefreshCw, Link as LinkIcon, Filter, Search } from 'lucide-react';
import { API, useApp } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export default function CaffestaMappingPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [meta, setMeta] = useState({ caffesta_count: 0, menu_count: 0, matched_count: 0 });
  const [threshold, setThreshold] = useState(60);
  const [onlyUnmapped, setOnlyUnmapped] = useState(true);
  const [selected, setSelected] = useState({});   // { menu_item_id: caffesta_product_id }
  const [applying, setApplying] = useState(false);
  const [search, setSearch] = useState('');
  const [includeEmpty, setIncludeEmpty] = useState(true);

  // Manual product picker state
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerForItem, setPickerForItem] = useState(null);
  const [allProducts, setAllProducts] = useState([]);
  const [productsLoaded, setProductsLoaded] = useState(false);
  const [pickerSearch, setPickerSearch] = useState('');

  const fetchSuggestions = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const r = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/caffesta/auto-mapping/suggest?threshold=${threshold}&only_unmapped=${onlyUnmapped}&include_empty=${includeEmpty}`,
        authHeaders,
      );
      setSuggestions(r.data.suggestions || []);
      setMeta({
        caffesta_count: r.data.caffesta_count || 0,
        menu_count: r.data.menu_count || 0,
        matched_count: r.data.matched_count || 0,
      });
      if (r.data.error) {
        toast.warning(r.data.error);
      }
      // Pre-select top candidate (>= 85)
      const pre = {};
      (r.data.suggestions || []).forEach((s) => {
        const best = s.candidates?.[0];
        if (best && best.score >= 85) pre[s.menu_item.id] = best.product_id;
      });
      setSelected(pre);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSuggestions(); /* eslint-disable-next-line */ }, [currentRestaurantId]);

  const toggle = (itemId, productId) => {
    setSelected((s) => ({
      ...s,
      [itemId]: s[itemId] === productId ? null : productId,
    }));
  };

  const skip = (itemId) => {
    setSelected((s) => {
      const next = { ...s };
      delete next[itemId];
      return next;
    });
  };

  const openManualPicker = async (item) => {
    setPickerForItem(item);
    setPickerSearch(item.name || '');
    setPickerOpen(true);
    if (!productsLoaded) {
      try {
        const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/caffesta/products`, authHeaders);
        setAllProducts(r.data?.data || []);
        setProductsLoaded(true);
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Не удалось загрузить товары Caffesta');
      }
    }
  };

  const pickManual = (product) => {
    if (!pickerForItem) return;
    setSelected((s) => ({ ...s, [pickerForItem.id]: product.product_id }));
    toast.success(`«${pickerForItem.name}» → ${product.title}`);
    setPickerOpen(false);
    setPickerForItem(null);
    setPickerSearch('');
  };

  const applyAll = async () => {
    const mappings = Object.entries(selected)
      .filter(([, v]) => v != null)
      .map(([menu_item_id, caffesta_product_id]) => ({ menu_item_id, caffesta_product_id }));
    if (mappings.length === 0) {
      toast.info('Ничего не выбрано');
      return;
    }
    setApplying(true);
    try {
      const r = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/caffesta/auto-mapping/apply`,
        { mappings },
        authHeaders,
      );
      toast.success(`Сохранено: ${r.data.updated} из ${r.data.total}`);
      fetchSuggestions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка применения');
    } finally {
      setApplying(false);
    }
  };

  const filtered = suggestions.filter((s) =>
    !search || s.menu_item.name.toLowerCase().includes(search.toLowerCase()),
  );

  const chosenCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="space-y-6" data-testid="caffesta-mapping-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-heading font-bold">Авто-маппинг блюд с Caffesta</h1>
          <p className="text-muted-foreground">
            Привязка позиций меню к товарам Caffesta по совпадению названий. После привязки импорт себестоимости, стоп-листа и отправка заказов заработают автоматически.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchSuggestions} disabled={loading} data-testid="refresh-suggestions">
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
            Обновить
          </Button>
          <Button className="bg-mint-500 hover:bg-mint-600 text-white" onClick={applyAll} disabled={applying || chosenCount === 0} data-testid="apply-mappings">
            {applying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Check className="w-4 h-4 mr-2" />}
            Применить ({chosenCount})
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card className="border-dashed">
        <CardContent className="p-4 flex flex-wrap items-end gap-4">
          <div className="space-y-1">
            <Label className="text-xs">Мин. совпадение (%)</Label>
            <div className="flex items-center gap-2">
              <input type="range" min="40" max="95" step="5" value={threshold} onChange={(e) => setThreshold(parseInt(e.target.value))} className="w-48" data-testid="threshold-slider" />
              <span className="font-mono w-10 text-center font-semibold">{threshold}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 pb-1">
            <input type="checkbox" id="only-unmapped" checked={onlyUnmapped} onChange={(e) => setOnlyUnmapped(e.target.checked)} data-testid="only-unmapped" />
            <Label htmlFor="only-unmapped" className="cursor-pointer text-sm">Только непривязанные</Label>
          </div>
          <div className="flex items-center gap-2 pb-1">
            <input type="checkbox" id="include-empty" checked={includeEmpty} onChange={(e) => setIncludeEmpty(e.target.checked)} data-testid="include-empty" />
            <Label htmlFor="include-empty" className="cursor-pointer text-sm">Показывать без совпадений</Label>
          </div>
          <div className="flex-1 min-w-[200px]">
            <Label className="text-xs">Поиск по названию</Label>
            <div className="flex items-center gap-1">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Название блюда..." data-testid="search-input" />
            </div>
          </div>
          <Button variant="outline" onClick={fetchSuggestions} disabled={loading}>Применить</Button>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Меню" value={meta.menu_count} />
        <StatCard label="Товаров в Caffesta" value={meta.caffesta_count} />
        <StatCard label="Найдено совпадений" value={meta.matched_count} />
        <StatCard label="Выбрано" value={chosenCount} accent />
      </div>

      {/* Table */}
      <Card className="border-none shadow-md">
        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <div className="py-12 text-center text-muted-foreground"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              {suggestions.length === 0 ? 'Нет совпадений. Понизьте порог или настройте Caffesta.' : 'Нет результатов по фильтру.'}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0 z-10">
                <tr className="text-left">
                  <th className="p-3 font-semibold w-2/5">Блюдо в меню</th>
                  <th className="p-3 font-semibold">Кандидаты из Caffesta (выберите)</th>
                  <th className="p-3 w-24"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => {
                  const currentSel = selected[s.menu_item.id];
                  return (
                    <tr key={s.menu_item.id} className="border-t border-border/50 align-top" data-testid={`mapping-row-${s.menu_item.id}`}>
                      <td className="p-3">
                        <p className="font-medium">{s.menu_item.name}</p>
                        {s.menu_item.current_caffesta_id && (
                          <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                            <LinkIcon className="w-3 h-3" /> Уже привязан: #{s.menu_item.current_caffesta_id}
                          </p>
                        )}
                      </td>
                      <td className="p-3">
                        <div className="space-y-1.5">
                          {s.candidates.length === 0 && (
                            <p className="text-xs text-muted-foreground italic">Авто-совпадений нет — подберите вручную →</p>
                          )}
                          {s.candidates.map((c, i) => {
                            const isSel = currentSel === c.product_id;
                            return (
                              <button
                                key={i}
                                onClick={() => toggle(s.menu_item.id, c.product_id)}
                                className={`w-full text-left px-3 py-2 rounded-lg border transition-all ${
                                  isSel
                                    ? 'border-mint-500 bg-mint-500/10 ring-1 ring-mint-500'
                                    : 'border-border hover:border-mint-500/50'
                                }`}
                                data-testid={`candidate-${s.menu_item.id}-${i}`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-medium truncate">{c.title}</span>
                                  <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className="text-xs text-muted-foreground">#{c.product_id} · {c.price} BYN</span>
                                    <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                                      c.score >= 85 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' :
                                      c.score >= 70 ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' :
                                      'bg-muted text-muted-foreground'
                                    }`}>{c.score}%</span>
                                    {isSel && <Check className="w-4 h-4 text-mint-500" />}
                                  </div>
                                </div>
                              </button>
                            );
                          })}
                          {currentSel && !s.candidates.some(c => c.product_id === currentSel) && (
                            <div className="px-3 py-2 rounded-lg border border-mint-500 bg-mint-500/10 text-sm flex items-center justify-between">
                              <span>✓ Выбран ID #{currentSel} (ручной)</span>
                              <button onClick={() => toggle(s.menu_item.id, currentSel)} className="text-xs text-muted-foreground hover:text-foreground">отменить</button>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="p-3 text-right space-y-1">
                        <Button size="sm" variant="outline" onClick={() => openManualPicker(s.menu_item)} data-testid={`manual-${s.menu_item.id}`} className="w-full">
                          <Search className="w-4 h-4 mr-1" /> Найти вручную
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => skip(s.menu_item.id)} data-testid={`skip-${s.menu_item.id}`} className="w-full">
                          <X className="w-4 h-4 mr-1" /> Пропустить
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Manual product picker */}
      <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Выберите товар Caffesta для «{pickerForItem?.name}»</DialogTitle>
          </DialogHeader>
          <div className="flex items-center gap-2 pt-2">
            <Search className="w-4 h-4 text-muted-foreground" />
            <Input
              autoFocus
              placeholder="Начните вводить название..."
              value={pickerSearch}
              onChange={(e) => setPickerSearch(e.target.value)}
              data-testid="picker-search"
            />
          </div>
          <div className="overflow-y-auto flex-1 -mx-6 px-6 space-y-1">
            {!productsLoaded ? (
              <div className="py-8 text-center text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin mx-auto" /></div>
            ) : (
              (() => {
                const q = pickerSearch.trim().toLowerCase();
                const filtered = allProducts
                  .filter(p => !q || (p.title || '').toLowerCase().includes(q))
                  .slice(0, 100);
                if (filtered.length === 0) {
                  return <p className="py-6 text-center text-sm text-muted-foreground">Не найдено. Попробуйте другой запрос.</p>;
                }
                return filtered.map((p) => (
                  <button
                    key={p.product_id}
                    onClick={() => pickManual(p)}
                    className="w-full flex items-center justify-between text-left p-3 rounded-lg border border-border hover:border-mint-500 hover:bg-mint-500/5 transition-all"
                    data-testid={`picker-product-${p.product_id}`}
                  >
                    <span className="font-medium truncate">{p.title}</span>
                    <span className="text-xs text-muted-foreground flex-shrink-0">#{p.product_id} · {p.price} BYN · {p.type}</span>
                  </button>
                ));
              })()
            )}
          </div>
          <p className="text-xs text-muted-foreground pt-2 border-t border-border">
            Показано до 100 товаров. Уточните поиск, если нужный товар не виден.
          </p>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <Card className="border-none shadow-sm">
      <CardContent className="p-3">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className={`text-2xl font-heading font-bold ${accent ? 'text-mint-500' : ''}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

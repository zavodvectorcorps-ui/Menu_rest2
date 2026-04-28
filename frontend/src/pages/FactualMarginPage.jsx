import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Loader2, TrendingUp, TrendingDown, Package, DollarSign, RefreshCw, Download, Info } from 'lucide-react';
import { API, useApp } from '@/App';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';

export default function FactualMarginPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState('30');
  const [data, setData] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // all | critical | warning | ok

  const fetchData = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/costs/factual-margin?days=${days}`, authHeaders);
      setData(r.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); /* eslint-disable-next-line */ }, [currentRestaurantId, days]);

  const statusOf = (m) => {
    if (m == null) return 'nodata';
    if (m < 20) return 'critical';
    if (m < 30) return 'warning';
    return 'ok';
  };

  const filtered = (data?.items || []).filter(i => {
    if (filter !== 'all' && statusOf(i.margin_pct) !== filter) return false;
    if (search && !(i.title || '').toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const exportCsv = () => {
    if (!data) return;
    const rows = [
      ['Товар', 'ID', 'Продано шт', 'Выручка', 'Себестоимость', 'Маржа (BYN)', 'Маржа %', 'Ср. цена', 'Ср. себест.'],
      ...filtered.map(i => [
        (i.title || '').replace(/"/g, '""'),
        i.product_id,
        i.qty,
        i.revenue,
        i.cost,
        i.margin_abs,
        i.margin_pct ?? '',
        i.avg_price ?? '',
        i.avg_cost ?? '',
      ]),
    ];
    const csv = rows.map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `factual-margin-${data.period.start}_${data.period.end}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="factual-margin-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-heading font-bold">Фактическая маржа по продажам</h1>
          <p className="text-muted-foreground max-w-3xl">
            Реальная маржа за период — посчитана из чеков Caffesta по формуле
            <span className="font-mono mx-1 text-xs px-2 py-0.5 rounded bg-muted">(выручка − себестоимость по тех.картам) / выручка</span>.
            Учитывается реальный расход продуктов.
          </p>
        </div>
        <div className="flex gap-2 items-end">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Период</label>
            <Select value={days} onValueChange={setDays}>
              <SelectTrigger className="w-32" data-testid="days-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 день</SelectItem>
                <SelectItem value="7">7 дней</SelectItem>
                <SelectItem value="14">14 дней</SelectItem>
                <SelectItem value="30">30 дней</SelectItem>
                <SelectItem value="60">60 дней</SelectItem>
                <SelectItem value="90">90 дней</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" onClick={fetchData} disabled={loading} data-testid="refresh">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          </Button>
          <Button variant="outline" onClick={exportCsv} disabled={!data || !data.items?.length} data-testid="export-csv">
            <Download className="w-4 h-4 mr-2" /> CSV
          </Button>
        </div>
      </div>

      {/* Summary */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <StatCard icon={<Package className="w-4 h-4" />} label="Товаров продано" value={data.summary.products_count} />
          <StatCard icon={<DollarSign className="w-4 h-4" />} label="Выручка" value={`${data.summary.total_revenue} BYN`} />
          <StatCard icon={<TrendingDown className="w-4 h-4" />} label="Себестоимость" value={`${data.summary.total_cost} BYN`} />
          <StatCard icon={<TrendingUp className="w-4 h-4 text-emerald-500" />} label="Маржа абс." value={`${data.summary.total_margin_abs} BYN`} accent="emerald" />
          <StatCard icon={<TrendingUp className={`w-4 h-4 ${data.summary.total_margin_pct >= 30 ? 'text-emerald-500' : 'text-amber-500'}`} />} label="Маржа %" value={`${data.summary.total_margin_pct}%`} accent={data.summary.total_margin_pct >= 30 ? 'emerald' : 'amber'} />
        </div>
      )}

      {/* Filters */}
      <Card className="border-dashed">
        <CardContent className="p-4 flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px] space-y-1">
            <label className="text-xs text-muted-foreground">Поиск по названию</label>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Название товара..." data-testid="search-input" />
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {[
              { v: 'all', label: 'Все' },
              { v: 'critical', label: 'Критично <20%' },
              { v: 'warning', label: 'Снижена <30%' },
              { v: 'ok', label: 'Норма' },
              { v: 'nodata', label: 'Без тех.карт' },
            ].map(f => (
              <Button
                key={f.v}
                size="sm"
                variant={filter === f.v ? 'default' : 'outline'}
                className={filter === f.v ? 'bg-mint-500 hover:bg-mint-600 text-white' : ''}
                onClick={() => setFilter(f.v)}
                data-testid={`filter-${f.v}`}
              >
                {f.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tip */}
      <Card className="border-dashed bg-blue-500/5 border-blue-500/30">
        <CardContent className="p-3 flex gap-2 items-start text-sm">
          <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <div>
            <p><b>Чем отличается от «Контроля цен»?</b></p>
            <p className="text-muted-foreground text-xs mt-1">
              «Контроль цен» считает <b>нормативную</b> маржу (цена - себестоимость карточки). Эта страница показывает <b>фактическую</b> — как реально списались продукты по тех.картам Caffesta. Разница покажет: воровство, перерасход, скидки и акции, бракованные блюда.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="border-none shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {filtered.length} {filtered.length === 1 ? 'товар' : 'товаров'} (сортировка от худшей маржи)
          </CardTitle>
          <CardDescription>
            Период: {data?.period.start} — {data?.period.end}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <div className="py-12 text-center"><Loader2 className="w-6 h-6 animate-spin mx-auto text-mint-500" /></div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              {data?.items?.length ? 'Нет товаров по фильтру' : 'За период нет продаж'}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0 z-10">
                <tr className="text-left">
                  <th className="p-3 font-semibold">Товар</th>
                  <th className="p-3 font-semibold text-right">Продано</th>
                  <th className="p-3 font-semibold text-right">Выручка</th>
                  <th className="p-3 font-semibold text-right">Себест.</th>
                  <th className="p-3 font-semibold text-right">Маржа BYN</th>
                  <th className="p-3 font-semibold text-right">Маржа %</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((i) => {
                  const s = statusOf(i.margin_pct);
                  return (
                    <tr key={i.product_id} className="border-t border-border/50" data-testid={`row-${i.product_id}`}>
                      <td className="p-3">
                        <p className="font-medium">{i.title}</p>
                        <p className="text-xs text-muted-foreground">
                          #{i.product_id}
                          {i.avg_price && ` · ср.цена ${i.avg_price}`}
                          {i.avg_cost > 0 && ` · ср.себест ${i.avg_cost}`}
                        </p>
                      </td>
                      <td className="p-3 text-right font-mono">{i.qty}</td>
                      <td className="p-3 text-right font-mono">{i.revenue}</td>
                      <td className="p-3 text-right font-mono text-muted-foreground">{i.cost || '—'}</td>
                      <td className={`p-3 text-right font-mono ${i.margin_abs < 0 ? 'text-red-500' : ''}`}>
                        {i.margin_abs}
                      </td>
                      <td className="p-3 text-right">
                        {i.margin_pct == null ? (
                          <Badge variant="outline" className="text-xs">нет тех.карты</Badge>
                        ) : (
                          <Badge className={`font-mono ${
                            s === 'critical' ? 'bg-red-500/20 text-red-700 dark:text-red-300 hover:bg-red-500/20' :
                            s === 'warning' ? 'bg-amber-500/20 text-amber-700 dark:text-amber-300 hover:bg-amber-500/20' :
                            'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20'
                          }`}>
                            {i.margin_pct}%
                          </Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ icon, label, value, accent }) {
  const color = accent === 'emerald' ? 'text-emerald-500' : accent === 'amber' ? 'text-amber-500' : '';
  return (
    <Card className="border-none shadow-sm">
      <CardContent className="p-3">
        <div className={`flex items-center gap-1 text-xs text-muted-foreground mb-1`}>
          {icon}
          {label}
        </div>
        <p className={`text-xl font-heading font-bold ${color}`}>{value}</p>
      </CardContent>
    </Card>
  );
}

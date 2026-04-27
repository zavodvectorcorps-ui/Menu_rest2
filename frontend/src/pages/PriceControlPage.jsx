import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { TrendingDown, Upload, RefreshCw, AlertTriangle, CheckCircle, DollarSign, Filter, Edit2, Loader2, Download, Settings as SettingsIcon, Save } from 'lucide-react';
import { useApp } from '@/App';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const STATUS_META = {
  ok:         { label: 'Норма',      color: 'text-emerald-600 bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-300' },
  warning:    { label: 'Снижена',    color: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30 dark:text-amber-300' },
  critical:   { label: 'Критично',   color: 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-300' },
  'no-cost':  { label: 'Нет данных', color: 'text-muted-foreground bg-muted' },
  'no-price': { label: 'Нет цены',   color: 'text-muted-foreground bg-muted' },
};

export default function PriceControlPage() {
  const { currentRestaurantId, settings, updateSettings } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } };

  const [data, setData] = useState({ items: [], summary: {} });
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState({ cost_price: '', margin_threshold: '' });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsForm, setSettingsForm] = useState({});
  const [savingSettings, setSavingSettings] = useState(false);

  const fetchData = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/costs/analysis`, authHeaders);
      setData(r.data);
    } catch {
      toast.error('Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); /* eslint-disable-next-line */ }, [currentRestaurantId]);
  useEffect(() => { setSettingsForm(settings || {}); }, [settings]);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const r = await axios.post(`${API}/restaurants/${currentRestaurantId}/costs/upload`, fd, {
        headers: { ...authHeaders.headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Сопоставлено: ${r.data.matched} из ${r.data.total}`);
      if (r.data.unmatched?.length > 0) {
        toast.warning(`Не найдено: ${r.data.unmatched.slice(0, 5).join(', ')}${r.data.unmatched.length > 5 ? '...' : ''}`, { duration: 8000 });
      }
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleImportCaffesta = async () => {
    setImporting(true);
    try {
      const r = await axios.post(`${API}/restaurants/${currentRestaurantId}/costs/import-caffesta`, {}, authHeaders);
      toast.success(r.data.message || `Импортировано: ${r.data.matched} из ${r.data.total}`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка импорта');
    } finally {
      setImporting(false);
    }
  };

  const openEdit = (item) => {
    setEditingItem(item);
    setForm({
      cost_price: item.cost_price ?? '',
      margin_threshold: item.threshold_source === 'item' ? item.threshold : '',
    });
  };

  const saveEdit = async () => {
    try {
      const payload = {};
      if (form.cost_price !== '') payload.cost_price = parseFloat(form.cost_price);
      payload.margin_threshold = form.margin_threshold === '' ? null : parseInt(form.margin_threshold);
      await axios.put(`${API}/restaurants/${currentRestaurantId}/menu-items/${editingItem.id}/cost`, payload, authHeaders);
      toast.success('Сохранено');
      setEditingItem(null);
      fetchData();
    } catch {
      toast.error('Ошибка сохранения');
    }
  };

  const saveSettings = async () => {
    setSavingSettings(true);
    try {
      await updateSettings({
        margin_threshold_default: parseInt(settingsForm.margin_threshold_default) || 30,
        margin_alerts_enabled: !!settingsForm.margin_alerts_enabled,
        margin_alerts_bot_token: settingsForm.margin_alerts_bot_token || '',
        margin_alerts_chat_id: settingsForm.margin_alerts_chat_id || '',
      });
      toast.success('Настройки сохранены');
      setSettingsOpen(false);
      fetchData();
    } catch {
      toast.error('Ошибка сохранения');
    } finally {
      setSavingSettings(false);
    }
  };

  // Filtering
  const categories = Array.from(new Set(data.items.map(i => i.category_name).filter(Boolean))).sort();
  const filtered = data.items.filter(i => {
    if (categoryFilter !== 'all' && i.category_name !== categoryFilter) return false;
    if (filter === 'all') return true;
    return i.status === filter;
  });

  const summary = data.summary || {};

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="price-control-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground">Контроль цен и маржинальности</h1>
          <p className="text-muted-foreground">Загрузка себестоимости и анализ маржи каждого блюда</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" className="rounded-full gap-2" onClick={() => setSettingsOpen(true)} data-testid="open-pc-settings">
            <SettingsIcon className="w-4 h-4" />Настройки
          </Button>
          <Button variant="outline" className="rounded-full gap-2" onClick={handleImportCaffesta} disabled={importing} data-testid="import-caffesta-btn">
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Импорт из Caffesta
          </Button>
          <input type="file" accept=".xlsx,.xls,.csv" id="cost-upload" className="hidden" onChange={handleUpload} data-testid="cost-upload-input" />
          <Button className="rounded-full gap-2 bg-mint-500 hover:bg-mint-600 text-white" onClick={() => document.getElementById('cost-upload').click()} disabled={uploading} data-testid="upload-costs-btn">
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            Загрузить файл
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <SummaryCard label="Всего позиций" value={summary.total ?? '—'} icon={<DollarSign className="w-4 h-4" />} color="text-foreground" />
        <SummaryCard label="С себестоимостью" value={summary.with_cost ?? '—'} icon={<CheckCircle className="w-4 h-4" />} color="text-emerald-500" />
        <SummaryCard label="Средняя маржа" value={summary.avg_margin !== null && summary.avg_margin !== undefined ? `${summary.avg_margin}%` : '—'} icon={<TrendingDown className="w-4 h-4" />} color="text-mint-500" />
        <SummaryCard label="Снижена" value={summary.warning ?? 0} icon={<AlertTriangle className="w-4 h-4" />} color="text-amber-500" />
        <SummaryCard label="Критично" value={summary.critical ?? 0} icon={<AlertTriangle className="w-4 h-4" />} color="text-red-500" />
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <Filter className="w-4 h-4 text-muted-foreground" />
        {['all', 'critical', 'warning', 'ok', 'no-cost'].map(s => (
          <Button key={s} size="sm" variant={filter === s ? 'default' : 'outline'} className={filter === s ? 'bg-mint-500 hover:bg-mint-600 rounded-full' : 'rounded-full'} onClick={() => setFilter(s)} data-testid={`filter-${s}`}>
            {s === 'all' ? 'Все' : STATUS_META[s]?.label || s}
          </Button>
        ))}
        {categories.length > 0 && (
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="h-9 px-3 rounded-full border border-border bg-background text-sm ml-auto">
            <option value="all">Все категории</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>

      {/* Table */}
      <Card className="border-none shadow-md">
        <CardContent className="p-0 overflow-x-auto">
          {loading ? (
            <div className="py-12 text-center text-muted-foreground"><Loader2 className="w-6 h-6 animate-spin mx-auto" /></div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">Нет данных по выбранным фильтрам</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0">
                <tr className="text-left">
                  <th className="p-3 font-semibold">Блюдо</th>
                  <th className="p-3 font-semibold">Категория</th>
                  <th className="p-3 font-semibold text-right">Цена</th>
                  <th className="p-3 font-semibold text-right">Себестоимость</th>
                  <th className="p-3 font-semibold text-right">Маржа</th>
                  <th className="p-3 font-semibold text-center">Порог</th>
                  <th className="p-3 font-semibold text-center">Статус</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const meta = STATUS_META[item.status] || STATUS_META['no-cost'];
                  return (
                    <tr key={item.id} className="border-t border-border/50 hover:bg-muted/30" data-testid={`cost-row-${item.id}`}>
                      <td className="p-3 font-medium">{item.name}</td>
                      <td className="p-3 text-muted-foreground">{item.category_name || '—'}</td>
                      <td className="p-3 text-right">{item.price ?? '—'}</td>
                      <td className="p-3 text-right">
                        {item.cost_price != null ? (
                          <span>{item.cost_price}{item.cost_source === 'caffesta' && <span className="ml-1 text-[10px] text-mint-500">C</span>}</span>
                        ) : <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="p-3 text-right font-semibold">
                        {item.margin_pct != null ? `${item.margin_pct}%` : <span className="text-muted-foreground">—</span>}
                      </td>
                      <td className="p-3 text-center text-xs">
                        {item.threshold}%
                        <div className="text-[10px] text-muted-foreground">
                          {item.threshold_source === 'item' ? 'своё' : item.threshold_source === 'category' ? 'катег.' : 'общий'}
                        </div>
                      </td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${meta.color}`}>
                          {meta.label}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <Button size="icon" variant="ghost" onClick={() => openEdit(item)} data-testid={`edit-cost-${item.id}`}>
                          <Edit2 className="w-4 h-4" />
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

      {/* Edit dialog */}
      <Dialog open={!!editingItem} onOpenChange={(o) => { if (!o) setEditingItem(null); }}>
        <DialogContent data-testid="edit-cost-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">{editingItem?.name}</DialogTitle>
            <DialogDescription>
              Цена: <strong>{editingItem?.price}</strong>. Ручная правка источника: <code>manual</code>.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Себестоимость</Label>
              <Input type="number" step="0.01" value={form.cost_price} onChange={(e) => setForm({ ...form, cost_price: e.target.value })} placeholder="0.00" data-testid="edit-cost-input" />
            </div>
            <div className="space-y-2">
              <Label>Индивидуальный порог маржи (%)</Label>
              <Input type="number" step="1" value={form.margin_threshold} onChange={(e) => setForm({ ...form, margin_threshold: e.target.value })} placeholder="оставить пустым = порог категории/общий" data-testid="edit-threshold-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingItem(null)}>Отмена</Button>
            <Button className="bg-mint-500 hover:bg-mint-600 text-white" onClick={saveEdit} data-testid="save-cost-btn">
              <Save className="w-4 h-4 mr-2" />Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Global settings dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent data-testid="pc-settings-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">Настройки контроля цен</DialogTitle>
            <DialogDescription>
              Общий порог маржи и Telegram-алерты при падении ниже критической отметки (&lt; порог – 5%).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Общий порог маржи (%)</Label>
              <Input type="number" step="1" value={settingsForm.margin_threshold_default || 30} onChange={(e) => setSettingsForm({ ...settingsForm, margin_threshold_default: e.target.value })} data-testid="default-threshold-input" />
              <p className="text-xs text-muted-foreground">Применяется, если для категории/позиции не задан свой порог.</p>
            </div>
            <div className="flex items-center justify-between border-t border-border pt-4">
              <Label className="font-medium">Telegram-алерты</Label>
              <Switch checked={!!settingsForm.margin_alerts_enabled} onCheckedChange={(v) => setSettingsForm({ ...settingsForm, margin_alerts_enabled: v })} data-testid="alerts-enabled-switch" />
            </div>
            {settingsForm.margin_alerts_enabled && (
              <>
                <div className="space-y-2">
                  <Label>Bot Token (от @BotFather)</Label>
                  <Input value={settingsForm.margin_alerts_bot_token || ''} onChange={(e) => setSettingsForm({ ...settingsForm, margin_alerts_bot_token: e.target.value })} placeholder="123456:ABC..." data-testid="alerts-token-input" />
                </div>
                <div className="space-y-2">
                  <Label>Chat ID</Label>
                  <Input value={settingsForm.margin_alerts_chat_id || ''} onChange={(e) => setSettingsForm({ ...settingsForm, margin_alerts_chat_id: e.target.value })} placeholder="-100123456789" data-testid="alerts-chat-input" />
                  <p className="text-xs text-muted-foreground">Напишите боту любое сообщение, потом получите chat_id через https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</p>
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSettingsOpen(false)}>Отмена</Button>
            <Button className="bg-mint-500 hover:bg-mint-600 text-white" onClick={saveSettings} disabled={savingSettings} data-testid="save-pc-settings-btn">
              {savingSettings ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Help */}
      <Card className="border-dashed border-border bg-muted/30">
        <CardContent className="p-4 text-sm text-muted-foreground">
          <p className="font-medium text-foreground mb-1"><Download className="w-4 h-4 inline mr-1" />Формат файла</p>
          <p>Excel (.xlsx) или CSV с двумя колонками: <b>«Название»</b> и <b>«Себестоимость»</b>. Сопоставление — по нормализованному названию блюда (регистр, знаки игнорируются). Для ресторанов с Caffesta — приоритет по ID товара.</p>
        </CardContent>
      </Card>
    </div>
  );
}

function SummaryCard({ label, value, icon, color }) {
  return (
    <Card className="border-none shadow-sm">
      <CardContent className="p-3">
        <div className={`flex items-center gap-1 text-xs mb-1 ${color}`}>
          {icon}
          <span>{label}</span>
        </div>
        <div className="text-2xl font-heading font-bold">{value}</div>
      </CardContent>
    </Card>
  );
}

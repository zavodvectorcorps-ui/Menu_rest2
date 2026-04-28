import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Plug, PlugZap, Save, TestTube, DollarSign, ShoppingCart, TrendingUp, Award, Users, FileText, Filter, Plus, Trash2, Star, Clock, CalendarDays, Ban, Percent } from 'lucide-react';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

export default function CaffestaPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState({ account_name: '', api_key: '', pos_id: '', payment_id: '1', payment_methods: [], enabled: false, admin_session_cookie: '' });
  const [connected, setConnected] = useState(false);

  // Analytics state
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsPeriod, setAnalyticsPeriod] = useState('30');

  // Time window state
  const [twLoading, setTwLoading] = useState(false);
  const [twData, setTwData] = useState(null);
  const [tw, setTw] = useState({ days: '30', day_type: 'all', time_from: '00:00', time_to: '23:59' });

  // Sales report state
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('7');
  const [reportCashier, setReportCashier] = useState('');

  // Digest state
  const [digestSettings, setDigestSettings] = useState({
    daily_digest_enabled: false,
    daily_digest_bot_token: '',
    daily_digest_chat_id: '',
    daily_digest_windows: [
      { name: 'Завтрак', time_from: '08:00', time_to: '12:00' },
      { name: 'Обед', time_from: '12:00', time_to: '16:00' },
      { name: 'Вечер', time_from: '18:00', time_to: '23:00' },
    ],
  });
  const [digestPreview, setDigestPreview] = useState('');
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestSaving, setDigestSaving] = useState(false);

  const fetchConfig = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/restaurants/${currentRestaurantId}/caffesta`, authHeaders);
      setConfig({
        account_name: resp.data.account_name || '',
        api_key: resp.data.api_key || '',
        pos_id: resp.data.pos_id ? String(resp.data.pos_id) : '',
        payment_id: resp.data.payment_id ? String(resp.data.payment_id) : '1',
        payment_methods: Array.isArray(resp.data.payment_methods) ? resp.data.payment_methods : [],
        enabled: resp.data.enabled || false,
        admin_session_cookie: resp.data.admin_session_cookie || '',
      });
      setConnected(!!resp.data.connected);
    } catch {
      // No config yet
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConfig(); }, [currentRestaurantId]);

  const saveConfig = async () => {
    setSaving(true);
    try {
      const cleanMethods = (config.payment_methods || [])
        .filter(m => m.name && m.payment_id !== '' && m.payment_id !== null && m.payment_id !== undefined)
        .map(m => ({ name: String(m.name).trim(), payment_id: parseInt(m.payment_id), is_default: !!m.is_default }));
      // ensure single default
      let hasDefault = false;
      for (const m of cleanMethods) {
        if (m.is_default && !hasDefault) hasDefault = true;
        else m.is_default = false;
      }
      if (cleanMethods.length > 0 && !hasDefault) cleanMethods[0].is_default = true;
      const payload = {
        account_name: config.account_name.trim(),
        api_key: config.api_key.trim(),
        pos_id: config.pos_id ? parseInt(config.pos_id) : null,
        payment_id: config.payment_id ? parseInt(config.payment_id) : 1,
        payment_methods: cleanMethods,
        enabled: config.enabled,
        admin_session_cookie: (config.admin_session_cookie || '').trim(),
      };
      await axios.put(`${API}/restaurants/${currentRestaurantId}/caffesta`, payload, authHeaders);
      toast.success('Настройки сохранены');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const addPaymentMethod = () => {
    setConfig({
      ...config,
      payment_methods: [
        ...(config.payment_methods || []),
        { name: '', payment_id: '', is_default: (config.payment_methods || []).length === 0 },
      ],
    });
  };
  const updatePaymentMethod = (idx, patch) => {
    const list = [...(config.payment_methods || [])];
    list[idx] = { ...list[idx], ...patch };
    if (patch.is_default) {
      list.forEach((m, i) => { if (i !== idx) m.is_default = false; });
    }
    setConfig({ ...config, payment_methods: list });
  };
  const removePaymentMethod = (idx) => {
    const list = (config.payment_methods || []).filter((_, i) => i !== idx);
    if (list.length > 0 && !list.some(m => m.is_default)) list[0].is_default = true;
    setConfig({ ...config, payment_methods: list });
  };

  const testConnection = async () => {
    setTesting(true);
    try {
      // Save first
      await saveConfig();
      const resp = await axios.post(`${API}/restaurants/${currentRestaurantId}/caffesta/test`, {}, authHeaders);
      if (resp.data.ok) {
        toast.success('Подключение к Caffesta успешно!');
        setConnected(true);
      } else {
        toast.error(resp.data.message || 'Ошибка подключения');
        setConnected(false);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка тестирования');
      setConnected(false);
    } finally {
      setTesting(false);
    }
  };

  const fetchAnalytics = async () => {
    if (!currentRestaurantId) return;
    setAnalyticsLoading(true);
    try {
      const resp = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/caffesta/analytics?days=${analyticsPeriod}`,
        authHeaders
      );
      setAnalytics(resp.data);
    } catch (err) {
      if (err.response?.status === 400) {
        toast.error('Caffesta не настроена или отключена');
      } else {
        toast.error('Ошибка загрузки аналитики');
      }
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    if (config.enabled && config.account_name && config.api_key) {
      fetchAnalytics();
    }
  }, [currentRestaurantId, analyticsPeriod, config.enabled]);

  const fetchReport = async () => {
    if (!currentRestaurantId) return;
    setReportLoading(true);
    try {
      let url = `${API}/restaurants/${currentRestaurantId}/caffesta/sales-report?days=${reportPeriod}`;
      if (reportCashier) url += `&cashier=${encodeURIComponent(reportCashier)}`;
      const resp = await axios.get(url, authHeaders);
      setReport(resp.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка загрузки отчёта');
    } finally {
      setReportLoading(false);
    }
  };

  const fetchTimeWindow = async () => {
    if (!currentRestaurantId) return;
    setTwLoading(true);
    try {
      const params = new URLSearchParams({
        days: tw.days,
        day_type: tw.day_type,
        time_from: tw.time_from,
        time_to: tw.time_to,
      });
      const resp = await axios.get(`${API}/restaurants/${currentRestaurantId}/caffesta/time-window?${params}`, authHeaders);
      setTwData(resp.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setTwLoading(false);
    }
  };

  const applyPreset = (preset) => {
    setTw(preset);
    setTimeout(fetchTimeWindow, 50);
  };

  const syncStopList = async () => {
    if (!currentRestaurantId) return;
    try {
      const r = await axios.post(`${API}/restaurants/${currentRestaurantId}/caffesta/stop-list/sync`, {}, authHeaders);
      const d = r.data;
      if (d.disabled_count > 0 || d.enabled_count > 0) {
        toast.success(`Стоп-лист синхронизирован: -${d.disabled_count}, +${d.enabled_count}`);
      } else {
        toast.success(`Стоп-лист синхронизирован. Изменений нет (проверено ${d.linked_items} привязанных позиций)`);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка синхронизации стоп-листа');
    }
  };

  // Digest: load/save settings
  const fetchDigestSettings = async () => {
    if (!currentRestaurantId) return;
    try {
      const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/settings`, authHeaders);
      const s = r.data || {};
      setDigestSettings({
        daily_digest_enabled: !!s.daily_digest_enabled,
        daily_digest_bot_token: s.daily_digest_bot_token || '',
        daily_digest_chat_id: s.daily_digest_chat_id || '',
        daily_digest_windows: Array.isArray(s.daily_digest_windows) && s.daily_digest_windows.length > 0
          ? s.daily_digest_windows
          : digestSettings.daily_digest_windows,
      });
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchDigestSettings(); /* eslint-disable-next-line */ }, [currentRestaurantId]);

  const saveDigestSettings = async () => {
    setDigestSaving(true);
    try {
      const windows = (digestSettings.daily_digest_windows || [])
        .filter((w) => w.name && w.time_from && w.time_to)
        .slice(0, 4);
      await axios.put(`${API}/restaurants/${currentRestaurantId}/settings`, {
        daily_digest_enabled: !!digestSettings.daily_digest_enabled,
        daily_digest_bot_token: digestSettings.daily_digest_bot_token || '',
        daily_digest_chat_id: digestSettings.daily_digest_chat_id || '',
        daily_digest_windows: windows,
      }, authHeaders);
      toast.success('Настройки дайджеста сохранены');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setDigestSaving(false);
    }
  };

  const loadDigestPreview = async () => {
    setDigestLoading(true);
    try {
      const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/digest/preview`, authHeaders);
      setDigestPreview(r.data?.text || '');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка предпросмотра');
    } finally {
      setDigestLoading(false);
    }
  };

  const sendDigestNow = async () => {
    try {
      await axios.post(`${API}/restaurants/${currentRestaurantId}/digest/send`, {}, authHeaders);
      toast.success('Дайджест отправлен в Telegram');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка отправки');
    }
  };

  const addDigestWindow = () => {
    if ((digestSettings.daily_digest_windows || []).length >= 4) return;
    setDigestSettings({
      ...digestSettings,
      daily_digest_windows: [...(digestSettings.daily_digest_windows || []), { name: '', time_from: '00:00', time_to: '01:00' }],
    });
  };
  const updateDigestWindow = (i, patch) => {
    const list = [...(digestSettings.daily_digest_windows || [])];
    list[i] = { ...list[i], ...patch };
    setDigestSettings({ ...digestSettings, daily_digest_windows: list });
  };
  const removeDigestWindow = (i) => {
    const list = (digestSettings.daily_digest_windows || []).filter((_, idx) => idx !== i);
    setDigestSettings({ ...digestSettings, daily_digest_windows: list });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-mint-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="caffesta-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-heading font-bold">Caffesta POS</h2>
          <p className="text-muted-foreground">Интеграция с кассовой системой</p>
        </div>
        <Badge variant={config.enabled ? "default" : "secondary"} className={config.enabled ? "bg-green-500/20 text-green-400 border-green-500/30" : ""}>
          {config.enabled ? "Активна" : "Отключена"}
        </Badge>
      </div>

      <Tabs defaultValue="settings">
        <TabsList data-testid="caffesta-tabs">
          <TabsTrigger value="settings" data-testid="tab-settings">Настройки</TabsTrigger>
          <TabsTrigger value="analytics" data-testid="tab-analytics">Аналитика POS</TabsTrigger>
          <TabsTrigger value="time-window" data-testid="tab-time-window">Сравнение по времени</TabsTrigger>
          <TabsTrigger value="report" data-testid="tab-report">Реализация</TabsTrigger>
          <TabsTrigger value="digest" data-testid="tab-digest">Дайджест 08:00</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plug className="w-5 h-5" />
                Подключение к Caffesta
              </CardTitle>
              <CardDescription>
                Данные для подключения можно получить в техподдержке Caffesta
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Account Name</Label>
                  <Input
                    value={config.account_name}
                    onChange={(e) => setConfig({ ...config, account_name: e.target.value })}
                    placeholder="my-organization"
                    data-testid="caffesta-account-name"
                  />
                  <p className="text-xs text-muted-foreground">Часть URL: {config.account_name || '...'}.caffesta.com</p>
                </div>
                <div className="space-y-2">
                  <Label>X-API-KEY</Label>
                  <Input
                    type="password"
                    value={config.api_key}
                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                    placeholder="Ваш API-ключ"
                    data-testid="caffesta-api-key"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>POS ID (точка продаж)</Label>
                  <Input
                    type="number"
                    value={config.pos_id}
                    onChange={(e) => setConfig({ ...config, pos_id: e.target.value })}
                    placeholder="2"
                    data-testid="caffesta-pos-id"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Payment ID по умолчанию</Label>
                  <Input
                    type="number"
                    value={config.payment_id}
                    onChange={(e) => setConfig({ ...config, payment_id: e.target.value })}
                    placeholder="1"
                    data-testid="caffesta-payment-id"
                  />
                  <p className="text-xs text-muted-foreground">Используется, если в списке ниже не задан вид по умолчанию</p>
                </div>
              </div>

              {/* Payment methods list */}
              <div className="space-y-2 pt-4 border-t border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Виды оплаты (из Caffesta)</Label>
                    <p className="text-xs text-muted-foreground">Добавьте все способы оплаты, которые используются в вашей кассе. Помеченный звёздочкой будет по умолчанию.</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addPaymentMethod} data-testid="add-payment-method">
                    <Plus className="w-4 h-4 mr-1" />Добавить вид
                  </Button>
                </div>
                <div className="space-y-2">
                  {(config.payment_methods || []).length === 0 && (
                    <p className="text-xs text-muted-foreground italic py-2">Нет добавленных видов оплаты. Добавьте, например: Наличные (1), Карта (2), Loyalty (3), Сертификат (4)…</p>
                  )}
                  {(config.payment_methods || []).map((m, i) => (
                    <div key={i} className="flex items-center gap-2" data-testid={`payment-method-${i}`}>
                      <Input
                        className="flex-1"
                        placeholder="Название (напр. Карта VISA)"
                        value={m.name || ''}
                        onChange={(e) => updatePaymentMethod(i, { name: e.target.value })}
                        data-testid={`payment-method-${i}-name`}
                      />
                      <Input
                        className="w-28"
                        type="number"
                        placeholder="ID"
                        value={m.payment_id ?? ''}
                        onChange={(e) => updatePaymentMethod(i, { payment_id: e.target.value })}
                        data-testid={`payment-method-${i}-id`}
                      />
                      <Button
                        type="button"
                        variant={m.is_default ? "default" : "outline"}
                        size="icon"
                        className={m.is_default ? "bg-amber-500 hover:bg-amber-600" : ""}
                        onClick={() => updatePaymentMethod(i, { is_default: true })}
                        title={m.is_default ? "По умолчанию" : "Сделать по умолчанию"}
                        data-testid={`payment-method-${i}-default`}
                      >
                        <Star className={`w-4 h-4 ${m.is_default ? 'fill-current' : ''}`} />
                      </Button>
                      <Button type="button" variant="ghost" size="icon" onClick={() => removePaymentMethod(i)} data-testid={`payment-method-${i}-remove`}>
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <div className="flex items-center gap-3">
                  <Switch
                    checked={config.enabled}
                    onCheckedChange={(v) => setConfig({ ...config, enabled: v })}
                    data-testid="caffesta-enabled-toggle"
                  />
                  <div>
                    <p className="text-sm font-medium">Автоматическая отправка заказов</p>
                    <p className="text-xs text-muted-foreground">Заказы с сайта автоматически отправляются на кассу</p>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-border/50 space-y-2">
                <Label htmlFor="admin-session-cookie" className="text-sm font-medium">PHPSESSID (cookie админки Caffesta)</Label>
                <Input
                  id="admin-session-cookie"
                  type="password"
                  placeholder="например: abcd1234ef5678..."
                  value={config.admin_session_cookie || ''}
                  onChange={(e) => setConfig({ ...config, admin_session_cookie: e.target.value })}
                  data-testid="caffesta-session-cookie-input"
                  autoComplete="off"
                />
                <p className="text-xs text-muted-foreground">
                  Опционально. Используется только для отображения <b>точного времени последних дозаказов</b> ("В работе"). API Caffesta не отдаёт это время.
                  Чтобы получить cookie: войдите в админку Caffesta в браузере → DevTools (F12) → Application/Cookies → скопируйте значение <code>PHPSESSID</code>.
                  Если cookie истечёт — приложение продолжит работать в обычном режиме.
                </p>
              </div>

              <div className="flex gap-3 pt-2 flex-wrap">
                <Button onClick={saveConfig} disabled={saving} data-testid="caffesta-save-btn">
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Сохранить
                </Button>
                <Button variant="outline" onClick={testConnection} disabled={testing || !config.account_name || !config.api_key} data-testid="caffesta-test-btn">
                  {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TestTube className="w-4 h-4 mr-2" />}
                  Проверить подключение
                </Button>
                <Button variant="outline" onClick={syncStopList} disabled={!config.enabled} data-testid="caffesta-sync-stop-list" title="Скрыть в меню позиции, помеченные в Caffesta как stop-list">
                  <Ban className="w-4 h-4 mr-2" />
                  Синхронизировать стоп-лист
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* How it works */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PlugZap className="w-5 h-5" />
                Как это работает
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-mint-500/20 text-mint-400 flex items-center justify-center text-xs font-bold">1</span>
                  <p>Клиент оформляет заказ через QR-меню вашего ресторана</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-mint-500/20 text-mint-400 flex items-center justify-center text-xs font-bold">2</span>
                  <p>Заказ автоматически отправляется на кассу Caffesta</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-mint-500/20 text-mint-400 flex items-center justify-center text-xs font-bold">3</span>
                  <p>Повар видит заказ на экране кухни, а вы — в личном кабинете и Telegram</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-mint-500/20 text-mint-400 flex items-center justify-center text-xs font-bold">4</span>
                  <p>Аналитика продаж из Caffesta доступна на вкладке «Аналитика POS»</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4 mt-4">
          {!config.enabled || !config.account_name ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Plug className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Настройте и включите интеграцию с Caffesta для доступа к аналитике POS</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Данные кассовой системы</h3>
                <div className="flex gap-2">
                  <Select value={analyticsPeriod} onValueChange={setAnalyticsPeriod}>
                    <SelectTrigger className="w-32" data-testid="caffesta-period-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">7 дней</SelectItem>
                      <SelectItem value="30">30 дней</SelectItem>
                      <SelectItem value="90">90 дней</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline" size="sm" onClick={fetchAnalytics} disabled={analyticsLoading} data-testid="caffesta-refresh-analytics">
                    {analyticsLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Обновить"}
                  </Button>
                </div>
              </div>

              {analyticsLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="w-6 h-6 animate-spin text-mint-500" />
                </div>
              ) : analytics ? (
                <>
                  {/* Summary cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <SummaryCard title="Выручка" value={`${analytics.totals.revenue} BYN`} icon={DollarSign} color="bg-green-500" />
                    <SummaryCard title="Продажи (шт)" value={analytics.totals.quantity} icon={ShoppingCart} color="bg-blue-500" />
                    <SummaryCard title="Средний чек" value={`${analytics.totals.avg_check} BYN`} icon={TrendingUp} color="bg-amber-500" />
                    <SummaryCard title="Скидки" value={`${analytics.totals.discount} BYN`} icon={Award} color="bg-purple-500" />
                  </div>

                  {/* Payment breakdown */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Оплата по типам</CardTitle>
                      <CardDescription>Все использованные способы оплаты за период</CardDescription>
                    </CardHeader>
                    <CardContent>
                      {analytics.payments?.length > 0 ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {analytics.payments.map((p, i) => (
                            <div key={i} className="p-3 rounded-lg bg-muted/50" data-testid={`payment-type-${i}`}>
                              <p className="text-xs text-muted-foreground truncate">{p.name}</p>
                              <p className="text-xl font-bold">{p.amount} BYN</p>
                              <p className="text-xs text-muted-foreground">{p.count} чек.</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="p-3 rounded-lg bg-muted/50">
                            <p className="text-xs text-muted-foreground">Наличные</p>
                            <p className="text-xl font-bold">{analytics.totals.cash} BYN</p>
                          </div>
                          <div className="p-3 rounded-lg bg-muted/50">
                            <p className="text-xs text-muted-foreground">Карта</p>
                            <p className="text-xl font-bold">{analytics.totals.card} BYN</p>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Top products */}
                  {analytics.top_products?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Топ продаж</CardTitle>
                        <CardDescription>Самые продаваемые позиции за период</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {analytics.top_products.map((p, i) => (
                            <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                              <div className="flex items-center gap-3">
                                <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">{i + 1}</span>
                                <span className="text-sm" data-testid={`top-product-${i}`}>{p.name}</span>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span>{p.qty} шт</span>
                                <span className="font-medium text-foreground">{p.revenue} BYN</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Нажмите «Обновить» для загрузки данных из Caffesta
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* Time Window Tab */}
        <TabsContent value="time-window" className="space-y-4 mt-4">
          {!config.enabled || !config.account_name ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Plug className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Настройте и включите интеграцию с Caffesta для анализа по часам</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Clock className="w-5 h-5" /> Продажи в определённое время
                  </CardTitle>
                  <CardDescription>
                    Фильтр по дням недели и диапазону часов. Полезно, чтобы оценить «ночные» или «ланчевые» смены.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Presets */}
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => applyPreset({ days: '30', day_type: 'mon_thu', time_from: '00:00', time_to: '02:00' })} data-testid="preset-monthu-night">
                      <CalendarDays className="w-3.5 h-3.5 mr-1" /> Пн–Чт 00:00–02:00
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => applyPreset({ days: '30', day_type: 'fri', time_from: '20:00', time_to: '02:00' })} data-testid="preset-fri-night">
                      <CalendarDays className="w-3.5 h-3.5 mr-1" /> Пятница 20:00–02:00
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => applyPreset({ days: '30', day_type: 'sat', time_from: '03:00', time_to: '06:00' })} data-testid="preset-sat-night">
                      <CalendarDays className="w-3.5 h-3.5 mr-1" /> Суббота 03:00–06:00
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => applyPreset({ days: '30', day_type: 'sun', time_from: '12:00', time_to: '15:00' })} data-testid="preset-sun-lunch">
                      <CalendarDays className="w-3.5 h-3.5 mr-1" /> Воскресенье 12:00–15:00
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-full" onClick={() => applyPreset({ days: '30', day_type: 'weekend', time_from: '12:00', time_to: '15:00' })} data-testid="preset-weekend-lunch">
                      <CalendarDays className="w-3.5 h-3.5 mr-1" /> Выходные 12:00–15:00
                    </Button>
                  </div>

                  {/* Custom filters */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-3 border-t border-border/50">
                    <div className="space-y-1">
                      <Label className="text-xs">Период</Label>
                      <Select value={tw.days} onValueChange={(v) => setTw({ ...tw, days: v })}>
                        <SelectTrigger data-testid="tw-days"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="7">7 дней</SelectItem>
                          <SelectItem value="14">14 дней</SelectItem>
                          <SelectItem value="30">30 дней</SelectItem>
                          <SelectItem value="60">60 дней</SelectItem>
                          <SelectItem value="90">90 дней</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">Дни</Label>
                      <Select value={tw.day_type} onValueChange={(v) => setTw({ ...tw, day_type: v })}>
                        <SelectTrigger data-testid="tw-day-type"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Все дни</SelectItem>
                          <SelectItem value="weekday">Будни (Пн–Пт)</SelectItem>
                          <SelectItem value="weekend">Выходные (Сб, Вс)</SelectItem>
                          <SelectItem value="mon_thu">Пн–Чт</SelectItem>
                          <SelectItem value="mon">Понедельник</SelectItem>
                          <SelectItem value="tue">Вторник</SelectItem>
                          <SelectItem value="wed">Среда</SelectItem>
                          <SelectItem value="thu">Четверг</SelectItem>
                          <SelectItem value="fri">Пятница</SelectItem>
                          <SelectItem value="sat">Суббота</SelectItem>
                          <SelectItem value="sun">Воскресенье</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">С (HH:MM)</Label>
                      <Input type="time" value={tw.time_from} onChange={(e) => setTw({ ...tw, time_from: e.target.value })} data-testid="tw-from" />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs">До (HH:MM)</Label>
                      <Input type="time" value={tw.time_to} onChange={(e) => setTw({ ...tw, time_to: e.target.value })} data-testid="tw-to" />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button onClick={fetchTimeWindow} disabled={twLoading} data-testid="tw-apply">
                      {twLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Filter className="w-4 h-4 mr-2" />}
                      Применить фильтр
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {twLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="w-6 h-6 animate-spin text-mint-500" />
                </div>
              ) : twData ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <SummaryCard title="Выручка" value={`${twData.totals.revenue} BYN`} icon={DollarSign} color="bg-green-500" />
                    <SummaryCard title="Чеков" value={twData.totals.receipts} icon={FileText} color="bg-blue-500" />
                    <SummaryCard title="Скидки за период" value={`${Math.abs(twData.totals.discount || 0).toFixed(2)} BYN`} icon={Percent} color="bg-rose-500" />
                    <SummaryCard title="Средний чек" value={`${twData.totals.avg_check} BYN`} icon={TrendingUp} color="bg-purple-500" />
                  </div>

                  {twData.payments?.length > 0 && (
                    <Card>
                      <CardHeader><CardTitle className="text-base">Оплата по типам</CardTitle></CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {twData.payments.map((p, i) => (
                            <div key={i} className="p-3 rounded-lg bg-muted/50">
                              <p className="text-xs text-muted-foreground truncate">{p.name}</p>
                              <p className="text-xl font-bold">{p.amount} BYN</p>
                              <p className="text-xs text-muted-foreground">{p.count} чек.</p>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {twData.top_products?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Топ позиций в окне</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {twData.top_products.slice(0, 15).map((p, i) => (
                            <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                              <div className="flex items-center gap-3">
                                <span className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">{i + 1}</span>
                                <span className="text-sm">{p.name}</span>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span>{p.qty} шт</span>
                                <span className="font-medium text-foreground">{p.revenue} BYN</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {twData.by_day?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">По дням</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border/50 text-muted-foreground">
                                <th className="text-left py-2 pr-4">Дата</th>
                                <th className="text-left py-2 px-3">День</th>
                                <th className="text-right py-2 px-3">Чеков</th>
                                <th className="text-right py-2 pl-3">Выручка</th>
                              </tr>
                            </thead>
                            <tbody>
                              {twData.by_day.map((d, i) => (
                                <tr key={i} className="border-b border-border/20">
                                  <td className="py-2 pr-4 font-medium">{d.date}</td>
                                  <td className="py-2 px-3 text-muted-foreground">{['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][d.weekday]}</td>
                                  <td className="text-right py-2 px-3">{d.receipts}</td>
                                  <td className="text-right py-2 pl-3 font-semibold">{d.revenue} BYN</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {twData.last_actions?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Clock className="w-4 h-4" />
                          {twData.open_orders_meta?.ok ? 'Последние дозаказы (В работе)' : 'Последние действия по чекам'}
                        </CardTitle>
                        <CardDescription>
                          {twData.open_orders_meta?.ok
                            ? 'Реальное время дозаказов из админки Caffesta (PHPSESSID)'
                            : 'Чеки, в которых были дозаказы или закрытие после открытия (топ-5 за период)'}
                          {twData.open_orders_meta?.reason === 'session_expired' && (
                            <span className="block text-amber-500 mt-1">⚠️ PHPSESSID истёк — обновите cookie в Настройках, чтобы видеть точное время дозаказов.</span>
                          )}
                          {twData.open_orders_meta?.reason === 'out_of_period' && (
                            <span className="block text-muted-foreground mt-1 text-xs">«В работе» доступно только когда период включает сегодня — показаны действия по чекам из выборки.</span>
                          )}
                          {twData.open_orders_meta?.reason === 'day_mismatch' && (
                            <span className="block text-muted-foreground mt-1 text-xs">Сегодняшний день не подходит под фильтр дней — показаны действия по чекам из выборки.</span>
                          )}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2">
                          {twData.last_actions.map((a, i) => (
                            <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0 text-sm">
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <span className="text-xs text-muted-foreground font-mono">#{a.id}</span>
                                <span className="text-muted-foreground">откр.</span>
                                <span className="font-medium">{a.opened_at.slice(11, 16)}</span>
                                <span className="text-muted-foreground">→ действие</span>
                                <span className="font-medium">{a.last_action_at.slice(11, 16)}</span>
                                {a.duration_min > 0 && <span className="text-xs text-muted-foreground">({a.duration_min} мин)</span>}
                                {a.table && <span className="text-xs text-muted-foreground">стол {a.table}</span>}
                              </div>
                              <span className="font-semibold whitespace-nowrap">{a.total} BYN</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {twData.totals.receipts === 0 && (
                    <Card><CardContent className="py-8 text-center text-muted-foreground">За указанный период и время продаж не найдено.</CardContent></Card>
                  )}
                </>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Выберите пресет или задайте собственный фильтр и нажмите «Применить»
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* Sales Report Tab */}
        <TabsContent value="report" className="space-y-4 mt-4">
          {!config.enabled || !config.account_name ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Plug className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Настройте и включите интеграцию с Caffesta для доступа к отчётам</p>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Отчёт реализации
                </h3>
                <div className="flex flex-wrap gap-2 items-center">
                  <Select value={reportPeriod} onValueChange={setReportPeriod}>
                    <SelectTrigger className="w-28" data-testid="report-period-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Сегодня</SelectItem>
                      <SelectItem value="7">7 дней</SelectItem>
                      <SelectItem value="14">14 дней</SelectItem>
                      <SelectItem value="30">30 дней</SelectItem>
                    </SelectContent>
                  </Select>
                  {report?.cashiers?.length > 0 && (
                    <Select value={reportCashier} onValueChange={setReportCashier}>
                      <SelectTrigger className="w-44" data-testid="report-cashier-select">
                        <Filter className="w-3.5 h-3.5 mr-1" />
                        <SelectValue placeholder="Все официанты" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">Все официанты</SelectItem>
                        {report.cashiers.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  <Button variant="outline" size="sm" onClick={fetchReport} disabled={reportLoading} data-testid="report-refresh-btn">
                    {reportLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Загрузить"}
                  </Button>
                </div>
              </div>

              {reportLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="w-6 h-6 animate-spin text-mint-500" />
                </div>
              ) : report ? (
                <>
                  {report.error && (
                    <Card><CardContent className="py-4 text-sm text-red-400">{report.error}</CardContent></Card>
                  )}

                  {/* By cashier summary */}
                  {report.by_cashier?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Users className="w-4 h-4" />
                          По официантам
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border/50 text-muted-foreground">
                                <th className="text-left py-2 pr-4">Официант</th>
                                <th className="text-right py-2 px-3">Чеков</th>
                                <th className="text-right py-2 px-3">Позиций</th>
                                <th className="text-right py-2 px-3">Скидки</th>
                                <th className="text-right py-2 pl-3">Выручка</th>
                              </tr>
                            </thead>
                            <tbody>
                              {report.by_cashier.map((c, i) => (
                                <tr key={i} className="border-b border-border/20 hover:bg-muted/30 cursor-pointer" onClick={() => { setReportCashier(c.cashier); fetchReport(); }} data-testid={`cashier-row-${i}`}>
                                  <td className="py-2.5 pr-4 font-medium">{c.cashier}</td>
                                  <td className="text-right py-2.5 px-3 text-muted-foreground">{c.receipts}</td>
                                  <td className="text-right py-2.5 px-3 text-muted-foreground">{c.items}</td>
                                  <td className="text-right py-2.5 px-3 text-muted-foreground">{c.discount} BYN</td>
                                  <td className="text-right py-2.5 pl-3 font-semibold">{c.revenue} BYN</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Receipts table */}
                  {report.receipts?.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Детализация ({report.total_receipts} записей)</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-border/50 text-muted-foreground text-xs">
                                <th className="text-left py-2 pr-2">Дата</th>
                                <th className="text-left py-2 px-2">Официант</th>
                                <th className="text-left py-2 px-2">Товар</th>
                                <th className="text-right py-2 px-2">Кол-во</th>
                                <th className="text-right py-2 px-2">Цена</th>
                                <th className="text-right py-2 pl-2">Сумма</th>
                              </tr>
                            </thead>
                            <tbody>
                              {report.receipts.map((r, i) => (
                                <tr key={i} className="border-b border-border/10 text-xs">
                                  <td className="py-1.5 pr-2 text-muted-foreground whitespace-nowrap">{r.date} {r.time}</td>
                                  <td className="py-1.5 px-2">{r.cashier}</td>
                                  <td className="py-1.5 px-2 max-w-[200px] truncate">{r.product}</td>
                                  <td className="text-right py-1.5 px-2 text-muted-foreground">{r.qty}</td>
                                  <td className="text-right py-1.5 px-2 text-muted-foreground">{r.price}</td>
                                  <td className="text-right py-1.5 pl-2 font-medium">{r.sum}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {!report.by_cashier?.length && !report.error && (
                    <Card><CardContent className="py-8 text-center text-muted-foreground">Нет данных за выбранный период</CardContent></Card>
                  )}
                </>
              ) : (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    Нажмите «Загрузить» для получения отчёта реализации из Caffesta
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </TabsContent>

        {/* Daily Digest Tab */}
        <TabsContent value="digest" className="space-y-4 mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="w-5 h-5" /> Ежедневный Telegram-дайджест
              </CardTitle>
              <CardDescription>
                Каждое утро в 08:00 (Минск) бот присылает итоги вчерашнего дня: выручка, чеки, средний чек,
                разбивка по временным окнам и топ-3 позиции. Сравнение с аналогичным днём неделю назад.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label className="text-base font-medium">Включить отправку</Label>
                <Switch
                  checked={!!digestSettings.daily_digest_enabled}
                  onCheckedChange={(v) => setDigestSettings({ ...digestSettings, daily_digest_enabled: v })}
                  data-testid="digest-enabled-switch"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Bot Token (опционально)</Label>
                  <Input
                    value={digestSettings.daily_digest_bot_token}
                    onChange={(e) => setDigestSettings({ ...digestSettings, daily_digest_bot_token: e.target.value })}
                    placeholder="Оставьте пустым — использовать токен из настроек Telegram"
                    data-testid="digest-token-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Chat ID (опционально)</Label>
                  <Input
                    value={digestSettings.daily_digest_chat_id}
                    onChange={(e) => setDigestSettings({ ...digestSettings, daily_digest_chat_id: e.target.value })}
                    placeholder="Оставьте пустым — использовать chat_id из Telegram"
                    data-testid="digest-chat-input"
                  />
                </div>
              </div>

              <div className="space-y-2 pt-4 border-t border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Временные окна (до 4 шт)</Label>
                    <p className="text-xs text-muted-foreground">По каждому окну — отдельная строка в дайджесте со сравнением.</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addDigestWindow} disabled={(digestSettings.daily_digest_windows || []).length >= 4} data-testid="add-digest-window">
                    <Plus className="w-4 h-4 mr-1" /> Окно
                  </Button>
                </div>
                <div className="space-y-2">
                  {(digestSettings.daily_digest_windows || []).map((w, i) => (
                    <div key={i} className="flex items-center gap-2" data-testid={`digest-window-${i}`}>
                      <Input
                        className="flex-1"
                        placeholder="Название (напр. Обед)"
                        value={w.name || ''}
                        onChange={(e) => updateDigestWindow(i, { name: e.target.value })}
                      />
                      <Input className="w-28" type="time" value={w.time_from || ''} onChange={(e) => updateDigestWindow(i, { time_from: e.target.value })} />
                      <span className="text-muted-foreground">–</span>
                      <Input className="w-28" type="time" value={w.time_to || ''} onChange={(e) => updateDigestWindow(i, { time_to: e.target.value })} />
                      <Button type="button" variant="ghost" size="icon" onClick={() => removeDigestWindow(i)}>
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 flex-wrap pt-2">
                <Button onClick={saveDigestSettings} disabled={digestSaving} data-testid="save-digest-settings">
                  {digestSaving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Сохранить
                </Button>
                <Button variant="outline" onClick={loadDigestPreview} disabled={digestLoading} data-testid="digest-preview">
                  {digestLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
                  Предпросмотр
                </Button>
                <Button variant="outline" onClick={sendDigestNow} data-testid="digest-send-now">
                  <CalendarDays className="w-4 h-4 mr-2" />
                  Отправить сейчас
                </Button>
              </div>
            </CardContent>
          </Card>

          {digestPreview && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Предпросмотр сообщения</CardTitle>
                <CardDescription>Так будет выглядеть сообщение в Telegram (HTML-теги будут отрендерены клиентом).</CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  className="p-4 rounded-lg bg-muted/50 font-mono text-sm whitespace-pre-wrap"
                  data-testid="digest-preview-text"
                  dangerouslySetInnerHTML={{ __html: digestPreview }}
                />
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SummaryCard({ title, value, icon: Icon, color }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
          </div>
          <div className={`p-3 rounded-xl ${color}`}>
            <Icon className="w-5 h-5 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

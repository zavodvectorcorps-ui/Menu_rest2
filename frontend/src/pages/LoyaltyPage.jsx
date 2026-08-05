import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Gift, Send, Loader2, RefreshCw, CheckCircle2, AlertCircle, Trash2, Search, MessageCircle, Megaphone } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { useApp } from '@/App';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function LoyaltyPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [config, setConfig] = useState(null);
  const [stats, setStats] = useState(null);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [clients, setClients] = useState([]);
  const [clientSearch, setClientSearch] = useState('');
  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState('all');

  // Индивидуальное сообщение клиенту
  const [msgClient, setMsgClient] = useState(null); // client obj or null
  const [msgText, setMsgText] = useState('');
  const [msgSending, setMsgSending] = useState(false);

  // Массовая рассылка
  const [broadcastText, setBroadcastText] = useState('');
  const [broadcastMinBalance, setBroadcastMinBalance] = useState('');
  const [broadcastRecipients, setBroadcastRecipients] = useState(null); // preview count
  const [broadcastSending, setBroadcastSending] = useState(false);

  // form state
  const [form, setForm] = useState({
    caffesta_account_name: '',
    caffesta_api_key: '',
    pos_id: '',
    sync_interval_min: 2,
    telegram_bot_token: '',
    template_accrual: '',
    template_debit: '',
    is_enabled: false,
  });

  const loadConfig = useCallback(async () => {
    if (!currentRestaurantId) return;
    try {
      const [cfgR, statR] = await Promise.all([
        axios.get(`${API}/restaurants/${currentRestaurantId}/loyalty/config`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/loyalty/stats`, authHeaders),
      ]);
      setConfig(cfgR.data);
      setStats(statR.data);
      setForm((f) => ({
        ...f,
        caffesta_account_name: cfgR.data.caffesta_account_name || '',
        pos_id: cfgR.data.pos_id || '',
        sync_interval_min: cfgR.data.sync_interval_min || 2,
        template_accrual: cfgR.data.template_accrual || '',
        template_debit: cfgR.data.template_debit || '',
        is_enabled: !!cfgR.data.is_enabled,
        // Секреты не пре-заполняем — плейсхолдер покажет маску.
        caffesta_api_key: '',
        telegram_bot_token: '',
      }));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось загрузить конфиг');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRestaurantId, token]);

  const loadClients = useCallback(async () => {
    if (!currentRestaurantId) return;
    try {
      const r = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/loyalty/clients`,
        { ...authHeaders, params: { search: clientSearch || undefined, limit: 500 } }
      );
      setClients(r.data || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось загрузить клиентов');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRestaurantId, token, clientSearch]);

  const loadLogs = useCallback(async () => {
    if (!currentRestaurantId) return;
    try {
      const params = { limit: 300 };
      if (logFilter === 'errors') params.status = 'error';
      else if (logFilter === 'notifications') params.status = 'success';
      const r = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/loyalty/logs`,
        { ...authHeaders, params }
      );
      setLogs(r.data || []);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось загрузить журнал');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRestaurantId, token, logFilter]);

  useEffect(() => { loadConfig(); }, [loadConfig]);
  useEffect(() => { loadClients(); }, [loadClients]);
  useEffect(() => { loadLogs(); }, [loadLogs]);

  const save = async () => {
    setSaving(true);
    try {
      const payload = { ...form };
      // Пустые секреты не отправляем (значит "не менять")
      if (!payload.caffesta_api_key) delete payload.caffesta_api_key;
      if (!payload.telegram_bot_token) delete payload.telegram_bot_token;
      await axios.put(
        `${API}/restaurants/${currentRestaurantId}/loyalty/config`,
        payload,
        authHeaders
      );
      toast.success('Настройки сохранены');
      await loadConfig();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const removeBotToken = async () => {
    if (!window.confirm('Удалить токен бота и снять webhook в Telegram?')) return;
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/loyalty/bot`, authHeaders);
      toast.success('Бот отключён');
      loadConfig();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
  };

  const syncNow = async () => {
    setSyncing(true);
    try {
      const r = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/loyalty/sync-now`,
        {},
        authHeaders
      );
      if (r.data.ok) {
        const info = r.data.info || {};
        if (info.changed) {
          toast.success(`Синхронизировано: ${info.processed} клиентов, отправлено ${info.notifications_sent || 0} уведомлений`);
        } else {
          toast.info('Caffesta пока не сообщает об изменениях');
        }
      } else {
        toast.error(r.data.error || 'Ошибка синхронизации');
      }
      await Promise.all([loadConfig(), loadClients(), loadLogs()]);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    } finally {
      setSyncing(false);
    }
  };

  const sendSingleMessage = async () => {
    if (!msgClient || !msgText.trim()) return;
    setMsgSending(true);
    try {
      await axios.post(
        `${API}/restaurants/${currentRestaurantId}/loyalty/clients/${msgClient.id}/message`,
        { text: msgText },
        authHeaders
      );
      toast.success('Сообщение отправлено');
      setMsgClient(null);
      setMsgText('');
      loadLogs();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка отправки');
    } finally {
      setMsgSending(false);
    }
  };

  const previewBroadcast = async () => {
    if (!broadcastText.trim()) {
      toast.error('Введите текст сообщения');
      return;
    }
    try {
      const payload = { text: broadcastText, dry_run: true };
      if (broadcastMinBalance !== '') payload.min_balance = Number(broadcastMinBalance);
      const r = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/loyalty/broadcast`,
        payload,
        authHeaders
      );
      setBroadcastRecipients(r.data.recipients || 0);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка');
    }
  };

  const sendBroadcast = async () => {
    if (!broadcastText.trim()) return;
    if (broadcastRecipients === null) {
      await previewBroadcast();
      return;
    }
    if (!window.confirm(`Отправить сообщение ${broadcastRecipients} получателям?`)) return;
    setBroadcastSending(true);
    try {
      const payload = { text: broadcastText, dry_run: false };
      if (broadcastMinBalance !== '') payload.min_balance = Number(broadcastMinBalance);
      const r = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/loyalty/broadcast`,
        payload,
        authHeaders
      );
      toast.success(`Отправлено: ${r.data.sent}, ошибок: ${r.data.failed}`);
      setBroadcastText('');
      setBroadcastRecipients(null);
      loadLogs();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка рассылки');
    } finally {
      setBroadcastSending(false);
    }
  };

  const fmtDate = (iso) => {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  };

  if (!config) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[300px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-6" data-testid="loyalty-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Gift className="w-6 h-6 text-mint-500" /> Лояльность
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Синхронизация бонусов Caffesta и Telegram-уведомления клиентам
          </p>
        </div>
        {stats && (
          <div className="flex gap-3 flex-wrap">
            <StatChip label="Клиентов всего" value={stats.total_clients} />
            <StatChip label="Привязано TG" value={stats.linked_clients} tone="mint" />
            <StatChip label="Уведомлений сегодня" value={stats.notifications_today} tone="mint" />
            <StatChip label="Ошибок сегодня" value={stats.errors_today} tone={stats.errors_today > 0 ? 'red' : 'neutral'} />
          </div>
        )}
      </div>

      <Tabs defaultValue="settings" className="w-full">
        <TabsList>
          <TabsTrigger value="settings" data-testid="loyalty-tab-settings">Настройки</TabsTrigger>
          <TabsTrigger value="clients" data-testid="loyalty-tab-clients">Клиенты</TabsTrigger>
          <TabsTrigger value="broadcast" data-testid="loyalty-tab-broadcast">Рассылка</TabsTrigger>
          <TabsTrigger value="logs" data-testid="loyalty-tab-logs">Журнал</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="space-y-4 mt-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Caffesta POS</span>
                {config.last_synced_at ? (
                  <Badge variant="outline" className="gap-1 border-mint-500 text-mint-600">
                    <CheckCircle2 className="w-3 h-3" /> Данные: {fmtDate(config.last_synced_at)}
                  </Badge>
                ) : (
                  <Badge variant="outline">данные ещё не подтягивались</Badge>
                )}
                {config.last_polled_at && (
                  <Badge variant="outline" className="gap-1 ml-2">
                    <RefreshCw className="w-3 h-3" /> Опрос: {fmtDate(config.last_polled_at)}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="Account name">
                <Input
                  value={form.caffesta_account_name}
                  onChange={(e) => setForm({ ...form, caffesta_account_name: e.target.value })}
                  placeholder="myatasport"
                  data-testid="loyalty-cf-account"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Часть URL перед .caffesta.com
                </p>
              </Field>
              <Field label="X-API-KEY">
                <Input
                  type="password"
                  value={form.caffesta_api_key}
                  onChange={(e) => setForm({ ...form, caffesta_api_key: e.target.value })}
                  placeholder={config.caffesta_api_key_set ? config.caffesta_api_key_mask : 'Введите ключ'}
                  data-testid="loyalty-cf-key"
                />
              </Field>
              <Field label="POS ID (ID точки продаж)">
                <Input
                  value={form.pos_id}
                  onChange={(e) => setForm({ ...form, pos_id: e.target.value })}
                  placeholder="1"
                  data-testid="loyalty-pos-id"
                />
              </Field>
              <Field label="Интервал опроса (мин)">
                <Input
                  type="number" min="1" max="60"
                  value={form.sync_interval_min}
                  onChange={(e) => setForm({ ...form, sync_interval_min: Number(e.target.value) })}
                  data-testid="loyalty-interval"
                />
              </Field>
              {config.last_error && (
                <div className="md:col-span-2 rounded-md border border-red-300 bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 text-sm p-3 flex gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium">Последняя ошибка ({fmtDate(config.last_error_at)}):</div>
                    <div className="mt-1 break-words">{config.last_error}</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Telegram-бот</span>
                {config.telegram_bot_username && (
                  <a
                    href={`https://t.me/${config.telegram_bot_username}`}
                    target="_blank" rel="noreferrer"
                    className="text-mint-600 text-sm hover:underline"
                  >
                    @{config.telegram_bot_username}
                  </a>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <Field label="Токен бота">
                <div className="flex gap-2">
                  <Input
                    type="password"
                    value={form.telegram_bot_token}
                    onChange={(e) => setForm({ ...form, telegram_bot_token: e.target.value })}
                    placeholder={config.telegram_bot_token_set ? config.telegram_bot_token_mask : 'Получить у @BotFather'}
                    data-testid="loyalty-bot-token"
                  />
                  {config.telegram_bot_token_set && (
                    <Button variant="outline" size="icon" onClick={removeBotToken} data-testid="loyalty-bot-delete">
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  При сохранении токена webhook Telegram настраивается автоматически.
                </p>
              </Field>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Шаблоны уведомлений</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <Field label="Начисление бонусов">
                <Textarea
                  rows={2}
                  value={form.template_accrual}
                  onChange={(e) => setForm({ ...form, template_accrual: e.target.value })}
                  data-testid="loyalty-tpl-accrual"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Плейсхолдеры: <code>{'{amount}'}</code>, <code>{'{balance}'}</code>, <code>{'{name}'}</code>
                </p>
              </Field>
              <Field label="Списание бонусов">
                <Textarea
                  rows={2}
                  value={form.template_debit}
                  onChange={(e) => setForm({ ...form, template_debit: e.target.value })}
                  data-testid="loyalty-tpl-debit"
                />
              </Field>
            </CardContent>
          </Card>

          <div className="flex items-center gap-3 flex-wrap pt-2">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <Switch
                checked={form.is_enabled}
                onCheckedChange={(v) => setForm({ ...form, is_enabled: v })}
                data-testid="loyalty-enabled-switch"
              />
              <span className="text-sm font-medium">
                {form.is_enabled ? 'Синхронизация включена' : 'Синхронизация выключена'}
              </span>
            </label>
            <div className="flex-1" />
            <Button variant="outline" onClick={syncNow} disabled={syncing || !config.is_enabled} data-testid="loyalty-sync-now">
              {syncing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <RefreshCw className="w-4 h-4 mr-2" />}
              Синхронизировать сейчас
            </Button>
            <Button onClick={save} disabled={saving} data-testid="loyalty-save-btn">
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Сохранить
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="clients" className="mt-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Поиск по имени или телефону"
                value={clientSearch}
                onChange={(e) => setClientSearch(e.target.value)}
                className="pl-9"
                data-testid="loyalty-clients-search"
              />
            </div>
            <span className="text-sm text-muted-foreground">
              Всего: <b>{clients.length}</b>
            </span>
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="p-3">Телефон</th>
                  <th className="p-3">Имя</th>
                  <th className="p-3">Telegram</th>
                  <th className="p-3 text-right">Баланс</th>
                  <th className="p-3">Последняя синхр.</th>
                  <th className="p-3"></th>
                </tr>
              </thead>
              <tbody>
                {clients.length === 0 && (
                  <tr><td colSpan={6} className="p-6 text-center text-muted-foreground">Пока никого</td></tr>
                )}
                {clients.map((c) => (
                  <tr key={c.id} className="border-t hover:bg-muted/20">
                    <td className="p-3 font-mono text-xs">+{c.phone_norm}</td>
                    <td className="p-3">{c.name || <span className="text-muted-foreground">—</span>}</td>
                    <td className="p-3">
                      {c.telegram_chat_id ? (
                        c.telegram_username ? (
                          <span className="text-mint-600">@{c.telegram_username}</span>
                        ) : (
                          <Badge variant="outline" className="text-mint-600 border-mint-500">chat #{c.telegram_chat_id}</Badge>
                        )
                      ) : (
                        <span className="text-muted-foreground text-xs">не привязан</span>
                      )}
                    </td>
                    <td className="p-3 text-right font-medium">{(c.last_bonus_balance || 0).toFixed(2)}</td>
                    <td className="p-3 text-xs text-muted-foreground">{fmtDate(c.last_synced_at)}</td>
                    <td className="p-3">
                      {c.telegram_chat_id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 gap-1 text-mint-600 hover:bg-mint-50 dark:hover:bg-mint-950/30"
                          onClick={() => { setMsgClient(c); setMsgText(''); }}
                          data-testid={`loyalty-msg-btn-${c.id}`}
                        >
                          <MessageCircle className="w-3.5 h-3.5" />
                          Написать
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="broadcast" className="mt-4 space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-mint-500" />
                Массовая рассылка
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="Текст сообщения">
                <Textarea
                  rows={5}
                  value={broadcastText}
                  onChange={(e) => { setBroadcastText(e.target.value); setBroadcastRecipients(null); }}
                  placeholder="Например: Новое сезонное меню уже в ресторане! Приходите пробовать 🍽"
                  data-testid="loyalty-broadcast-text"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Плейсхолдеры: <code>{'{name}'}</code>, <code>{'{balance}'}</code>. Поддерживается HTML.
                </p>
              </Field>

              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Только с балансом ≥">
                  <Input
                    type="number"
                    value={broadcastMinBalance}
                    onChange={(e) => { setBroadcastMinBalance(e.target.value); setBroadcastRecipients(null); }}
                    placeholder="без ограничений"
                    data-testid="loyalty-broadcast-min-balance"
                  />
                </Field>
              </div>

              {broadcastRecipients !== null && (
                <div className="rounded-md bg-mint-500/10 text-mint-700 dark:text-mint-400 px-4 py-3 text-sm flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  Получателей: <b>{broadcastRecipients}</b>
                </div>
              )}

              <div className="flex gap-2 flex-wrap">
                <Button variant="outline" onClick={previewBroadcast} disabled={!broadcastText.trim()} data-testid="loyalty-broadcast-preview">
                  Подсчитать получателей
                </Button>
                <Button
                  onClick={sendBroadcast}
                  disabled={!broadcastText.trim() || broadcastSending || broadcastRecipients === null || broadcastRecipients === 0}
                  className="bg-mint-500 hover:bg-mint-600"
                  data-testid="loyalty-broadcast-send"
                >
                  {broadcastSending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
                  Отправить рассылку
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Telegram ограничивает 30 сообщений в секунду. Рассылка на 1000 человек займёт ~35 секунд.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="mt-4">
          <div className="flex gap-2 mb-4">
            {[
              { key: 'all', label: 'Все' },
              { key: 'notifications', label: 'Уведомления' },
              { key: 'errors', label: 'Ошибки' },
            ].map((f) => (
              <Button
                key={f.key}
                variant={logFilter === f.key ? 'default' : 'outline'}
                size="sm"
                className="rounded-full"
                onClick={() => setLogFilter(f.key)}
                data-testid={`loyalty-log-filter-${f.key}`}
              >
                {f.label}
              </Button>
            ))}
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="p-3">Дата</th>
                  <th className="p-3">Тип</th>
                  <th className="p-3">Клиент</th>
                  <th className="p-3">Сообщение / ошибка</th>
                  <th className="p-3">Статус</th>
                </tr>
              </thead>
              <tbody>
                {logs.length === 0 && (
                  <tr><td colSpan={5} className="p-6 text-center text-muted-foreground">Записей нет</td></tr>
                )}
                {logs.map((l) => (
                  <tr key={l.id} className="border-t hover:bg-muted/20">
                    <td className="p-3 text-xs whitespace-nowrap">{fmtDate(l.sent_at)}</td>
                    <td className="p-3">
                      <Badge variant="outline" className={
                        l.kind === 'accrual' ? 'text-mint-600 border-mint-500' :
                        l.kind === 'debit' ? 'text-amber-600 border-amber-500' :
                        'text-red-600 border-red-500'
                      }>
                        {l.kind === 'accrual' ? '+ Начисление' : l.kind === 'debit' ? '− Списание' : l.kind}
                      </Badge>
                    </td>
                    <td className="p-3 font-mono text-xs">+{l.phone_norm || '—'}</td>
                    <td className="p-3 text-xs break-words max-w-md">
                      {l.status === 'error' ? (
                        <span className="text-red-600">{l.error_text || l.message}</span>
                      ) : (
                        l.message
                      )}
                    </td>
                    <td className="p-3">
                      {l.status === 'success' ? (
                        <Badge className="bg-mint-500">OK</Badge>
                      ) : (
                        <Badge variant="destructive">Ошибка{l.http_code ? ` ${l.http_code}` : ''}</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>

      {/* Диалог отправки индивидуального сообщения клиенту */}
      <Dialog open={!!msgClient} onOpenChange={(o) => { if (!o) setMsgClient(null); }}>
        <DialogContent className="max-w-md" data-testid="loyalty-msg-dialog">
          <DialogHeader>
            <DialogTitle>
              Сообщение клиенту{msgClient?.name ? ` — ${msgClient.name}` : ''}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground">
              +{msgClient?.phone_norm} · Баланс: {(msgClient?.last_bonus_balance || 0).toFixed(2)}
            </div>
            <Textarea
              rows={5}
              value={msgText}
              onChange={(e) => setMsgText(e.target.value)}
              placeholder="Ваш ответ..."
              data-testid="loyalty-msg-text"
              autoFocus
            />
            <p className="text-xs text-muted-foreground">
              Плейсхолдеры: <code>{'{name}'}</code>, <code>{'{balance}'}</code>
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMsgClient(null)}>Отмена</Button>
            <Button onClick={sendSingleMessage} disabled={!msgText.trim() || msgSending} data-testid="loyalty-msg-send">
              {msgSending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
              Отправить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground mb-1.5 block">{label}</Label>
      {children}
    </div>
  );
}

function StatChip({ label, value, tone = 'neutral' }) {
  const toneClasses = {
    neutral: 'bg-muted text-foreground',
    mint: 'bg-mint-500/10 text-mint-700 dark:text-mint-400',
    red: 'bg-red-500/10 text-red-700 dark:text-red-400',
  }[tone];
  return (
    <div className={`px-3 py-2 rounded-lg text-sm ${toneClasses}`}>
      <div className="text-xs opacity-70">{label}</div>
      <div className="text-xl font-bold leading-tight">{value}</div>
    </div>
  );
}

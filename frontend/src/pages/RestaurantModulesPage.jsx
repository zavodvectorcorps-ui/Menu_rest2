import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Loader2, Building2, Plus, Trash2, Globe, X, CheckCircle2, AlertCircle, AlertTriangle, Copy } from 'lucide-react';
import { toast } from 'sonner';
import { API, useApp } from '@/App';

const ALL_MODULES = [
  { key: 'caffesta',         label: 'Caffesta POS',          desc: 'Интеграция с кассовой системой Caffesta + аналитика POS, Сравнение по времени, Реализация' },
  { key: 'caffesta_mapping', label: 'Маппинг Caffesta',      desc: 'Связывание блюд меню с товарами Caffesta (fuzzy + ручной)' },
  { key: 'telegram_bot',     label: 'Telegram-бот',          desc: 'Уведомления о заказах и вызовах, Утренний дайджест, Алерты по марже' },
  { key: 'cost_control',     label: 'Контроль цен и маржи',  desc: 'Импорт себестоимости, мониторинг маржинальности, Telegram-алерты' },
  { key: 'factual_margin',   label: 'Фактическая маржа',     desc: 'Расчёт реального P&L по чекам Caffesta' },
  { key: 'cart_only',        label: 'Корзина (без онлайн-заказа)', desc: 'Гость собирает блюда в корзину и показывает официанту. Отправки на кухню/в Telegram нет.' },
];

export default function RestaurantModulesPage() {
  const { token } = useApp();
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', slug: '', address: '', phone: '', email: '', enabled_modules: [] });
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const load = async () => {
    try {
      const r = await axios.get(`${API}/restaurants`, auth);
      setRestaurants(r.data || []);
    } catch (e) {
      toast.error('Ошибка загрузки ресторанов');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const toggleModule = async (rest, key, on) => {
    setSavingId(rest.id);
    const newModules = on
      ? [...new Set([...(rest.enabled_modules || []), key])]
      : (rest.enabled_modules || []).filter(m => m !== key);
    try {
      await axios.put(`${API}/restaurants/${rest.id}`, { enabled_modules: newModules }, auth);
      setRestaurants(rs => rs.map(r => r.id === rest.id ? { ...r, enabled_modules: newModules } : r));
      toast.success(`${on ? 'Включено' : 'Отключено'}: ${ALL_MODULES.find(m => m.key === key)?.label}`);
    } catch (e) {
      toast.error('Не удалось сохранить');
    } finally {
      setSavingId(null);
    }
  };

  const handleCreate = async () => {
    if (!form.name.trim()) { toast.error('Введите название'); return; }
    setCreating(true);
    try {
      await axios.post(`${API}/restaurants`, form, auth);
      toast.success('Ресторан создан');
      setCreateOpen(false);
      setForm({ name: '', slug: '', address: '', phone: '', email: '', enabled_modules: [] });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось создать');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (rest) => {
    if (!window.confirm(`Удалить ресторан «${rest.name}»? Все его данные будут безвозвратно удалены.`)) return;
    try {
      await axios.delete(`${API}/restaurants/${rest.id}`, auth);
      toast.success('Удалено');
      setRestaurants(rs => rs.filter(r => r.id !== rest.id));
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось удалить');
    }
  };

  // Custom domains
  const [domainsOpen, setDomainsOpen] = useState(null);  // restaurant id
  const [newDomain, setNewDomain] = useState('');
  const [savingDomains, setSavingDomains] = useState(false);

  const saveDomains = async (rest, domains) => {
    setSavingDomains(true);
    try {
      const r = await axios.put(`${API}/restaurants/${rest.id}`, { custom_domains: domains }, auth);
      const updated = r.data?.custom_domains || domains;
      setRestaurants(rs => rs.map(x => x.id === rest.id ? { ...x, custom_domains: updated } : x));
      toast.success('Домены обновлены');
      setNewDomain('');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось сохранить');
    } finally {
      setSavingDomains(false);
    }
  };

  const addDomain = (rest) => {
    const d = newDomain.trim().toLowerCase().replace(/^https?:\/\//, '').split('/')[0].split(':')[0];
    if (!d) return;
    if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$/.test(d)) {
      toast.error('Введите валидный домен (например, menu.catch.com)');
      return;
    }
    const current = rest.custom_domains || [];
    if (current.includes(d)) { toast.error('Этот домен уже добавлен'); return; }
    saveDomains(rest, [...current, d]);
  };

  const removeDomain = (rest, domain) => {
    const next = (rest.custom_domains || []).filter(d => d !== domain);
    saveDomains(rest, next);
  };

  // Per-domain status check ({ [`${rid}|${domain}`]: { loading, result } })
  const [domainStatus, setDomainStatus] = useState({});

  const checkDomain = async (rest, domain) => {
    const key = `${rest.id}|${domain}`;
    setDomainStatus(s => ({ ...s, [key]: { loading: true } }));
    try {
      const r = await axios.get(`${API}/restaurants/${rest.id}/domains/check`, {
        ...auth,
        params: { domain },
      });
      setDomainStatus(s => ({ ...s, [key]: { loading: false, result: r.data } }));
      const v = r.data?.overall;
      if (v === 'ok') toast.success('Домен полностью настроен');
      else if (v === 'warning') toast.warning(r.data.summary);
      else toast.error(r.data.summary);
    } catch (e) {
      setDomainStatus(s => ({ ...s, [key]: { loading: false, error: e.response?.data?.detail || 'Ошибка проверки' } }));
      toast.error(e.response?.data?.detail || 'Ошибка проверки домена');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Скопировано в буфер обмена');
    } catch {
      toast.error('Не удалось скопировать');
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6" data-testid="rest-modules-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-heading text-3xl font-bold flex items-center gap-3">
            <Building2 className="w-8 h-8 text-mint-500" />
            Модули ресторанов
          </h1>
          <p className="text-muted-foreground mt-1">
            Включайте и отключайте функциональные модули отдельно для каждого ресторана. Отключённые модули скрываются у администратора и менеджеров этого ресторана.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="bg-mint-500 hover:bg-mint-600" data-testid="btn-create-restaurant">
          <Plus className="w-4 h-4 mr-2" /> Добавить ресторан
        </Button>
      </div>

      {restaurants.length === 0 ? (
        <Card><CardContent className="py-10 text-center text-muted-foreground">Нет ресторанов</CardContent></Card>
      ) : (
        <div className="space-y-4">
          {restaurants.map(rest => (
            <Card key={rest.id} data-testid={`rest-card-${rest.id}`}>
              <CardHeader>
                <CardTitle className="flex items-center gap-3">
                  <Building2 className="w-5 h-5 text-mint-500" />
                  {rest.name}
                  {savingId === rest.id && <Loader2 className="w-4 h-4 animate-spin" />}
                  <Button variant="ghost" size="sm" className="ml-auto text-rose-500 hover:text-rose-600" onClick={() => handleDelete(rest)} data-testid={`btn-delete-${rest.id}`}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </CardTitle>
                <CardDescription>{rest.address || rest.email || 'Без адреса'}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {ALL_MODULES.map(m => {
                    const isOn = (rest.enabled_modules || []).includes(m.key);
                    return (
                      <div key={m.key} className="flex items-start justify-between rounded-lg border border-border/60 p-3">
                        <div className="flex-1 min-w-0 mr-3">
                          <p className="text-sm font-semibold">{m.label}</p>
                          <p className="text-xs text-muted-foreground mt-0.5">{m.desc}</p>
                        </div>
                        <Switch
                          checked={isOn}
                          disabled={savingId === rest.id}
                          onCheckedChange={(v) => toggleModule(rest, m.key, v)}
                          data-testid={`toggle-${rest.id}-${m.key}`}
                        />
                      </div>
                    );
                  })}
                </div>

                {/* Custom domains */}
                <div className="rounded-lg border border-border/60 p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-mint-500" />
                      <p className="text-sm font-semibold">Кастомные домены</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { setDomainsOpen(domainsOpen === rest.id ? null : rest.id); setNewDomain(''); }}
                      data-testid={`btn-toggle-domains-${rest.id}`}
                    >
                      {domainsOpen === rest.id ? 'Свернуть' : 'Управление'}
                    </Button>
                  </div>
                  {(rest.custom_domains || []).length > 0 ? (
                    <div className="space-y-2">
                      {(rest.custom_domains || []).map(d => {
                        const key = `${rest.id}|${d}`;
                        const st = domainStatus[key];
                        const verdict = st?.result?.overall;
                        const StatusIcon =
                          verdict === 'ok' ? CheckCircle2 :
                          verdict === 'warning' ? AlertTriangle :
                          verdict === 'error' ? AlertCircle :
                          null;
                        const statusColor =
                          verdict === 'ok' ? 'text-emerald-500' :
                          verdict === 'warning' ? 'text-amber-500' :
                          verdict === 'error' ? 'text-rose-500' : '';
                        return (
                          <div key={d} className="rounded-lg border border-border/40 p-2.5 space-y-2" data-testid={`domain-row-${rest.id}-${d}`}>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded-full bg-mint-500/10 text-mint-700 dark:text-mint-300 border border-mint-500/30">
                                <Globe className="w-3 h-3" />
                                {d}
                              </span>
                              {StatusIcon && <StatusIcon className={`w-4 h-4 ${statusColor}`} />}
                              <a
                                href={`https://${d}`}
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-muted-foreground hover:text-foreground underline"
                              >
                                открыть
                              </a>
                              <div className="ml-auto flex items-center gap-1">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="h-7 text-xs"
                                  onClick={() => checkDomain(rest, d)}
                                  disabled={st?.loading}
                                  data-testid={`btn-check-domain-${rest.id}-${d}`}
                                >
                                  {st?.loading ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Проверить'}
                                </Button>
                                {domainsOpen === rest.id && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 w-7 p-0 text-rose-500"
                                    onClick={() => removeDomain(rest, d)}
                                    disabled={savingDomains}
                                    data-testid={`btn-remove-domain-${rest.id}-${d}`}
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </Button>
                                )}
                              </div>
                            </div>
                            {st?.result && (
                              <div className={`text-xs leading-relaxed ${statusColor || 'text-muted-foreground'}`}>
                                {st.result.summary}
                                {verdict !== 'ok' && (
                                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                                    <code className="text-[11px] bg-muted px-2 py-1 rounded font-mono select-all">
                                      ./scripts/add-domain.sh {d}
                                    </code>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="h-6 px-2 text-xs"
                                      onClick={() => copyToClipboard(`./scripts/add-domain.sh ${d}`)}
                                      data-testid={`btn-copy-cmd-${rest.id}-${d}`}
                                    >
                                      <Copy className="w-3 h-3 mr-1" /> Скопировать
                                    </Button>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">Доменов не привязано. Гости открывают меню по адресу <code className="text-[11px]">rest-menu.by/{rest.slug || rest.id}/НОМЕР_СТОЛА</code></p>
                  )}

                  {domainsOpen === rest.id && (
                    <div className="pt-2 border-t border-border/40 space-y-2">
                      <div className="flex gap-2">
                        <Input
                          value={newDomain}
                          onChange={(e) => setNewDomain(e.target.value)}
                          placeholder="catch-menu.by"
                          onKeyDown={(e) => { if (e.key === 'Enter') addDomain(rest); }}
                          data-testid={`input-new-domain-${rest.id}`}
                        />
                        <Button
                          onClick={() => addDomain(rest)}
                          disabled={savingDomains || !newDomain.trim()}
                          className="bg-mint-500 hover:bg-mint-600 shrink-0"
                          data-testid={`btn-add-domain-${rest.id}`}
                        >
                          {savingDomains ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                        </Button>
                      </div>
                      <details className="text-xs text-muted-foreground rounded-md bg-muted/30 p-2.5 -mx-1">
                        <summary className="cursor-pointer font-semibold text-foreground hover:text-mint-500">
                          📘 Пошаговая инструкция: как привязать домен (например, catch-menu.by)
                        </summary>
                        <ol className="list-decimal pl-5 mt-2 space-y-2 leading-relaxed">
                          <li>
                            <b>Купите домен</b> у регистратора (например, hoster.by, GoDaddy, REG.RU). Подойдёт любой свободный.
                          </li>
                          <li>
                            <b>В DNS-настройках домена</b> создайте A-запись:<br/>
                            <code className="text-[11px] bg-background px-2 py-0.5 rounded">A @ → {`<IP_ВАШЕГО_VPS>`}</code><br/>
                            <span className="text-[11px]">(IP сервера можно узнать командой <code>curl ifconfig.me</code> в SSH)</span><br/>
                            Подождите 5–30 минут пока DNS прорастёт.
                          </li>
                          <li>
                            <b>Добавьте домен сюда</b> через поле выше (нажмите Plus). Это сохранит привязку домена к ресторану в базе.
                          </li>
                          <li>
                            <b>Зайдите по SSH на ваш VPS</b> и в папке проекта запустите команду (домен скопируйте из чипа выше):<br/>
                            <code className="text-[11px] bg-background px-2 py-0.5 rounded select-all">./scripts/add-domain.sh ВАШ_ДОМЕН</code><br/>
                            Скрипт сам: проверит DNS, добавит блок в Nginx, получит SSL-сертификат Let's Encrypt и перезапустит Nginx (~30 секунд).
                          </li>
                          <li>
                            <b>Нажмите «Проверить»</b> рядом с доменом — должен загореться зелёный значок. Готово!
                          </li>
                          <li>
                            <b>QR-коды столов</b> на этом домене будут работать автоматически по адресу <code className="text-[11px]">https://ВАШ_ДОМЕН/НОМЕР_СТОЛА</code>. Чтобы напечатать QR именно с этим доменом, зайдите в настройки → Столы под учёткой ресторана и скачайте PDF — он использует текущий домен браузера.
                          </li>
                        </ol>
                      </details>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg" data-testid="dlg-create-restaurant">
          <DialogHeader>
            <DialogTitle>Новый ресторан</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Название*</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Кафе «Ромашка»" data-testid="input-create-name" />
            </div>
            <div>
              <Label>Slug (часть URL)</Label>
              <Input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} placeholder="romashka" data-testid="input-create-slug" />
              <p className="text-xs text-muted-foreground mt-1">Латиница и дефис. Будет использоваться как `/menu/{form.slug || 'slug'}`</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Адрес</Label>
                <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
              </div>
              <div>
                <Label>Телефон</Label>
                <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
            </div>
            <div>
              <Label>Email</Label>
              <Input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} type="email" />
            </div>
            <div>
              <Label className="block mb-2">Подключаемые модули</Label>
              <div className="space-y-2">
                {ALL_MODULES.map(m => {
                  const isOn = form.enabled_modules.includes(m.key);
                  return (
                    <div key={m.key} className="flex items-center justify-between rounded border border-border/60 p-2">
                      <span className="text-sm">{m.label}</span>
                      <Switch
                        checked={isOn}
                        onCheckedChange={(v) => {
                          const next = v
                            ? [...form.enabled_modules, m.key]
                            : form.enabled_modules.filter(x => x !== m.key);
                          setForm({ ...form, enabled_modules: next });
                        }}
                        data-testid={`create-toggle-${m.key}`}
                      />
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-muted-foreground mt-2">Можно изменить позже на этой же странице.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Отмена</Button>
            <Button onClick={handleCreate} disabled={creating} className="bg-mint-500 hover:bg-mint-600" data-testid="btn-create-submit">
              {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
              Создать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

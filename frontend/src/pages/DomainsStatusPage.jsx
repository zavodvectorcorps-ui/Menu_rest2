import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, RefreshCw, Globe, CheckCircle2, AlertTriangle, AlertCircle, Copy, ExternalLink, Building2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { API, useApp } from '@/App';

export default function DomainsStatusPage() {
  const { token } = useApp();
  const auth = { headers: { Authorization: `Bearer ${token}` } };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/admin/domains-status`, auth);
      setData(r.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось получить статус доменов');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); /* eslint-disable-next-line */ }, []);

  const copyCmd = async (text) => {
    try { await navigator.clipboard.writeText(text); toast.success('Скопировано'); }
    catch { toast.error('Не удалось скопировать'); }
  };

  // Per-domain "renewing" state: { [domain]: boolean }
  const [renewing, setRenewing] = useState({});

  const renewCert = async (domain) => {
    if (!window.confirm(`Принудительно продлить сертификат для ${domain}?\n\nЭто обратится к Let's Encrypt и перезапишет файлы сертификата. Соблюдается лимит Let's Encrypt (≤5 обновлений/неделю на домен).`)) return;
    setRenewing((s) => ({ ...s, [domain]: true }));
    try {
      const r = await axios.post(`${API}/admin/domains-status/${encodeURIComponent(domain)}/renew`, {}, auth);
      toast.success(`Сертификат продлён до ${r.data.renewed_expires_at?.slice(0, 10)}`);
      fetchData();
    } catch (e) {
      const msg = e.response?.data?.detail || 'Не удалось продлить сертификат';
      // Keep full error visible — user likely needs tail from certbot
      toast.error(msg, { duration: 10000 });
    } finally {
      setRenewing((s) => ({ ...s, [domain]: false }));
    }
  };

  const iconFor = (verdict) =>
    verdict === 'ok' ? <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" /> :
    verdict === 'warning' ? <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" /> :
    <AlertCircle className="w-5 h-5 text-rose-500 flex-shrink-0" />;

  const counts = data?.rows ? {
    ok: data.rows.filter((r) => r.overall === 'ok').length,
    warning: data.rows.filter((r) => r.overall === 'warning').length,
    error: data.rows.filter((r) => r.overall === 'error').length,
  } : { ok: 0, warning: 0, error: 0 };

  return (
    <div className="space-y-6" data-testid="domains-status-page">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 flex-wrap">
          <div>
            <CardTitle className="font-heading flex items-center gap-2">
              <Globe className="w-5 h-5 text-mint-500" />
              Подключённые домены VPS
            </CardTitle>
            <CardDescription>
              Статус всех кастомных доменов на сервере: nginx-конфиг, сертификат, привязка к ресторану.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} data-testid="btn-refresh-domains">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            <span className="ml-2">Обновить</span>
          </Button>
        </CardHeader>

        {data && (
          <CardContent className="flex flex-wrap gap-4 text-sm border-t border-border/40">
            <span className="inline-flex items-center gap-1.5 pt-4"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> ОК: <b>{counts.ok}</b></span>
            <span className="inline-flex items-center gap-1.5 pt-4"><AlertTriangle className="w-4 h-4 text-amber-500" /> Предупреждения: <b>{counts.warning}</b></span>
            <span className="inline-flex items-center gap-1.5 pt-4"><AlertCircle className="w-4 h-4 text-rose-500" /> Ошибки: <b>{counts.error}</b></span>
            <span className="inline-flex items-center gap-1.5 pt-4 text-muted-foreground">Всего: <b>{data.total}</b></span>
            {!data.dir_exists && (
              <span className="inline-flex items-center gap-1.5 pt-4 text-amber-500">
                <AlertTriangle className="w-4 h-4" /> Папка {data.custom_domains_dir} не смонтирована (это нормально в dev-окружении).
              </span>
            )}
          </CardContent>
        )}
      </Card>

      {loading && !data && (
        <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-mint-500" /></div>
      )}

      {data && data.rows.length === 0 && !loading && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Кастомных доменов пока нет. Привяжите домен ресторану в «Модули ресторанов» и запустите на VPS <code className="text-[11px]">./scripts/add-domain.sh</code>.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-3">
        {(data?.rows || []).map((row) => (
          <Card key={row.domain} data-testid={`domain-card-${row.domain}`}>
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start gap-3 flex-wrap">
                {iconFor(row.overall)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <a
                      href={`https://${row.domain}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-base font-semibold hover:text-mint-500 inline-flex items-center gap-1"
                    >
                      {row.domain}
                      <ExternalLink className="w-3.5 h-3.5 opacity-60" />
                    </a>
                    {row.has_nginx_config ? (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
                        NGINX ✓
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                        NGINX ✗
                      </span>
                    )}
                    {row.cert?.expires_at ? (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full border ${
                        row.cert.days_left != null && row.cert.days_left < 7
                          ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30'
                          : 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                      }`}>
                        SSL до {row.cert.expires_at.slice(0, 10)} ({row.cert.days_left} дн)
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30">
                        SSL ✗
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
                    {row.summary}
                  </p>

                  <div className="flex items-center gap-3 mt-2 flex-wrap text-xs text-muted-foreground">
                    {row.owner_restaurant ? (
                      <span className="inline-flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5" />
                        Ресторан: <b className="text-foreground">{row.owner_restaurant.name}</b>
                        {row.owner_restaurant.slug && <code className="text-[11px] bg-muted px-1 rounded">/{row.owner_restaurant.slug}</code>}
                      </span>
                    ) : (
                      <span className="text-rose-500 inline-flex items-center gap-1">
                        <AlertCircle className="w-3.5 h-3.5" /> Не привязан к ресторану
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {row.overall !== 'ok' && (
                <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border/40">
                  <code className="text-[11px] bg-muted px-2 py-1 rounded font-mono select-all">
                    ./scripts/add-domain.sh {row.domain}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => copyCmd(`./scripts/add-domain.sh ${row.domain}`)}
                    data-testid={`btn-copy-fix-${row.domain}`}
                  >
                    <Copy className="w-3 h-3 mr-1" /> Скопировать
                  </Button>
                </div>
              )}

              {/* Renew button — только если сертификат есть на диске */}
              {row.cert?.expires_at && (
                <div className="flex items-center gap-2 flex-wrap pt-2 border-t border-border/40">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8"
                    onClick={() => renewCert(row.domain)}
                    disabled={!!renewing[row.domain]}
                    data-testid={`btn-renew-${row.domain}`}
                  >
                    {renewing[row.domain] ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ShieldCheck className="w-4 h-4 mr-2" />}
                    {renewing[row.domain] ? 'Продление...' : 'Продлить сертификат'}
                  </Button>
                  <span className="text-[11px] text-muted-foreground">
                    Принудительный renew у Let's Encrypt (лимит ≤5/нед).
                  </span>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Plug, PlugZap, Save, TestTube, DollarSign, ShoppingCart, TrendingUp, Award, Users, FileText, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

export default function CaffestaPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState({ account_name: '', api_key: '', pos_id: '', payment_id: '1', enabled: false });
  const [connected, setConnected] = useState(false);

  // Analytics state
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsPeriod, setAnalyticsPeriod] = useState('30');

  // Sales report state
  const [reportLoading, setReportLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [reportPeriod, setReportPeriod] = useState('7');
  const [reportCashier, setReportCashier] = useState('');

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
        enabled: resp.data.enabled || false,
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
      const payload = {
        account_name: config.account_name.trim(),
        api_key: config.api_key.trim(),
        pos_id: config.pos_id ? parseInt(config.pos_id) : null,
        payment_id: config.payment_id ? parseInt(config.payment_id) : 1,
        enabled: config.enabled,
      };
      await axios.put(`${API}/restaurants/${currentRestaurantId}/caffesta`, payload, authHeaders);
      toast.success('Настройки сохранены');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
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
          <TabsTrigger value="report" data-testid="tab-report">Реализация</TabsTrigger>
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
                  <Label>Payment ID (способ оплаты)</Label>
                  <Input
                    type="number"
                    value={config.payment_id}
                    onChange={(e) => setConfig({ ...config, payment_id: e.target.value })}
                    placeholder="1"
                    data-testid="caffesta-payment-id"
                  />
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

              <div className="flex gap-3 pt-2">
                <Button onClick={saveConfig} disabled={saving} data-testid="caffesta-save-btn">
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Сохранить
                </Button>
                <Button variant="outline" onClick={testConnection} disabled={testing || !config.account_name || !config.api_key} data-testid="caffesta-test-btn">
                  {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TestTube className="w-4 h-4 mr-2" />}
                  Проверить подключение
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
                    </CardHeader>
                    <CardContent>
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

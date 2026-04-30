import { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Loader2, Building2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { API, useApp } from '@/App';

const ALL_MODULES = [
  { key: 'caffesta',         label: 'Caffesta POS',          desc: 'Интеграция с кассовой системой Caffesta + аналитика POS, Сравнение по времени, Реализация' },
  { key: 'caffesta_mapping', label: 'Маппинг Caffesta',      desc: 'Связывание блюд меню с товарами Caffesta (fuzzy + ручной)' },
  { key: 'telegram_bot',     label: 'Telegram-бот',          desc: 'Уведомления о заказах и вызовах, Утренний дайджест, Алерты по марже' },
  { key: 'cost_control',     label: 'Контроль цен и маржи',  desc: 'Импорт себестоимости, мониторинг маржинальности, Telegram-алерты' },
  { key: 'factual_margin',   label: 'Фактическая маржа',     desc: 'Расчёт реального P&L по чекам Caffesta' },
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
              <CardContent>
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

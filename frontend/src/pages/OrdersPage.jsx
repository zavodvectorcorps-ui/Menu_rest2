import { useState, useEffect, useMemo, useCallback } from 'react';
import { ShoppingBag, Phone, Clock, CheckCircle, XCircle, Loader2, CheckCheck, CalendarClock, User, PhoneCall, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

const STATUS_MAP = {
  new: { label: 'Новый', color: 'bg-blue-500', icon: Clock },
  in_progress: { label: 'В работе', color: 'bg-yellow-500', icon: Loader2 },
  completed: { label: 'Завершён', color: 'bg-green-500', icon: CheckCircle },
  cancelled: { label: 'Отменён', color: 'bg-red-500', icon: XCircle },
  pending: { label: 'Ожидает', color: 'bg-blue-500', icon: Clock },
  acknowledged: { label: 'Принят', color: 'bg-yellow-500', icon: CheckCircle },
};

export default function OrdersPage() {
  const { token, currentRestaurantId } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const [orders, setOrders] = useState([]);
  const [staffCalls, setStaffCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('orders');
  const [completeAllOpen, setCompleteAllOpen] = useState(false);
  const [completeAllType, setCompleteAllType] = useState('');
  const [clearAllOpen, setClearAllOpen] = useState(false);
  const [clearAllType, setClearAllType] = useState('');
  const [clearing, setClearing] = useState(false);

  const fetchData = async () => {
    if (!currentRestaurantId) return;
    try {
      const [ordersRes, callsRes] = await Promise.all([
        axios.get(`${API}/restaurants/${currentRestaurantId}/orders`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/staff-calls`, authHeaders)
      ]);
      setOrders(ordersRes.data);
      setStaffCalls(callsRes.data);
    } catch (err) {
      toast.error('Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [currentRestaurantId]);

  // Listen for WebSocket events
  useEffect(() => {
    const handleNewOrder = () => fetchData();
    const handleNewCall = () => fetchData();
    window.addEventListener('ws:new_order', handleNewOrder);
    window.addEventListener('ws:new_staff_call', handleNewCall);
    return () => {
      window.removeEventListener('ws:new_order', handleNewOrder);
      window.removeEventListener('ws:new_staff_call', handleNewCall);
    };
  }, [currentRestaurantId]);

  const updateOrderStatus = async (orderId, status) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/orders/${orderId}/status`, { status }, authHeaders);
      fetchData();
    } catch { toast.error('Ошибка'); }
  };

  const updateCallStatus = async (callId, status) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/staff-calls/${callId}/status`, { status }, authHeaders);
      fetchData();
    } catch { toast.error('Ошибка'); }
  };

  const handleCompleteAll = async () => {
    try {
      if (completeAllType === 'orders') {
        const resp = await axios.post(`${API}/restaurants/${currentRestaurantId}/orders/complete-all`, {}, authHeaders);
        toast.success(resp.data.message);
      } else {
        const resp = await axios.post(`${API}/restaurants/${currentRestaurantId}/staff-calls/complete-all`, {}, authHeaders);
        toast.success(resp.data.message);
      }
      setCompleteAllOpen(false);
      fetchData();
    } catch { toast.error('Ошибка'); }
  };

  const handleClearAll = async () => {
    setClearing(true);
    try {
      const url = clearAllType === 'orders'
        ? `${API}/restaurants/${currentRestaurantId}/orders/clear-all`
        : `${API}/restaurants/${currentRestaurantId}/staff-calls/clear-all`;
      const resp = await axios.delete(url, authHeaders);
      toast.success(resp.data.message);
      setClearAllOpen(false);
      fetchData();
    } catch { toast.error('Ошибка очистки'); }
    finally { setClearing(false); }
  };

  const regularOrders = useMemo(() => orders.filter(o => !o.is_preorder), [orders]);
  const preOrders = useMemo(() => orders.filter(o => o.is_preorder), [orders]);
  const activeOrders = regularOrders.filter(o => o.status !== 'completed' && o.status !== 'cancelled');
  const activeCalls = staffCalls.filter(c => c.status !== 'completed');
  const activePreorders = preOrders.filter(o => o.status !== 'completed' && o.status !== 'cancelled');

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>;
  }

  const renderOrder = (order) => {
    const st = STATUS_MAP[order.status] || STATUS_MAP.new;
    const StIcon = st.icon;
    return (
      <div key={order.id} className="p-4 rounded-xl border border-border space-y-3" data-testid={`order-${order.id}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {order.is_preorder ? (
              <Badge className="bg-purple-500 text-white gap-1"><CalendarClock className="w-3 h-3" />Предзаказ</Badge>
            ) : (
              <Badge variant="outline">Стол #{order.table_number}</Badge>
            )}
            <Badge className={`${st.color} text-white gap-1`}><StIcon className="w-3 h-3" />{st.label}</Badge>
          </div>
          <span className="text-xs text-muted-foreground">{new Date(order.created_at).toLocaleString('ru')}</span>
        </div>

        {order.is_preorder && (
          <div className="grid grid-cols-2 gap-2 text-sm bg-purple-500/5 rounded-lg p-3">
            <div className="flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-purple-500" /><span>{order.customer_name || '—'}</span></div>
            <div className="flex items-center gap-1.5"><PhoneCall className="w-3.5 h-3.5 text-purple-500" /><span>{order.customer_phone || '—'}</span></div>
            <div className="flex items-center gap-1.5"><CalendarClock className="w-3.5 h-3.5 text-purple-500" /><span>{order.preorder_date || '—'} {order.preorder_time || ''}</span></div>
            {order.notes && <div className="col-span-2 text-muted-foreground">{order.notes}</div>}
          </div>
        )}

        <div className="space-y-1">
          {order.items?.map((item, i) => (
            <div key={i} className="flex justify-between text-sm">
              <span>{item.name} <span className="text-muted-foreground">x{item.quantity}</span></span>
              <span className="font-medium">{(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
          <div className="flex justify-between font-bold border-t border-border pt-1 mt-2">
            <span>Итого</span><span>{order.total?.toFixed(2)} BYN</span>
          </div>
        </div>

        {order.status !== 'completed' && order.status !== 'cancelled' && (
          <div className="flex gap-2">
            {order.status === 'new' && (
              <Button size="sm" className="bg-yellow-500 hover:bg-yellow-600 text-white" onClick={() => updateOrderStatus(order.id, 'in_progress')}>В работу</Button>
            )}
            <Button size="sm" className="bg-green-500 hover:bg-green-600 text-white" onClick={() => updateOrderStatus(order.id, 'completed')}>Завершить</Button>
            <Button size="sm" variant="outline" className="text-destructive" onClick={() => updateOrderStatus(order.id, 'cancelled')}>Отменить</Button>
          </div>
        )}
      </div>
    );
  };

  const renderCall = (call) => {
    const st = STATUS_MAP[call.status] || STATUS_MAP.pending;
    const StIcon = st.icon;
    return (
      <div key={call.id} className="p-4 rounded-xl border border-border" data-testid={`call-${call.id}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="outline">Стол #{call.table_number}</Badge>
            <Badge className={`${st.color} text-white gap-1`}><StIcon className="w-3 h-3" />{st.label}</Badge>
            <span className="text-sm font-medium">{call.call_type_name || 'Вызов'}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">{new Date(call.created_at).toLocaleString('ru')}</span>
            {call.status !== 'completed' && (
              <Button size="sm" className="bg-green-500 hover:bg-green-600 text-white h-7" onClick={() => updateCallStatus(call.id, 'completed')}>Готово</Button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="orders-page">
      <div>
        <h1 className="text-2xl font-heading font-bold">Заказы и вызовы</h1>
        <p className="text-muted-foreground">Управление заказами, предзаказами и вызовами персонала</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="grid grid-cols-3 w-full max-w-md">
          <TabsTrigger value="orders" className="gap-1.5" data-testid="tab-orders">
            <ShoppingBag className="w-4 h-4" />Заказы
            {activeOrders.length > 0 && <Badge className="bg-blue-500 text-white text-[10px] h-4 min-w-4 px-1">{activeOrders.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="preorders" className="gap-1.5" data-testid="tab-preorders">
            <CalendarClock className="w-4 h-4" />Предзаказы
            {activePreorders.length > 0 && <Badge className="bg-purple-500 text-white text-[10px] h-4 min-w-4 px-1">{activePreorders.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="calls" className="gap-1.5" data-testid="tab-calls">
            <Phone className="w-4 h-4" />Вызовы
            {activeCalls.length > 0 && <Badge className="bg-orange-500 text-white text-[10px] h-4 min-w-4 px-1">{activeCalls.length}</Badge>}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="orders" className="mt-6 space-y-4">
          {(activeOrders.length > 0 || regularOrders.length > 0) && (
            <div className="flex justify-end gap-2 flex-wrap">
              {activeOrders.length > 0 && (
                <Button variant="outline" className="gap-2" onClick={() => { setCompleteAllType('orders'); setCompleteAllOpen(true); }} data-testid="complete-all-orders-btn">
                  <CheckCheck className="w-4 h-4" />Завершить все ({activeOrders.length})
                </Button>
              )}
              {regularOrders.length > 0 && (
                <Button variant="outline" className="gap-2 border-destructive text-destructive hover:bg-destructive/10" onClick={() => { setClearAllType('orders'); setClearAllOpen(true); }} data-testid="clear-all-orders-btn">
                  <Trash2 className="w-4 h-4" />Очистить все ({regularOrders.length})
                </Button>
              )}
            </div>
          )}
          {regularOrders.length === 0 ? (
            <Card className="border-none shadow-md"><CardContent className="py-12 text-center text-muted-foreground"><ShoppingBag className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>Заказов пока нет</p></CardContent></Card>
          ) : (
            regularOrders.map(renderOrder)
          )}
        </TabsContent>

        <TabsContent value="preorders" className="mt-6 space-y-4">
          {(activePreorders.length > 0 || preOrders.length > 0) && (
            <div className="flex justify-end gap-2 flex-wrap">
              {activePreorders.length > 0 && (
                <Button variant="outline" className="gap-2" onClick={() => { setCompleteAllType('orders'); setCompleteAllOpen(true); }} data-testid="complete-all-preorders-btn">
                  <CheckCheck className="w-4 h-4" />Завершить все ({activePreorders.length})
                </Button>
              )}
              {preOrders.length > 0 && (
                <Button variant="outline" className="gap-2 border-destructive text-destructive hover:bg-destructive/10" onClick={() => { setClearAllType('orders'); setClearAllOpen(true); }} data-testid="clear-all-preorders-btn">
                  <Trash2 className="w-4 h-4" />Очистить все ({preOrders.length})
                </Button>
              )}
            </div>
          )}
          {preOrders.length === 0 ? (
            <Card className="border-none shadow-md"><CardContent className="py-12 text-center text-muted-foreground"><CalendarClock className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>Предзаказов пока нет</p></CardContent></Card>
          ) : (
            preOrders.map(renderOrder)
          )}
        </TabsContent>

        <TabsContent value="calls" className="mt-6 space-y-4">
          {(activeCalls.length > 0 || staffCalls.length > 0) && (
            <div className="flex justify-end gap-2 flex-wrap">
              {activeCalls.length > 0 && (
                <Button variant="outline" className="gap-2" onClick={() => { setCompleteAllType('calls'); setCompleteAllOpen(true); }} data-testid="complete-all-calls-btn">
                  <CheckCheck className="w-4 h-4" />Завершить все ({activeCalls.length})
                </Button>
              )}
              {staffCalls.length > 0 && (
                <Button variant="outline" className="gap-2 border-destructive text-destructive hover:bg-destructive/10" onClick={() => { setClearAllType('calls'); setClearAllOpen(true); }} data-testid="clear-all-calls-btn">
                  <Trash2 className="w-4 h-4" />Очистить все ({staffCalls.length})
                </Button>
              )}
            </div>
          )}
          {staffCalls.length === 0 ? (
            <Card className="border-none shadow-md"><CardContent className="py-12 text-center text-muted-foreground"><Phone className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>Вызовов пока нет</p></CardContent></Card>
          ) : (
            staffCalls.map(renderCall)
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={completeAllOpen} onOpenChange={setCompleteAllOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Завершить все?</DialogTitle>
            <DialogDescription>
              {completeAllType === 'orders'
                ? `Все активные заказы (${activeOrders.length + activePreorders.length}) будут отмечены как завершённые.`
                : `Все активные вызовы (${activeCalls.length}) будут отмечены как завершённые.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCompleteAllOpen(false)}>Отмена</Button>
            <Button className="bg-green-500 hover:bg-green-600 text-white gap-2" onClick={handleCompleteAll} data-testid="confirm-complete-all">
              <CheckCheck className="w-4 h-4" />Завершить все
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={clearAllOpen} onOpenChange={setClearAllOpen}>
        <DialogContent data-testid="clear-all-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">Очистить все?</DialogTitle>
            <DialogDescription>
              {clearAllType === 'orders'
                ? `Будут удалены ВСЕ заказы (${orders.length}), включая историю и предзаказы. Это действие необратимо.`
                : `Будут удалены ВСЕ вызовы (${staffCalls.length}). Это действие необратимо.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearAllOpen(false)} disabled={clearing}>Отмена</Button>
            <Button className="bg-destructive hover:bg-destructive/90 text-white gap-2" onClick={handleClearAll} disabled={clearing} data-testid="confirm-clear-all">
              {clearing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Очистить все
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

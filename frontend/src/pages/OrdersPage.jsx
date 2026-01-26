import { useState, useEffect } from 'react';
import { Calendar, Clock, Filter, Search, ChevronDown, Check, X, RefreshCw, Eye } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';

const statusLabels = {
  new: { label: 'Новый', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  in_progress: { label: 'В работе', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  completed: { label: 'Выполнен', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' },
  cancelled: { label: 'Отменён', color: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' }
};

const callStatusLabels = {
  pending: { label: 'Ожидает', color: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
  acknowledged: { label: 'Принят', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  completed: { label: 'Выполнен', color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300' }
};

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [staffCalls, setStaffCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('orders');

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const fetchData = async () => {
    try {
      const [ordersRes, callsRes] = await Promise.all([
        axios.get(`${API}/orders${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`),
        axios.get(`${API}/staff-calls`)
      ]);
      setOrders(ordersRes.data);
      setStaffCalls(callsRes.data);
    } catch (error) {
      toast.error('Ошибка загрузки заказов');
    } finally {
      setLoading(false);
    }
  };

  const updateOrderStatus = async (orderId, newStatus) => {
    try {
      await axios.put(`${API}/orders/${orderId}/status`, { status: newStatus });
      toast.success('Статус обновлён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка обновления статуса');
    }
  };

  const updateCallStatus = async (callId, newStatus) => {
    try {
      await axios.put(`${API}/staff-calls/${callId}/status?status=${newStatus}`);
      toast.success('Статус обновлён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка обновления статуса');
    }
  };

  const openOrderDetails = (order) => {
    setSelectedOrder(order);
    setDetailsDialogOpen(true);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      day: '2-digit', 
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredOrders = orders.filter(order => {
    if (!searchQuery) return true;
    return order.table_number.toString().includes(searchQuery) ||
           order.id.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const pendingCalls = staffCalls.filter(c => c.status === 'pending').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="orders-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground">Заказы и вызовы</h1>
          <p className="text-muted-foreground">Управление заказами гостей</p>
        </div>
        <Button
          variant="outline"
          className="gap-2 rounded-full"
          onClick={fetchData}
          data-testid="refresh-orders-btn"
        >
          <RefreshCw className="w-4 h-4" />
          Обновить
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="orders" className="gap-2" data-testid="tab-orders">
            Заказы
            <Badge variant="secondary" className="ml-1">{orders.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="calls" className="gap-2" data-testid="tab-calls">
            Вызовы персонала
            {pendingCalls > 0 && (
              <Badge className="ml-1 bg-red-500 text-white animate-pulse">{pendingCalls}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="orders" className="mt-6">
          {/* Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
              <Input
                placeholder="Поиск по номеру стола..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 rounded-full"
                data-testid="orders-search-input"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px] rounded-full" data-testid="status-filter">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Все статусы" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                <SelectItem value="new">Новые</SelectItem>
                <SelectItem value="in_progress">В работе</SelectItem>
                <SelectItem value="completed">Выполненные</SelectItem>
                <SelectItem value="cancelled">Отменённые</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Orders Table */}
          {filteredOrders.length === 0 ? (
            <Card className="border-none shadow-md">
              <CardContent className="py-12 text-center">
                <Clock className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">Заказов пока нет</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-none shadow-md overflow-hidden" data-testid="orders-table">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="font-heading">Стол</TableHead>
                    <TableHead className="font-heading">Время</TableHead>
                    <TableHead className="font-heading">Позиции</TableHead>
                    <TableHead className="font-heading">Сумма</TableHead>
                    <TableHead className="font-heading">Статус</TableHead>
                    <TableHead className="font-heading text-right">Действия</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOrders.map((order) => (
                    <TableRow key={order.id} className="table-row-hover" data-testid={`order-row-${order.id}`}>
                      <TableCell>
                        <span className="font-semibold">№{order.table_number}</span>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <span className="text-foreground">{formatDate(order.created_at)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          {order.items?.length || 0} поз.
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-mint-500">{order.total} ₽</span>
                      </TableCell>
                      <TableCell>
                        <Badge className={statusLabels[order.status]?.color}>
                          {statusLabels[order.status]?.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openOrderDetails(order)}
                            data-testid={`view-order-${order.id}`}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                          {order.status === 'new' && (
                            <Button
                              size="sm"
                              className="h-8 bg-mint-500 hover:bg-mint-600 rounded-full"
                              onClick={() => updateOrderStatus(order.id, 'in_progress')}
                              data-testid={`accept-order-${order.id}`}
                            >
                              Принять
                            </Button>
                          )}
                          {order.status === 'in_progress' && (
                            <Button
                              size="sm"
                              className="h-8 bg-emerald-500 hover:bg-emerald-600 rounded-full"
                              onClick={() => updateOrderStatus(order.id, 'completed')}
                              data-testid={`complete-order-${order.id}`}
                            >
                              <Check className="w-4 h-4 mr-1" />
                              Готово
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="calls" className="mt-6">
          {staffCalls.length === 0 ? (
            <Card className="border-none shadow-md">
              <CardContent className="py-12 text-center">
                <Clock className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">Вызовов пока нет</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4" data-testid="calls-list">
              {staffCalls.map((call) => (
                <Card 
                  key={call.id} 
                  className={`border-none shadow-md ${call.status === 'pending' ? 'ring-2 ring-amber-500/50' : ''}`}
                  data-testid={`call-${call.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                          <span className="text-lg font-bold text-amber-600 dark:text-amber-400">
                            {call.table_number}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-heading font-semibold text-foreground">
                            Стол №{call.table_number}
                          </h4>
                          <p className="text-sm text-muted-foreground">{formatDate(call.created_at)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge className={callStatusLabels[call.status]?.color}>
                          {callStatusLabels[call.status]?.label}
                        </Badge>
                        {call.status === 'pending' && (
                          <Button
                            size="sm"
                            className="bg-mint-500 hover:bg-mint-600 rounded-full"
                            onClick={() => updateCallStatus(call.id, 'acknowledged')}
                            data-testid={`acknowledge-call-${call.id}`}
                          >
                            Принять
                          </Button>
                        )}
                        {call.status === 'acknowledged' && (
                          <Button
                            size="sm"
                            className="bg-emerald-500 hover:bg-emerald-600 rounded-full"
                            onClick={() => updateCallStatus(call.id, 'completed')}
                            data-testid={`complete-call-${call.id}`}
                          >
                            <Check className="w-4 h-4 mr-1" />
                            Выполнен
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Order Details Dialog */}
      <Dialog open={detailsDialogOpen} onOpenChange={setDetailsDialogOpen}>
        <DialogContent className="max-w-lg" data-testid="order-details-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              Заказ №{selectedOrder?.id?.slice(0, 8)}
            </DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4 py-4">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Стол</span>
                <span className="font-semibold">№{selectedOrder.table_number}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Время</span>
                <span>{formatDate(selectedOrder.created_at)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Статус</span>
                <Badge className={statusLabels[selectedOrder.status]?.color}>
                  {statusLabels[selectedOrder.status]?.label}
                </Badge>
              </div>
              
              <div className="border-t border-border pt-4">
                <h4 className="font-heading font-semibold mb-3">Позиции:</h4>
                <div className="space-y-2">
                  {selectedOrder.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center py-2 border-b border-border/50 last:border-0">
                      <div>
                        <span className="font-medium">{item.name}</span>
                        <span className="text-muted-foreground ml-2">×{item.quantity}</span>
                      </div>
                      <span className="font-medium">{item.price * item.quantity} ₽</span>
                    </div>
                  ))}
                </div>
              </div>

              {selectedOrder.notes && (
                <div className="bg-muted/50 p-3 rounded-lg">
                  <span className="text-sm text-muted-foreground">Комментарий: </span>
                  <span className="text-sm">{selectedOrder.notes}</span>
                </div>
              )}

              <div className="flex justify-between items-center pt-4 border-t border-border">
                <span className="text-lg font-heading font-semibold">Итого:</span>
                <span className="text-xl font-bold text-mint-500">{selectedOrder.total} ₽</span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailsDialogOpen(false)}>
              Закрыть
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

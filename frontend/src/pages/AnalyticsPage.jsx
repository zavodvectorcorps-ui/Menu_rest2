import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Eye, ShoppingCart, Bell, DollarSign, TrendingUp, Users, Utensils, Loader2 } from 'lucide-react';
import { useApp, API } from '@/App';
import axios from 'axios';

export default function AnalyticsPage() {
  const { currentRestaurantId, token } = useApp();
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30');
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, [currentRestaurantId, period]);

  const fetchAnalytics = async () => {
    if (!currentRestaurantId) return;
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/analytics?days=${period}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setData(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-mint-500" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        Нет данных для отображения
      </div>
    );
  }

  const StatCard = ({ title, value, today, icon: Icon, color }) => (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold mt-1">{value}</p>
            {today !== undefined && (
              <p className="text-sm text-muted-foreground mt-1">Сегодня: {today}</p>
            )}
          </div>
          <div className={`p-3 rounded-xl ${color}`}>
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Simple bar chart using div widths
  const maxViews = Math.max(...data.views.by_day.map(d => d.count), 1);
  const maxOrders = Math.max(...data.orders.by_day.map(d => d.count), 1);

  return (
    <div className="space-y-6" data-testid="analytics-page">
      {/* Period selector */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-heading font-bold">Аналитика</h2>
          <p className="text-muted-foreground">Статистика за выбранный период</p>
        </div>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-40" data-testid="period-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">7 дней</SelectItem>
            <SelectItem value="30">30 дней</SelectItem>
            <SelectItem value="90">90 дней</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          title="Просмотры меню" 
          value={data.views.total}
          today={data.views.today}
          icon={Eye}
          color="bg-blue-500"
        />
        <StatCard 
          title="Заказы" 
          value={data.orders.total}
          today={data.orders.today}
          icon={ShoppingCart}
          color="bg-green-500"
        />
        <StatCard 
          title="Выручка (BYN)" 
          value={data.revenue.total.toFixed(2)}
          today={data.revenue.today.toFixed(2)}
          icon={DollarSign}
          color="bg-amber-500"
        />
        <StatCard 
          title="Вызовы персонала" 
          value={data.staff_calls.total}
          today={data.staff_calls.today}
          icon={Bell}
          color="bg-purple-500"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Views chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-500" />
              Просмотры меню
            </CardTitle>
            <CardDescription>По дням за период</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.views.by_day.slice(-14).map((day, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-20">
                    {new Date(day.date).toLocaleDateString('ru', { day: '2-digit', month: 'short' })}
                  </span>
                  <div className="flex-1 bg-muted rounded-full h-6 overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 rounded-full transition-all duration-500"
                      style={{ width: `${(day.count / maxViews) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium w-8 text-right">{day.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Orders chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-green-500" />
              Заказы
            </CardTitle>
            <CardDescription>По дням за период</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {data.orders.by_day.slice(-14).map((day, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground w-20">
                    {new Date(day.date).toLocaleDateString('ru', { day: '2-digit', month: 'short' })}
                  </span>
                  <div className="flex-1 bg-muted rounded-full h-6 overflow-hidden">
                    <div 
                      className="h-full bg-green-500 rounded-full transition-all duration-500"
                      style={{ width: `${(day.count / maxOrders) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium w-8 text-right">{day.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Popular items */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-amber-500" />
            Популярные блюда
          </CardTitle>
          <CardDescription>Топ-10 по количеству заказов</CardDescription>
        </CardHeader>
        <CardContent>
          {data.popular_items.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">Нет данных о заказах</p>
          ) : (
            <div className="space-y-3">
              {data.popular_items.map((item, i) => (
                <div key={item.id} className="flex items-center gap-4 p-3 bg-muted/50 rounded-lg">
                  <span className="w-8 h-8 rounded-full bg-mint-100 dark:bg-mint-900/30 flex items-center justify-center text-mint-600 font-bold">
                    {i + 1}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium">{item.name}</p>
                    <p className="text-sm text-muted-foreground">
                      Заказано: {item.count} шт. • Выручка: {item.revenue.toFixed(2)} BYN
                    </p>
                  </div>
                  <Utensils className="w-5 h-5 text-muted-foreground" />
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Additional stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <Users className="w-10 h-10 mx-auto text-mint-500 mb-2" />
            <p className="text-3xl font-bold">{data.employees_count}</p>
            <p className="text-sm text-muted-foreground">Сотрудников</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <TrendingUp className="w-10 h-10 mx-auto text-green-500 mb-2" />
            <p className="text-3xl font-bold">
              {data.orders.total > 0 ? (data.revenue.total / data.orders.total).toFixed(2) : '0.00'}
            </p>
            <p className="text-sm text-muted-foreground">Средний чек (BYN)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6 text-center">
            <Eye className="w-10 h-10 mx-auto text-blue-500 mb-2" />
            <p className="text-3xl font-bold">
              {data.views.total > 0 && data.orders.total > 0 
                ? ((data.orders.total / data.views.total) * 100).toFixed(1) + '%'
                : '0%'}
            </p>
            <p className="text-sm text-muted-foreground">Конверсия</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

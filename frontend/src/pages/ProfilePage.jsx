import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Bell, ShoppingBag, Users, Settings, ArrowRight, Utensils, Sparkles, HelpCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useApp, API } from '@/App';
import axios from 'axios';

export default function ProfilePage() {
  const { restaurant, token, currentRestaurantId } = useApp();
  const [stats, setStats] = useState({
    views_today: 0,
    views_total: 0,
    calls_today: 0,
    calls_total: 0,
    orders_today: 0,
    orders_total: 0,
    employees_count: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      if (!currentRestaurantId || !token) return;
      try {
        const response = await axios.get(
          `${API}/restaurants/${currentRestaurantId}/analytics?days=30`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setStats({
          views_today: response.data.views.today,
          views_total: response.data.views.total,
          calls_today: response.data.staff_calls.today,
          calls_total: response.data.staff_calls.total,
          orders_today: response.data.orders.today,
          orders_total: response.data.orders.total,
          employees_count: response.data.employees_count
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [currentRestaurantId, token]);

  const statCards = [
    {
      title: 'Просмотры меню',
      icon: Eye,
      todayLabel: 'Сегодня',
      todayValue: stats.views_today,
      monthLabel: 'За месяц',
      monthValue: stats.views_total,
      settingsPath: '/admin/analytics',
      color: 'text-mint-500',
      bgColor: 'bg-mint-50 dark:bg-mint-500/10'
    },
    {
      title: 'Вызовы персонала',
      icon: Bell,
      todayLabel: 'Сегодня',
      todayValue: stats.calls_today,
      monthLabel: 'За месяц',
      monthValue: stats.calls_total,
      settingsPath: '/admin/orders',
      color: 'text-brown-500',
      bgColor: 'bg-brown-50 dark:bg-brown-500/10'
    },
    {
      title: 'Заказы',
      icon: ShoppingBag,
      todayLabel: 'Сегодня',
      todayValue: stats.orders_today,
      monthLabel: 'За месяц',
      monthValue: stats.orders_total,
      settingsPath: '/admin/orders',
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-500/10'
    },
    {
      title: 'Сотрудники',
      icon: Users,
      todayLabel: 'Всего',
      todayValue: stats.employees_count,
      monthLabel: '',
      monthValue: null,
      settingsPath: '/admin/settings',
      color: 'text-purple-500',
      bgColor: 'bg-purple-50 dark:bg-purple-500/10'
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-mint-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="profile-page">
      {/* Restaurant Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-heading font-bold text-foreground">
            {restaurant?.name || 'Ресторан'}
          </h1>
          <p className="text-muted-foreground mt-1">
            {restaurant?.slogan || 'Добро пожаловать в личный кабинет'}
          </p>
        </div>
        <Link to="/admin/settings">
          <Button variant="outline" className="gap-2">
            <Settings className="w-4 h-4" />
            Настройки
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <Card key={index} className="relative overflow-hidden group hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className={`p-3 rounded-xl ${stat.bgColor}`}>
                    <Icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                  <Link to={stat.settingsPath} className="opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <Settings className="w-4 h-4" />
                    </Button>
                  </Link>
                </div>
                <div className="mt-4">
                  <h3 className="text-sm font-medium text-muted-foreground">{stat.title}</h3>
                  <div className="mt-2 flex items-baseline gap-4">
                    <div>
                      <span className="text-2xl font-bold text-foreground">{stat.todayValue}</span>
                      <span className="text-xs text-muted-foreground ml-1">{stat.todayLabel}</span>
                    </div>
                    {stat.monthValue !== null && (
                      <div className="text-muted-foreground">
                        <span className="text-lg font-semibold">{stat.monthValue}</span>
                        <span className="text-xs ml-1">{stat.monthLabel}</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Menu Editor Promo */}
        <Card className="bg-gradient-to-br from-mint-500 to-mint-600 text-white overflow-hidden">
          <CardContent className="p-6 relative">
            <div className="absolute -right-8 -bottom-8 w-32 h-32 bg-white/10 rounded-full" />
            <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-white/10 rounded-full" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-white/20 rounded-xl">
                  <Sparkles className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-heading font-bold">Редактор меню</h3>
              </div>
              <p className="text-mint-100 mb-4">
                Управляйте категориями и позициями меню, добавляйте фото и описания
              </p>
              <Link to="/admin/menu">
                <Button className="bg-white text-mint-600 hover:bg-mint-50 gap-2">
                  Открыть редактор
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Analytics Promo */}
        <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white overflow-hidden">
          <CardContent className="p-6 relative">
            <div className="absolute -right-8 -bottom-8 w-32 h-32 bg-white/10 rounded-full" />
            <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-white/10 rounded-full" />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-white/20 rounded-xl">
                  <Eye className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-heading font-bold">Аналитика</h3>
              </div>
              <p className="text-blue-100 mb-4">
                Отслеживайте просмотры, заказы и популярные блюда
              </p>
              <Link to="/admin/analytics">
                <Button className="bg-white text-blue-600 hover:bg-blue-50 gap-2">
                  Смотреть статистику
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Restaurant Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-heading">
            <Utensils className="w-5 h-5 text-mint-500" />
            Информация о ресторане
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Адрес</p>
                <p className="font-medium">{restaurant?.address || 'Не указан'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Телефон</p>
                <p className="font-medium">{restaurant?.phone || 'Не указан'}</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium">{restaurant?.email || 'Не указан'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Режим работы</p>
                <p className="font-medium">{restaurant?.working_hours || 'Не указан'}</p>
              </div>
            </div>
          </div>
          {restaurant?.description && (
            <div className="mt-6 pt-6 border-t">
              <p className="text-sm text-muted-foreground mb-2">Описание</p>
              <p className="text-foreground">{restaurant.description}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Help Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10">
              <HelpCircle className="w-6 h-6 text-amber-500" />
            </div>
            <div className="flex-1">
              <h3 className="font-heading font-semibold">Нужна помощь?</h3>
              <p className="text-sm text-muted-foreground">
                Посетите справочный центр или свяжитесь с поддержкой
              </p>
            </div>
            <div className="flex gap-2">
              <Link to="/admin/help">
                <Button variant="outline">Справка</Button>
              </Link>
              <Link to="/admin/support">
                <Button className="bg-mint-500 hover:bg-mint-600">Поддержка</Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Bell, ShoppingBag, Users, Settings, ArrowRight, Utensils, Sparkles, HelpCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useApp, API } from '@/App';
import axios from 'axios';

export default function ProfilePage() {
  const { restaurant } = useApp();
  const [stats, setStats] = useState({
    views_today: 0,
    views_month: 0,
    calls_today: 0,
    calls_month: 0,
    orders_today: 0,
    orders_month: 0,
    employees_count: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API}/stats`);
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const statCards = [
    {
      title: 'Просмотры меню',
      icon: Eye,
      todayLabel: 'Сегодня',
      todayValue: stats.views_today,
      monthLabel: 'За месяц',
      monthValue: stats.views_month,
      settingsPath: '/admin/settings',
      color: 'text-mint-500',
      bgColor: 'bg-mint-50 dark:bg-mint-500/10'
    },
    {
      title: 'Вызовы персонала',
      icon: Bell,
      todayLabel: 'Сегодня',
      todayValue: stats.calls_today,
      monthLabel: 'За месяц',
      monthValue: stats.calls_month,
      settingsPath: '/admin/settings',
      color: 'text-brown-500',
      bgColor: 'bg-brown-50 dark:bg-brown-500/10'
    },
    {
      title: 'Заказы',
      icon: ShoppingBag,
      todayLabel: 'Сегодня',
      todayValue: stats.orders_today,
      monthLabel: 'За месяц',
      monthValue: stats.orders_month,
      settingsPath: '/admin/orders',
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-50 dark:bg-emerald-500/10'
    },
    {
      title: 'Сотрудники',
      icon: Users,
      singleValue: stats.employees_count,
      singleLabel: 'Активных сотрудников',
      settingsPath: '/admin/settings',
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-500/10'
    }
  ];

  return (
    <div className="space-y-8 animate-fadeIn" data-testid="profile-page">
      {/* Restaurant Info Card */}
      <Card className="border-none shadow-lg" data-testid="restaurant-info-card">
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-mint-500 flex items-center justify-center shadow-lg shadow-mint-500/30">
                <Utensils className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-heading font-bold text-foreground">
                  {restaurant?.name || 'Загрузка...'}
                </h2>
                <p className="text-muted-foreground">{restaurant?.address}</p>
                <p className="text-sm text-mint-500 font-medium">{restaurant?.working_hours}</p>
              </div>
            </div>
            <Link to="/admin/settings">
              <Button 
                variant="outline" 
                className="gap-2 rounded-full border-mint-500 text-mint-500 hover:bg-mint-50 dark:hover:bg-mint-500/10"
                data-testid="edit-restaurant-btn"
              >
                <Settings className="w-4 h-4" />
                Редактировать
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" data-testid="stats-grid">
        {statCards.map((card, index) => {
          const Icon = card.icon;
          return (
            <Card 
              key={index} 
              className="stat-card border-none shadow-md hover:shadow-xl transition-all duration-300"
              data-testid={`stat-card-${index}`}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl ${card.bgColor} flex items-center justify-center`}>
                    <Icon className={`w-6 h-6 ${card.color}`} />
                  </div>
                  <Link 
                    to={card.settingsPath}
                    className="text-sm text-muted-foreground hover:text-mint-500 transition-colors flex items-center gap-1"
                    data-testid={`stat-settings-link-${index}`}
                  >
                    Настройки
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
                
                <h3 className="font-heading font-semibold text-foreground mb-3">{card.title}</h3>
                
                {card.singleValue !== undefined ? (
                  <div>
                    <p className="text-3xl font-bold text-foreground">
                      {loading ? '—' : card.singleValue}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">{card.singleLabel}</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{card.todayLabel}</span>
                      <span className="text-xl font-bold text-foreground">
                        {loading ? '—' : card.todayValue}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">{card.monthLabel}</span>
                      <span className="text-xl font-bold text-foreground">
                        {loading ? '—' : card.monthValue}
                      </span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Online Menu Editor Promo */}
      <Card 
        className="border-none shadow-lg bg-gradient-to-br from-mint-500 to-mint-600 text-white overflow-hidden"
        data-testid="menu-promo-card"
      >
        <CardContent className="p-8 relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/10 rounded-full translate-y-1/2 -translate-x-1/2" />
          
          <div className="relative z-10 max-w-2xl">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5" />
              <span className="text-sm font-medium opacity-90">Онлайн-редактор меню</span>
            </div>
            
            <h3 className="text-2xl md:text-3xl font-heading font-bold mb-4">
              Заполните меню в{' '}
              <Link to="/admin/menu" className="underline hover:no-underline">
                онлайн-редакторе
              </Link>
            </h3>
            
            <p className="text-white/80 mb-6 leading-relaxed">
              Ваши гости увидят актуальное меню, бизнес-ланч, акции и спецпредложения. 
              В редакторе можно настроить дизайн и элементы брендинга вашего ресторана.
            </p>
            
            <Link to="/admin/menu">
              <Button 
                className="bg-white text-mint-600 hover:bg-white/90 rounded-full px-8 py-6 text-base font-semibold shadow-lg"
                data-testid="create-menu-btn"
              >
                Создать меню
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-none shadow-md card-hover cursor-pointer" data-testid="quick-action-orders">
          <Link to="/admin/orders">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-500/10 flex items-center justify-center">
                  <ShoppingBag className="w-6 h-6 text-amber-500" />
                </div>
                <div>
                  <h4 className="font-heading font-semibold text-foreground">Текущие заказы</h4>
                  <p className="text-sm text-muted-foreground">Управление заказами</p>
                </div>
                <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="border-none shadow-md card-hover cursor-pointer" data-testid="quick-action-tables">
          <Link to="/admin/settings">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-500/10 flex items-center justify-center">
                  <Settings className="w-6 h-6 text-purple-500" />
                </div>
                <div>
                  <h4 className="font-heading font-semibold text-foreground">Управление столами</h4>
                  <p className="text-sm text-muted-foreground">QR-коды и ссылки</p>
                </div>
                <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
              </div>
            </CardContent>
          </Link>
        </Card>

        <Card className="border-none shadow-md card-hover cursor-pointer" data-testid="quick-action-help">
          <Link to="/admin/help">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-cyan-50 dark:bg-cyan-500/10 flex items-center justify-center">
                  <HelpCircle className="w-6 h-6 text-cyan-500" />
                </div>
                <div>
                  <h4 className="font-heading font-semibold text-foreground">Справочный центр</h4>
                  <p className="text-sm text-muted-foreground">Инструкции и FAQ</p>
                </div>
                <ArrowRight className="w-5 h-5 text-muted-foreground ml-auto" />
              </div>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
}

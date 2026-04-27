import { useState, useCallback, useRef, useEffect } from 'react';
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { 
  User, 
  UtensilsCrossed, 
  ShoppingBag, 
  Settings, 
  HelpCircle, 
  MessageSquare,
  Menu,
  X,
  ChevronRight,
  BarChart3,
  Users,
  LogOut,
  ChevronDown,
  Building2,
  Bot,
  Coffee,
  Link as LinkIcon,
  TrendingDown,
  Database,
  Wifi,
  WifiOff,
  Volume2,
  VolumeX
} from 'lucide-react';
import { useApp, useTheme } from '@/App';
import { Button } from '@/components/ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useWebSocket } from '@/hooks/useWebSocket';

const navItems = [
  { path: '/admin/profile', label: 'Профиль', icon: User },
  { path: '/admin/menu', label: 'Меню', icon: UtensilsCrossed },
  { path: '/admin/orders', label: 'Заказы', icon: ShoppingBag },
  { path: '/admin/analytics', label: 'Аналитика', icon: BarChart3 },
  { path: '/admin/settings', label: 'Настройки', icon: Settings },
  { path: '/admin/telegram-bot', label: 'Telegram-бот', icon: Bot },
  { path: '/admin/caffesta', label: 'Caffesta POS', icon: Coffee },
  { path: '/admin/caffesta-mapping', label: 'Маппинг Caffesta', icon: LinkIcon },
  { path: '/admin/price-control', label: 'Контроль цен', icon: TrendingDown },
  { path: '/admin/help', label: 'Справочный центр', icon: HelpCircle },
  { path: '/admin/support', label: 'Поддержка', icon: MessageSquare },
];

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(() => localStorage.getItem('ws_sound') !== 'off');
  const [unreadCount, setUnreadCount] = useState(0);
  const { restaurant, restaurants, currentRestaurantId, switchRestaurant, user, handleLogout, token } = useApp();
  const { theme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const audioRef = useRef(null);

  const playNotificationSound = useCallback(() => {
    if (!soundEnabled) return;
    try {
      if (!audioRef.current) {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        audioRef.current = ctx;
      }
      const ctx = audioRef.current;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.1);
      osc.frequency.setValueAtTime(880, ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    } catch { /* audio not available */ }
  }, [soundEnabled]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'new_order') {
      const order = msg.data;
      playNotificationSound();
      setUnreadCount(c => c + 1);
      if (order.is_preorder) {
        toast.info(`Новый предзаказ от ${order.customer_name || 'Гость'}`, {
          description: `${order.items?.length || 0} поз. — ${order.total?.toFixed(2)} BYN`,
          action: { label: 'Открыть', onClick: () => navigate('/admin/orders') },
          duration: 8000,
        });
      } else {
        toast.info(`Новый заказ — Стол #${order.table_number}`, {
          description: `${order.items?.length || 0} поз. — ${order.total?.toFixed(2)} BYN`,
          action: { label: 'Открыть', onClick: () => navigate('/admin/orders') },
          duration: 8000,
        });
      }
      window.dispatchEvent(new CustomEvent('ws:new_order', { detail: order }));
    } else if (msg.type === 'new_staff_call') {
      const call = msg.data;
      playNotificationSound();
      setUnreadCount(c => c + 1);
      toast.warning(`Вызов — Стол #${call.table_number}`, {
        description: call.call_type_name || 'Вызов персонала',
        action: { label: 'Открыть', onClick: () => navigate('/admin/orders') },
        duration: 8000,
      });
      window.dispatchEvent(new CustomEvent('ws:new_staff_call', { detail: call }));
    }
  }, [playNotificationSound, navigate]);

  const { connected } = useWebSocket(currentRestaurantId, token, handleWsMessage);

  // Reset unread count when on orders page
  useEffect(() => {
    if (location.pathname === '/admin/orders') setUnreadCount(0);
  }, [location.pathname]);

  const toggleSound = () => {
    const next = !soundEnabled;
    setSoundEnabled(next);
    localStorage.setItem('ws_sound', next ? 'on' : 'off');
    toast.success(next ? 'Звук уведомлений включён' : 'Звук уведомлений выключен');
  };

  const currentRestaurant = restaurants.find(r => r.id === currentRestaurantId) || restaurant;

  return (
    <div className="min-h-screen bg-background flex" data-testid="admin-layout">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-overlay"
        />
      )}

      {/* Sidebar */}
      <aside 
        className={cn(
          "fixed md:static inset-y-0 left-0 z-50 w-72 bg-card border-r border-border flex flex-col transition-transform duration-300 md:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
        data-testid="sidebar"
      >
        {/* Logo/Header with Restaurant Selector */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-mint-500 flex items-center justify-center">
                <UtensilsCrossed className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Личный кабинет</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setSidebarOpen(false)}
              data-testid="close-sidebar-btn"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {/* Restaurant Selector */}
          {restaurants.length > 1 ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button 
                  variant="outline" 
                  className="w-full justify-between h-auto py-2"
                  data-testid="restaurant-selector"
                >
                  <div className="flex items-center gap-2 text-left">
                    <Building2 className="w-4 h-4 text-mint-500 flex-shrink-0" />
                    <span className="truncate font-medium">{currentRestaurant?.name || 'Выберите ресторан'}</span>
                  </div>
                  <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-[240px]">
                {restaurants.map((r) => (
                  <DropdownMenuItem 
                    key={r.id} 
                    onClick={() => switchRestaurant(r.id)}
                    className={cn(
                      "cursor-pointer",
                      r.id === currentRestaurantId && "bg-mint-50 dark:bg-mint-900/20"
                    )}
                  >
                    <Building2 className="w-4 h-4 mr-2" />
                    {r.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 rounded-lg">
              <Building2 className="w-4 h-4 text-mint-500" />
              <span className="font-medium truncate">{currentRestaurant?.name || 'Ресторан'}</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                  isActive 
                    ? "bg-mint-500 text-white shadow-lg shadow-mint-500/30" 
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
                data-testid={`nav-${item.path.split('/').pop()}`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
                {item.path === '/admin/orders' && unreadCount > 0 && !isActive && (
                  <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-bold text-white animate-pulse" data-testid="unread-badge">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
                {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
              </NavLink>
            );
          })}

          {/* Users link (superadmin only) */}
          {user?.role === 'superadmin' && (
            <NavLink
              to="/admin/users"
              onClick={() => setSidebarOpen(false)}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                location.pathname === '/admin/users'
                  ? "bg-mint-500 text-white shadow-lg shadow-mint-500/30" 
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              data-testid="nav-users"
            >
              <Users className="w-5 h-5" />
              <span className="font-medium">Пользователи</span>
              {location.pathname === '/admin/users' && <ChevronRight className="w-4 h-4 ml-auto" />}
            </NavLink>
          )}

          {/* Backup link (superadmin only) */}
          {user?.role === 'superadmin' && (
            <NavLink
              to="/admin/backup"
              onClick={() => setSidebarOpen(false)}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                location.pathname === '/admin/backup'
                  ? "bg-mint-500 text-white shadow-lg shadow-mint-500/30"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
              data-testid="nav-backup"
            >
              <Database className="w-5 h-5" />
              <span className="font-medium">Резервные копии</span>
              {location.pathname === '/admin/backup' && <ChevronRight className="w-4 h-4 ml-auto" />}
            </NavLink>
          )}
        </nav>

        {/* User info & Logout */}
        <div className="p-4 border-t border-border">
          {/* Connection status */}
          <div className="flex items-center justify-between mb-3 px-1">
            <div className="flex items-center gap-2">
              <div className={cn("w-2 h-2 rounded-full", connected ? "bg-green-500" : "bg-red-500")} data-testid="ws-status-sidebar" />
              <span className="text-xs text-muted-foreground">{connected ? 'Онлайн' : 'Нет связи'}</span>
            </div>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={toggleSound} data-testid="toggle-sound-sidebar">
              {soundEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5 text-muted-foreground" />}
            </Button>
          </div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-mint-100 dark:bg-mint-900/30 flex items-center justify-center">
              <User className="w-5 h-5 text-mint-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{user?.username}</p>
              <p className="text-xs text-muted-foreground">
                {user?.role === 'superadmin' ? 'Суперадмин' : 'Менеджер'}
              </p>
            </div>
          </div>
          <Button 
            variant="outline" 
            className="w-full justify-start text-muted-foreground hover:text-destructive hover:border-destructive"
            onClick={handleLogout}
            data-testid="logout-btn"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Выйти
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <header className="md:hidden sticky top-0 z-30 bg-card border-b border-border p-4 flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
            data-testid="open-sidebar-btn"
          >
            <Menu className="w-5 h-5" />
          </Button>
          <h1 className="font-heading font-bold truncate">{currentRestaurant?.name}</h1>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleSound} data-testid="toggle-sound-mobile">
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4 text-muted-foreground" />}
            </Button>
            <div className={cn("w-2 h-2 rounded-full", connected ? "bg-green-500" : "bg-red-500")} data-testid="ws-status-mobile" title={connected ? 'Онлайн' : 'Нет связи'} />
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 p-4 md:p-8 overflow-auto">
          <Outlet />
        </div>

        {/* Footer */}
        <footer className="px-4 md:px-8 py-3 border-t border-border flex items-center justify-center gap-2 text-xs text-muted-foreground" data-testid="admin-footer">
          <span className="w-5 h-5 rounded bg-foreground/10 flex items-center justify-center font-bold text-[10px] text-foreground/60">MK</span>
          <span>Made by Knyazev</span>
        </footer>
      </main>
    </div>
  );
}

import { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { 
  User, 
  UtensilsCrossed, 
  ShoppingBag, 
  Settings, 
  HelpCircle, 
  MessageSquare,
  Menu,
  X,
  ChevronRight
} from 'lucide-react';
import { useApp, useTheme } from '@/App';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const navItems = [
  { path: '/admin/profile', label: 'Профиль', icon: User },
  { path: '/admin/menu', label: 'Меню', icon: UtensilsCrossed },
  { path: '/admin/orders', label: 'Заказы', icon: ShoppingBag },
  { path: '/admin/settings', label: 'Настройки', icon: Settings },
  { path: '/admin/help', label: 'Справочный центр', icon: HelpCircle },
  { path: '/admin/support', label: 'Поддержка', icon: MessageSquare },
];

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { restaurant } = useApp();
  const { theme } = useTheme();
  const location = useLocation();

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
        {/* Logo/Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-mint-500 flex items-center justify-center">
                <UtensilsCrossed className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-heading font-bold text-foreground truncate max-w-[160px]">
                  {restaurant?.name || 'Ресторан'}
                </h1>
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
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1" data-testid="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all duration-200",
                  isActive 
                    ? "bg-mint-500 text-white shadow-lg shadow-mint-500/25" 
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
                data-testid={`nav-${item.path.split('/').pop()}`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
              </NavLink>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border">
          <div className="px-4 py-3 rounded-xl bg-accent/50">
            <p className="text-sm font-medium text-foreground">Нужна помощь?</p>
            <p className="text-xs text-muted-foreground mt-1">
              Свяжитесь с поддержкой
            </p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-md border-b border-border px-4 md:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                onClick={() => setSidebarOpen(true)}
                data-testid="open-sidebar-btn"
              >
                <Menu className="w-5 h-5" />
              </Button>
              <div>
                <h2 className="font-heading font-semibold text-lg text-foreground">
                  {navItems.find(item => item.path === location.pathname)?.label || 'Панель управления'}
                </h2>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-foreground">{restaurant?.name}</p>
                <p className="text-xs text-muted-foreground">{restaurant?.address}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-brown-500 flex items-center justify-center text-white font-semibold">
                {restaurant?.name?.charAt(0) || 'М'}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 md:p-8" data-testid="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

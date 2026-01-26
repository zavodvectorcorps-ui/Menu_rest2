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
  ChevronRight,
  BarChart3,
  Users,
  LogOut,
  ChevronDown,
  Building2
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

const navItems = [
  { path: '/admin/profile', label: 'Профиль', icon: User },
  { path: '/admin/menu', label: 'Меню', icon: UtensilsCrossed },
  { path: '/admin/orders', label: 'Заказы', icon: ShoppingBag },
  { path: '/admin/analytics', label: 'Аналитика', icon: BarChart3 },
  { path: '/admin/settings', label: 'Настройки', icon: Settings },
  { path: '/admin/help', label: 'Справочный центр', icon: HelpCircle },
  { path: '/admin/support', label: 'Поддержка', icon: MessageSquare },
];

export default function AdminLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { restaurant, restaurants, currentRestaurantId, switchRestaurant, user, handleLogout } = useApp();
  const { theme } = useTheme();
  const location = useLocation();

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
        </nav>

        {/* User info & Logout */}
        <div className="p-4 border-t border-border">
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
          <div className="w-10" /> {/* Spacer for centering */}
        </header>

        {/* Page content */}
        <div className="flex-1 p-4 md:p-8 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { useEffect, useState, createContext, useContext } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";

// Pages
import LoginPage from "@/pages/LoginPage";
import AdminLayout from "@/pages/AdminLayout";
import ProfilePage from "@/pages/ProfilePage";
import MenuPage from "@/pages/MenuPage";
import OrdersPage from "@/pages/OrdersPage";
import SettingsPage from "@/pages/SettingsPage";
import HelpCenterPage from "@/pages/HelpCenterPage";
import SupportPage from "@/pages/SupportPage";
import ClientMenuPage from "@/pages/ClientMenuPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import UsersPage from "@/pages/UsersPage";
import TelegramBotPage from "@/pages/TelegramBotPage";
import CaffestaPage from "@/pages/CaffestaPage";
import BackupPage from "@/pages/BackupPage";
import PriceControlPage from "@/pages/PriceControlPage";
import CaffestaMappingPage from "@/pages/CaffestaMappingPage";
import FactualMarginPage from "@/pages/FactualMarginPage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Theme Context
export const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// App Context for sharing data
export const AppContext = createContext();

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

function App() {
  const [theme, setTheme] = useState('light');
  const [settings, setSettings] = useState(null);
  const [restaurant, setRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Auth state
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [restaurants, setRestaurants] = useState(() => {
    const saved = localStorage.getItem('restaurants');
    return saved ? JSON.parse(saved) : [];
  });
  const [currentRestaurantId, setCurrentRestaurantId] = useState(
    localStorage.getItem('currentRestaurantId')
  );

  // Initialize app
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Seed data
        await axios.post(`${API}/seed`);
        
        // If we have a token, verify it and fetch data
        if (token) {
          try {
            const response = await axios.get(`${API}/auth/me`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            setUser(response.data.user);
            setRestaurants(response.data.restaurants);
            localStorage.setItem('user', JSON.stringify(response.data.user));
            localStorage.setItem('restaurants', JSON.stringify(response.data.restaurants));
            
            // Set current restaurant if not set
            if (!currentRestaurantId && response.data.restaurants.length > 0) {
              const firstRestaurantId = response.data.restaurants[0].id;
              setCurrentRestaurantId(firstRestaurantId);
              localStorage.setItem('currentRestaurantId', firstRestaurantId);
            }
          } catch (error) {
            // Token invalid, clear auth
            handleLogout();
          }
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeApp();
  }, []);

  // Fetch restaurant data when currentRestaurantId changes
  useEffect(() => {
    if (token && currentRestaurantId) {
      fetchRestaurantData();
    }
  }, [currentRestaurantId, token]);

  const fetchRestaurantData = async () => {
    if (!currentRestaurantId || !token) return;
    
    try {
      const [restaurantRes, settingsRes] = await Promise.all([
        axios.get(`${API}/restaurants/${currentRestaurantId}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/restaurants/${currentRestaurantId}/settings`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      
      setRestaurant(restaurantRes.data);
      setSettings(settingsRes.data);
      
      if (settingsRes.data?.theme) {
        setTheme(settingsRes.data.theme);
      }
    } catch (error) {
      console.error('Failed to fetch restaurant data:', error);
    }
  };

  // Apply theme
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const handleLogin = (accessToken, userData, restaurantsList) => {
    setToken(accessToken);
    setUser(userData);
    setRestaurants(restaurantsList);
    if (restaurantsList.length > 0) {
      setCurrentRestaurantId(restaurantsList[0].id);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setRestaurants([]);
    setCurrentRestaurantId(null);
    setRestaurant(null);
    setSettings(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('restaurants');
    localStorage.removeItem('currentRestaurantId');
  };

  const switchRestaurant = (restaurantId) => {
    setCurrentRestaurantId(restaurantId);
    localStorage.setItem('currentRestaurantId', restaurantId);
  };

  const updateSettings = async (newSettings) => {
    if (!currentRestaurantId || !token) return;
    try {
      const response = await axios.put(
        `${API}/restaurants/${currentRestaurantId}/settings`, 
        newSettings,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSettings(response.data);
      if (newSettings.theme) {
        setTheme(newSettings.theme);
      }
      return response.data;
    } catch (error) {
      console.error('Failed to update settings:', error);
      throw error;
    }
  };

  const updateRestaurant = async (newData) => {
    if (!currentRestaurantId || !token) return;
    try {
      const response = await axios.put(
        `${API}/restaurants/${currentRestaurantId}`, 
        newData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRestaurant(response.data);
      // Update in restaurants list
      setRestaurants(prev => prev.map(r => r.id === currentRestaurantId ? response.data : r));
      return response.data;
    } catch (error) {
      console.error('Failed to update restaurant:', error);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-mint-500/20 flex items-center justify-center">
            <div className="w-10 h-10 rounded-full bg-mint-500 animate-ping" />
          </div>
          <p className="text-muted-foreground font-medium">Загрузка...</p>
        </div>
      </div>
    );
  }

  const appContextValue = {
    settings,
    updateSettings,
    restaurant,
    updateRestaurant,
    token,
    user,
    restaurants,
    currentRestaurantId,
    switchRestaurant,
    handleLogout,
    fetchRestaurantData
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <AppContext.Provider value={appContextValue}>
        <div className="App">
          <BrowserRouter>
            <Routes>
              {/* Login Route */}
              <Route 
                path="/login" 
                element={
                  token ? <Navigate to="/admin/profile" replace /> : <LoginPage onLogin={handleLogin} />
                } 
              />
              
              {/* Admin Routes (Protected) */}
              <Route 
                path="/admin" 
                element={token ? <AdminLayout /> : <Navigate to="/login" replace />}
              >
                <Route index element={<Navigate to="/admin/profile" replace />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="menu" element={<MenuPage />} />
                <Route path="orders" element={<OrdersPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="telegram-bot" element={<TelegramBotPage />} />
                <Route path="caffesta" element={<CaffestaPage />} />
                <Route path="caffesta-mapping" element={<CaffestaMappingPage />} />
                <Route path="price-control" element={<PriceControlPage />} />
                <Route path="factual-margin" element={<FactualMarginPage />} />
                <Route path="users" element={user?.role === 'superadmin' ? <UsersPage /> : <Navigate to="/admin/profile" replace />} />
                <Route path="backup" element={user?.role === 'superadmin' ? <BackupPage /> : <Navigate to="/admin/profile" replace />} />
                <Route path="help" element={<HelpCenterPage />} />
                <Route path="support" element={<SupportPage />} />
              </Route>
              
              {/* Client Menu Route (Public) */}
              <Route path="/menu/:tableCode" element={<ClientMenuPage />} />
              <Route path="/:slug/:tableNumber" element={<ClientMenuPage />} />
              
              {/* Default redirect */}
              <Route path="/" element={<Navigate to={token ? "/admin/profile" : "/login"} replace />} />
              <Route path="*" element={<Navigate to={token ? "/admin/profile" : "/login"} replace />} />
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </div>
      </AppContext.Provider>
    </ThemeContext.Provider>
  );
}

export default App;

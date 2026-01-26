import { useEffect, useState, createContext, useContext } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";

// Pages
import AdminLayout from "@/pages/AdminLayout";
import ProfilePage from "@/pages/ProfilePage";
import MenuPage from "@/pages/MenuPage";
import OrdersPage from "@/pages/OrdersPage";
import SettingsPage from "@/pages/SettingsPage";
import HelpCenterPage from "@/pages/HelpCenterPage";
import SupportPage from "@/pages/SupportPage";
import ClientMenuPage from "@/pages/ClientMenuPage";

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

// API Context for sharing data
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

  // Fetch initial data
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Seed data first
        await axios.post(`${API}/seed`);
        
        // Fetch settings and restaurant info
        const [settingsRes, restaurantRes] = await Promise.all([
          axios.get(`${API}/settings`),
          axios.get(`${API}/restaurant`)
        ]);
        
        setSettings(settingsRes.data);
        setRestaurant(restaurantRes.data);
        
        // Apply theme from settings
        if (settingsRes.data?.theme) {
          setTheme(settingsRes.data.theme);
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
      } finally {
        setLoading(false);
      }
    };

    initializeApp();
  }, []);

  // Apply theme to document
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const updateSettings = async (newSettings) => {
    try {
      const response = await axios.put(`${API}/settings`, newSettings);
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
    try {
      const response = await axios.put(`${API}/restaurant`, newData);
      setRestaurant(response.data);
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

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <AppContext.Provider value={{ settings, updateSettings, restaurant, updateRestaurant }}>
        <div className="App">
          <BrowserRouter>
            <Routes>
              {/* Admin Routes */}
              <Route path="/admin" element={<AdminLayout />}>
                <Route index element={<Navigate to="/admin/profile" replace />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="menu" element={<MenuPage />} />
                <Route path="orders" element={<OrdersPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="help" element={<HelpCenterPage />} />
                <Route path="support" element={<SupportPage />} />
              </Route>
              
              {/* Client Menu Route */}
              <Route path="/menu/:tableCode" element={<ClientMenuPage />} />
              
              {/* Default redirect */}
              <Route path="/" element={<Navigate to="/admin/profile" replace />} />
              <Route path="*" element={<Navigate to="/admin/profile" replace />} />
            </Routes>
          </BrowserRouter>
          <Toaster position="top-right" richColors />
        </div>
      </AppContext.Provider>
    </ThemeContext.Provider>
  );
}

export default App;

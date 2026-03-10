import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Palette, Building2, Bot, QrCode, Plus, Trash2, RefreshCw, Copy, ExternalLink, Users, Save, Moon, Sun, Bell, Layers, Edit2, Download, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { toast } from 'sonner';
import { useApp, useTheme, API } from '@/App';
import axios from 'axios';

export default function SettingsPage() {
  const { settings, updateSettings, restaurant, updateRestaurant, currentRestaurantId, token } = useApp();
  const { theme, setTheme } = useTheme();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };
  
  const [tables, setTables] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [menuSections, setMenuSections] = useState([]);
  const [callTypes, setCallTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Forms
  const [restaurantForm, setRestaurantForm] = useState({});
  const [settingsForm, setSettingsForm] = useState({});
  
  // Dialogs
  const [tableDialogOpen, setTableDialogOpen] = useState(false);
  const [employeeDialogOpen, setEmployeeDialogOpen] = useState(false);
  const [sectionDialogOpen, setSectionDialogOpen] = useState(false);
  const [callTypeDialogOpen, setCallTypeDialogOpen] = useState(false);
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  
  const [editingTable, setEditingTable] = useState(null);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [editingSection, setEditingSection] = useState(null);
  const [editingCallType, setEditingCallType] = useState(null);
  
  const [tableForm, setTableForm] = useState({ number: '', name: '', is_active: true });
  const [employeeForm, setEmployeeForm] = useState({ name: '', role: '', telegram_id: '', is_active: true });
  const [sectionForm, setSectionForm] = useState({ name: '', sort_order: 0, is_active: true });
  const [callTypeForm, setCallTypeForm] = useState({ name: '', telegram_message: '', sort_order: 0, is_active: true });
  
  const [qrData, setQrData] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    if (currentRestaurantId) {
      fetchData();
    }
  }, [currentRestaurantId]);

  useEffect(() => {
    if (restaurant) {
      setRestaurantForm({ ...restaurant });
    }
    if (settings) {
      setSettingsForm({ ...settings });
    }
  }, [restaurant, settings]);

  const fetchData = async () => {
    if (!currentRestaurantId) return;
    try {
      const [tablesRes, employeesRes, sectionsRes, callTypesRes] = await Promise.all([
        axios.get(`${API}/restaurants/${currentRestaurantId}/tables`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/employees`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/menu-sections`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/call-types`, authHeaders)
      ]);
      setTables(tablesRes.data);
      setEmployees(employeesRes.data);
      setMenuSections(sectionsRes.data);
      setCallTypes(callTypesRes.data);
    } catch (error) {
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await updateSettings(settingsForm);
      toast.success('Настройки сохранены');
    } catch (error) {
      toast.error('Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveRestaurant = async () => {
    setSaving(true);
    try {
      await updateRestaurant(restaurantForm);
      toast.success('Информация сохранена');
    } catch (error) {
      toast.error('Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  // Table handlers
  const openTableDialog = (table = null) => {
    if (table) {
      setEditingTable(table);
      setTableForm({ number: table.number, name: table.name || '', is_active: table.is_active });
    } else {
      setEditingTable(null);
      setTableForm({ number: tables.length + 1, name: '', is_active: true });
    }
    setTableDialogOpen(true);
  };

  const saveTableHandler = async () => {
    try {
      const data = { ...tableForm, number: parseInt(tableForm.number) };
      if (editingTable) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/tables/${editingTable.id}`, data, authHeaders);
        toast.success('Стол обновлён');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/tables`, data, authHeaders);
        toast.success('Стол добавлен');
      }
      setTableDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения');
    }
  };

  const deleteTable = async (tableId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/tables/${tableId}`, authHeaders);
      toast.success('Стол удалён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  const regenerateTableCode = async (tableId) => {
    try {
      await axios.post(`${API}/restaurants/${currentRestaurantId}/tables/${tableId}/regenerate-code`, {}, authHeaders);
      toast.success('Код обновлён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка обновления кода');
    }
  };

  const copyTableLink = (code) => {
    const link = `${window.location.origin}/menu/${code}`;
    navigator.clipboard.writeText(link);
    toast.success('Ссылка скопирована');
  };

  // QR Code handlers
  const showQrCode = async (table) => {
    setQrLoading(true);
    setQrDialogOpen(true);
    try {
      const baseUrl = window.location.origin;
      const response = await axios.get(`${API}/restaurants/${currentRestaurantId}/tables/${table.id}/qr?base_url=${encodeURIComponent(baseUrl)}`, authHeaders);
      setQrData(response.data);
    } catch (error) {
      toast.error('Ошибка генерации QR-кода');
      setQrDialogOpen(false);
    } finally {
      setQrLoading(false);
    }
  };

  const downloadQrCode = () => {
    if (!qrData) return;
    
    // Create download link from base64
    const link = document.createElement('a');
    link.href = qrData.qr_base64;
    link.download = `qr_table_${qrData.table_number}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('QR-код скачан');
  };

  // Employee handlers
  const openEmployeeDialog = (employee = null) => {
    if (employee) {
      setEditingEmployee(employee);
      setEmployeeForm({ 
        name: employee.name, 
        role: employee.role, 
        telegram_id: employee.telegram_id || '',
        is_active: employee.is_active 
      });
    } else {
      setEditingEmployee(null);
      setEmployeeForm({ name: '', role: '', telegram_id: '', is_active: true });
    }
    setEmployeeDialogOpen(true);
  };

  const saveEmployeeHandler = async () => {
    try {
      if (editingEmployee) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/employees/${editingEmployee.id}`, employeeForm, authHeaders);
        toast.success('Сотрудник обновлён');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/employees`, employeeForm, authHeaders);
        toast.success('Сотрудник добавлен');
      }
      setEmployeeDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения');
    }
  };

  const deleteEmployee = async (employeeId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/employees/${employeeId}`, authHeaders);
      toast.success('Сотрудник удалён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  // Menu Section handlers
  const openSectionDialog = (section = null) => {
    if (section) {
      setEditingSection(section);
      setSectionForm({ name: section.name, sort_order: section.sort_order, is_active: section.is_active });
    } else {
      setEditingSection(null);
      setSectionForm({ name: '', sort_order: menuSections.length + 1, is_active: true });
    }
    setSectionDialogOpen(true);
  };

  const saveSectionHandler = async () => {
    try {
      if (editingSection) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/menu-sections/${editingSection.id}`, sectionForm, authHeaders);
        toast.success('Раздел меню обновлён');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/menu-sections`, sectionForm, authHeaders);
        toast.success('Раздел меню добавлен');
      }
      setSectionDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения');
    }
  };

  const deleteSection = async (sectionId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/menu-sections/${sectionId}`, authHeaders);
      toast.success('Раздел меню удалён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  // Call Type handlers
  const openCallTypeDialog = (callType = null) => {
    if (callType) {
      setEditingCallType(callType);
      setCallTypeForm({ 
        name: callType.name, 
        telegram_message: callType.telegram_message || '',
        sort_order: callType.sort_order,
        is_active: callType.is_active 
      });
    } else {
      setEditingCallType(null);
      setCallTypeForm({ name: '', telegram_message: '', sort_order: callTypes.length + 1, is_active: true });
    }
    setCallTypeDialogOpen(true);
  };

  const saveCallTypeHandler = async () => {
    try {
      if (editingCallType) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/call-types/${editingCallType.id}`, callTypeForm, authHeaders);
        toast.success('Тип вызова обновлён');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/call-types`, callTypeForm, authHeaders);
        toast.success('Тип вызова добавлен');
      }
      setCallTypeDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения');
    }
  };

  const deleteCallType = async (typeId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/call-types/${typeId}`, authHeaders);
      toast.success('Тип вызова удалён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  const handleThemeToggle = async () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    setSettingsForm({ ...settingsForm, theme: newTheme });
    try {
      await updateSettings({ theme: newTheme });
    } catch (error) {
      console.error('Failed to save theme');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="settings-page">
      <div>
        <h1 className="text-2xl font-heading font-bold text-foreground">Настройки</h1>
        <p className="text-muted-foreground">Управление функциями и информацией о ресторане</p>
      </div>

      <Tabs defaultValue="features" className="w-full">
        <TabsList className="flex flex-wrap h-auto gap-2 p-1">
          <TabsTrigger value="features" className="gap-2" data-testid="tab-features">
            <SettingsIcon className="w-4 h-4" />
            Функции
          </TabsTrigger>
          <TabsTrigger value="restaurant" className="gap-2" data-testid="tab-restaurant">
            <Building2 className="w-4 h-4" />
            О ресторане
          </TabsTrigger>
          <TabsTrigger value="menu-sections" className="gap-2" data-testid="tab-menu-sections">
            <Layers className="w-4 h-4" />
            Разделы меню
          </TabsTrigger>
          <TabsTrigger value="call-types" className="gap-2" data-testid="tab-call-types">
            <Bell className="w-4 h-4" />
            Типы вызовов
          </TabsTrigger>
          <TabsTrigger value="tables" className="gap-2" data-testid="tab-tables">
            <QrCode className="w-4 h-4" />
            Столы
          </TabsTrigger>
          <TabsTrigger value="employees" className="gap-2" data-testid="tab-employees">
            <Users className="w-4 h-4" />
            Сотрудники
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-2" data-testid="tab-integrations">
            <Bot className="w-4 h-4" />
            Интеграции
          </TabsTrigger>
          <TabsTrigger value="appearance" className="gap-2" data-testid="tab-appearance">
            <Palette className="w-4 h-4" />
            Оформление
          </TabsTrigger>
        </TabsList>

        {/* Features Tab */}
        <TabsContent value="features" className="mt-6">
          <Card className="border-none shadow-md" data-testid="features-card">
            <CardHeader>
              <CardTitle className="font-heading">Функции кабинета</CardTitle>
              <CardDescription>Включите или отключите модули для вашего ресторана</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <Label className="text-base font-medium">Онлайн-меню</Label>
                  <p className="text-sm text-muted-foreground">Гости смогут просматривать меню по QR-коду</p>
                </div>
                <Switch
                  checked={settingsForm.online_menu_enabled}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, online_menu_enabled: checked })}
                  data-testid="switch-online-menu"
                />
              </div>
              
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <Label className="text-base font-medium">Вызов персонала</Label>
                  <p className="text-sm text-muted-foreground">Гости смогут вызвать официанта через меню</p>
                </div>
                <Switch
                  checked={settingsForm.staff_call_enabled}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, staff_call_enabled: checked })}
                  data-testid="switch-staff-call"
                />
              </div>
              
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <Label className="text-base font-medium">Онлайн-заказы</Label>
                  <p className="text-sm text-muted-foreground">Гости смогут делать заказы через меню</p>
                </div>
                <Switch
                  checked={settingsForm.online_orders_enabled}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, online_orders_enabled: checked })}
                  data-testid="switch-online-orders"
                />
              </div>
              
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div>
                  <Label className="text-base font-medium">Бизнес-ланч</Label>
                  <p className="text-sm text-muted-foreground">Показывать блок бизнес-ланча в меню</p>
                </div>
                <Switch
                  checked={settingsForm.business_lunch_enabled}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, business_lunch_enabled: checked })}
                  data-testid="switch-business-lunch"
                />
              </div>
              
              <div className="flex items-center justify-between py-3">
                <div>
                  <Label className="text-base font-medium">Акции и спецпредложения</Label>
                  <p className="text-sm text-muted-foreground">Показывать акционные позиции в меню</p>
                </div>
                <Switch
                  checked={settingsForm.promotions_enabled}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, promotions_enabled: checked })}
                  data-testid="switch-promotions"
                />
              </div>

              <Button 
                className="w-full mt-4 bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={handleSaveSettings}
                disabled={saving}
                data-testid="save-features-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Сохранение...' : 'Сохранить настройки'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Restaurant Info Tab */}
        <TabsContent value="restaurant" className="mt-6">
          <Card className="border-none shadow-md" data-testid="restaurant-card">
            <CardHeader>
              <CardTitle className="font-heading">Информация о ресторане</CardTitle>
              <CardDescription>Основные данные вашего заведения</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Название</Label>
                  <Input
                    value={restaurantForm.name || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, name: e.target.value })}
                    placeholder="Название ресторана"
                    data-testid="restaurant-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Слоган</Label>
                  <Input
                    value={restaurantForm.slogan || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, slogan: e.target.value })}
                    placeholder="Короткий слоган"
                    data-testid="restaurant-slogan-input"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Описание</Label>
                <Textarea
                  value={restaurantForm.description || ''}
                  onChange={(e) => setRestaurantForm({ ...restaurantForm, description: e.target.value })}
                  placeholder="Описание ресторана"
                  rows={3}
                  data-testid="restaurant-description-input"
                />
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Адрес</Label>
                  <Input
                    value={restaurantForm.address || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, address: e.target.value })}
                    placeholder="Адрес"
                    data-testid="restaurant-address-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Телефон</Label>
                  <Input
                    value={restaurantForm.phone || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, phone: e.target.value })}
                    placeholder="+375 (29) 123-45-67"
                    data-testid="restaurant-phone-input"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={restaurantForm.email || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, email: e.target.value })}
                    placeholder="info@restaurant.by"
                    data-testid="restaurant-email-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Режим работы</Label>
                  <Input
                    value={restaurantForm.working_hours || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, working_hours: e.target.value })}
                    placeholder="Пн-Вс: 12:00 - 02:00"
                    data-testid="restaurant-hours-input"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>URL логотипа</Label>
                <Input
                  value={restaurantForm.logo_url || ''}
                  onChange={(e) => setRestaurantForm({ ...restaurantForm, logo_url: e.target.value })}
                  placeholder="https://..."
                  data-testid="restaurant-logo-input"
                />
              </div>

              <Button 
                className="w-full mt-4 bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={handleSaveRestaurant}
                disabled={saving}
                data-testid="save-restaurant-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Сохранение...' : 'Сохранить информацию'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Menu Sections Tab */}
        <TabsContent value="menu-sections" className="mt-6">
          <Card className="border-none shadow-md" data-testid="menu-sections-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading">Разделы меню</CardTitle>
                <CardDescription>Блоки меню для клиентов (Гастрономическое, Барное, Кальянное)</CardDescription>
              </div>
              <Button 
                className="bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={() => openSectionDialog()}
                data-testid="add-section-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить раздел
              </Button>
            </CardHeader>
            <CardContent>
              {menuSections.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Разделы меню не созданы
                </div>
              ) : (
                <div className="space-y-3">
                  {menuSections.map((section) => (
                    <div key={section.id} className="flex items-center justify-between p-4 rounded-xl bg-muted/50" data-testid={`section-${section.id}`}>
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-mint-100 dark:bg-mint-900/30 flex items-center justify-center">
                          <Layers className="w-5 h-5 text-mint-500" />
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">{section.name}</h4>
                          <p className="text-sm text-muted-foreground">Порядок: {section.sort_order}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs ${section.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
                          {section.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openSectionDialog(section)}
                          data-testid={`edit-section-${section.id}`}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-destructive"
                          onClick={() => deleteSection(section.id)}
                          data-testid={`delete-section-${section.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Call Types Tab */}
        <TabsContent value="call-types" className="mt-6">
          <Card className="border-none shadow-md" data-testid="call-types-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading">Типы вызовов</CardTitle>
                <CardDescription>Варианты для кнопки "Вызов" в клиентском меню</CardDescription>
              </div>
              <Button 
                className="bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={() => openCallTypeDialog()}
                data-testid="add-call-type-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить тип
              </Button>
            </CardHeader>
            <CardContent>
              {callTypes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Типы вызовов не созданы
                </div>
              ) : (
                <div className="space-y-3">
                  {callTypes.map((callType) => (
                    <div key={callType.id} className="flex items-center justify-between p-4 rounded-xl bg-muted/50" data-testid={`call-type-${callType.id}`}>
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                          <Bell className="w-5 h-5 text-amber-500" />
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">{callType.name}</h4>
                          {callType.telegram_message && (
                            <p className="text-sm text-muted-foreground truncate max-w-xs">{callType.telegram_message}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 rounded-full text-xs ${callType.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
                          {callType.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openCallTypeDialog(callType)}
                          data-testid={`edit-call-type-${callType.id}`}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-destructive"
                          onClick={() => deleteCallType(callType.id)}
                          data-testid={`delete-call-type-${callType.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tables Tab */}
        <TabsContent value="tables" className="mt-6">
          <Card className="border-none shadow-md" data-testid="tables-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading">Управление столами</CardTitle>
                <CardDescription>QR-коды и ссылки для каждого стола</CardDescription>
              </div>
              <Button 
                className="bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={() => openTableDialog()}
                data-testid="add-table-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить стол
              </Button>
            </CardHeader>
            <CardContent>
              {tables.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Столы ещё не добавлены
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>№</TableHead>
                      <TableHead>Название</TableHead>
                      <TableHead>Код</TableHead>
                      <TableHead>Статус</TableHead>
                      <TableHead className="text-right">Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tables.map((table) => (
                      <TableRow key={table.id} data-testid={`table-row-${table.id}`}>
                        <TableCell className="font-semibold">{table.number}</TableCell>
                        <TableCell>{table.name || `Стол ${table.number}`}</TableCell>
                        <TableCell>
                          <code className="bg-muted px-2 py-1 rounded text-sm">{table.code}</code>
                        </TableCell>
                        <TableCell>
                          <span className={`px-2 py-1 rounded-full text-xs ${table.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
                            {table.is_active ? 'Активен' : 'Неактивен'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 gap-1 px-2 text-xs font-medium"
                              onClick={() => showQrCode(table)}
                              title="QR-код"
                              data-testid={`qr-code-${table.id}`}
                            >
                              <QrCode className="w-3.5 h-3.5" />
                              QR
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => copyTableLink(table.code)}
                              title="Копировать ссылку"
                              data-testid={`copy-link-${table.id}`}
                            >
                              <Copy className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => window.open(`/menu/${table.code}`, '_blank')}
                              title="Открыть меню"
                              data-testid={`open-menu-${table.id}`}
                            >
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => regenerateTableCode(table.id)}
                              title="Обновить код"
                              data-testid={`regenerate-code-${table.id}`}
                            >
                              <RefreshCw className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => openTableDialog(table)}
                              data-testid={`edit-table-${table.id}`}
                            >
                              <Edit2 className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 hover:text-destructive"
                              onClick={() => deleteTable(table.id)}
                              data-testid={`delete-table-${table.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Employees Tab */}
        <TabsContent value="employees" className="mt-6">
          <Card className="border-none shadow-md" data-testid="employees-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading">Сотрудники</CardTitle>
                <CardDescription>Управление персоналом ресторана</CardDescription>
              </div>
              <Button 
                className="bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={() => openEmployeeDialog()}
                data-testid="add-employee-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Добавить сотрудника
              </Button>
            </CardHeader>
            <CardContent>
              {employees.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Сотрудники ещё не добавлены
                </div>
              ) : (
                <div className="grid gap-4">
                  {employees.map((emp) => (
                    <div key={emp.id} className="flex items-center justify-between p-4 rounded-xl bg-muted/50" data-testid={`employee-${emp.id}`}>
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-brown-100 dark:bg-brown-900/30 flex items-center justify-center">
                          <span className="font-semibold text-brown-600 dark:text-brown-400">
                            {emp.name.charAt(0)}
                          </span>
                        </div>
                        <div>
                          <h4 className="font-medium text-foreground">{emp.name}</h4>
                          <p className="text-sm text-muted-foreground">{emp.role}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {emp.telegram_id && (
                          <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-2 py-1 rounded">
                            Telegram
                          </span>
                        )}
                        <span className={`px-2 py-1 rounded-full text-xs ${emp.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}>
                          {emp.is_active ? 'Активен' : 'Неактивен'}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => openEmployeeDialog(emp)}
                          data-testid={`edit-employee-${emp.id}`}
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-destructive"
                          onClick={() => deleteEmployee(emp.id)}
                          data-testid={`delete-employee-${emp.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Integrations Tab */}
        <TabsContent value="integrations" className="mt-6">
          <Card className="border-none shadow-md" data-testid="integrations-card">
            <CardHeader>
              <CardTitle className="font-heading">Интеграции</CardTitle>
              <CardDescription>Подключение внешних сервисов</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 rounded-xl border border-border">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-blue-500" />
                  </div>
                  <div>
                    <h4 className="font-heading font-semibold">Telegram Bot</h4>
                    <p className="text-sm text-muted-foreground">Уведомления о заказах и вызовах</p>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Bot Token</Label>
                    <Input
                      type="password"
                      value={settingsForm.telegram_bot_token || ''}
                      onChange={(e) => setSettingsForm({ ...settingsForm, telegram_bot_token: e.target.value })}
                      placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                      data-testid="telegram-token-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Chat ID</Label>
                    <Input
                      value={settingsForm.telegram_chat_id || ''}
                      onChange={(e) => setSettingsForm({ ...settingsForm, telegram_chat_id: e.target.value })}
                      placeholder="-1001234567890"
                      data-testid="telegram-chat-input"
                    />
                  </div>
                </div>
              </div>

              <Button 
                className="w-full bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={handleSaveSettings}
                disabled={saving}
                data-testid="save-integrations-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Сохранение...' : 'Сохранить интеграции'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Appearance Tab */}
        <TabsContent value="appearance" className="mt-6">
          <Card className="border-none shadow-md" data-testid="appearance-card">
            <CardHeader>
              <CardTitle className="font-heading">Оформление</CardTitle>
              <CardDescription>Настройки внешнего вида</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between py-3 border-b border-border">
                <div className="flex items-center gap-3">
                  {theme === 'light' ? (
                    <Sun className="w-5 h-5 text-amber-500" />
                  ) : (
                    <Moon className="w-5 h-5 text-blue-500" />
                  )}
                  <div>
                    <Label className="text-base font-medium">Тёмная тема</Label>
                    <p className="text-sm text-muted-foreground">
                      {theme === 'light' ? 'Светлая тема активна' : 'Тёмная тема активна'}
                    </p>
                  </div>
                </div>
                <Switch
                  checked={theme === 'dark'}
                  onCheckedChange={handleThemeToggle}
                  data-testid="theme-switch"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Основной цвет</Label>
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-10 h-10 rounded-lg border border-border"
                      style={{ backgroundColor: settingsForm.primary_color || '#5DA9A4' }}
                    />
                    <Input
                      value={settingsForm.primary_color || '#5DA9A4'}
                      onChange={(e) => setSettingsForm({ ...settingsForm, primary_color: e.target.value })}
                      placeholder="#5DA9A4"
                      data-testid="primary-color-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Дополнительный цвет</Label>
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-10 h-10 rounded-lg border border-border"
                      style={{ backgroundColor: settingsForm.secondary_color || '#8D6E63' }}
                    />
                    <Input
                      value={settingsForm.secondary_color || '#8D6E63'}
                      onChange={(e) => setSettingsForm({ ...settingsForm, secondary_color: e.target.value })}
                      placeholder="#8D6E63"
                      data-testid="secondary-color-input"
                    />
                  </div>
                </div>
              </div>

              <Button 
                className="w-full bg-mint-500 hover:bg-mint-600 rounded-full"
                onClick={handleSaveSettings}
                disabled={saving}
                data-testid="save-appearance-btn"
              >
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Сохранение...' : 'Сохранить оформление'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Table Dialog */}
      <Dialog open={tableDialogOpen} onOpenChange={setTableDialogOpen}>
        <DialogContent data-testid="table-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingTable ? 'Редактировать стол' : 'Новый стол'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Номер стола</Label>
              <Input
                type="number"
                value={tableForm.number}
                onChange={(e) => setTableForm({ ...tableForm, number: e.target.value })}
                data-testid="table-number-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Название (опционально)</Label>
              <Input
                value={tableForm.name}
                onChange={(e) => setTableForm({ ...tableForm, name: e.target.value })}
                placeholder="Например: VIP зона"
                data-testid="table-name-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={tableForm.is_active}
                onCheckedChange={(checked) => setTableForm({ ...tableForm, is_active: checked })}
                data-testid="table-active-switch"
              />
              <Label>Активен</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTableDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveTableHandler}
              className="bg-mint-500 hover:bg-mint-600"
              data-testid="save-table-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Employee Dialog */}
      <Dialog open={employeeDialogOpen} onOpenChange={setEmployeeDialogOpen}>
        <DialogContent data-testid="employee-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingEmployee ? 'Редактировать сотрудника' : 'Новый сотрудник'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Имя</Label>
              <Input
                value={employeeForm.name}
                onChange={(e) => setEmployeeForm({ ...employeeForm, name: e.target.value })}
                placeholder="Иван Петров"
                data-testid="employee-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Должность</Label>
              <Input
                value={employeeForm.role}
                onChange={(e) => setEmployeeForm({ ...employeeForm, role: e.target.value })}
                placeholder="Официант"
                data-testid="employee-role-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Telegram ID (для уведомлений)</Label>
              <Input
                value={employeeForm.telegram_id}
                onChange={(e) => setEmployeeForm({ ...employeeForm, telegram_id: e.target.value })}
                placeholder="123456789"
                data-testid="employee-telegram-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={employeeForm.is_active}
                onCheckedChange={(checked) => setEmployeeForm({ ...employeeForm, is_active: checked })}
                data-testid="employee-active-switch"
              />
              <Label>Активен</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEmployeeDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveEmployeeHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!employeeForm.name || !employeeForm.role}
              data-testid="save-employee-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Menu Section Dialog */}
      <Dialog open={sectionDialogOpen} onOpenChange={setSectionDialogOpen}>
        <DialogContent data-testid="section-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingSection ? 'Редактировать раздел' : 'Новый раздел меню'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название</Label>
              <Input
                value={sectionForm.name}
                onChange={(e) => setSectionForm({ ...sectionForm, name: e.target.value })}
                placeholder="Например: Барное меню"
                data-testid="section-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Порядок сортировки</Label>
              <Input
                type="number"
                value={sectionForm.sort_order}
                onChange={(e) => setSectionForm({ ...sectionForm, sort_order: parseInt(e.target.value) || 0 })}
                data-testid="section-sort-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={sectionForm.is_active}
                onCheckedChange={(checked) => setSectionForm({ ...sectionForm, is_active: checked })}
                data-testid="section-active-switch"
              />
              <Label>Активен</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSectionDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveSectionHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!sectionForm.name}
              data-testid="save-section-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Call Type Dialog */}
      <Dialog open={callTypeDialogOpen} onOpenChange={setCallTypeDialogOpen}>
        <DialogContent data-testid="call-type-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingCallType ? 'Редактировать тип вызова' : 'Новый тип вызова'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название</Label>
              <Input
                value={callTypeForm.name}
                onChange={(e) => setCallTypeForm({ ...callTypeForm, name: e.target.value })}
                placeholder="Например: Вызов официанта"
                data-testid="call-type-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Сообщение для Telegram</Label>
              <Textarea
                value={callTypeForm.telegram_message}
                onChange={(e) => setCallTypeForm({ ...callTypeForm, telegram_message: e.target.value })}
                placeholder="🔔 Стол #{table} - Вызов официанта"
                rows={2}
                data-testid="call-type-message-input"
              />
              <p className="text-xs text-muted-foreground">Используйте {'{table}'} для номера стола</p>
            </div>
            <div className="space-y-2">
              <Label>Порядок сортировки</Label>
              <Input
                type="number"
                value={callTypeForm.sort_order}
                onChange={(e) => setCallTypeForm({ ...callTypeForm, sort_order: parseInt(e.target.value) || 0 })}
                data-testid="call-type-sort-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={callTypeForm.is_active}
                onCheckedChange={(checked) => setCallTypeForm({ ...callTypeForm, is_active: checked })}
                data-testid="call-type-active-switch"
              />
              <Label>Активен</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCallTypeDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveCallTypeHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!callTypeForm.name}
              data-testid="save-call-type-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* QR Code Dialog */}
      <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
        <DialogContent className="max-w-md" data-testid="qr-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading text-center">
              QR-код для стола
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {qrLoading ? (
              <div className="flex flex-col items-center gap-4 py-8">
                <Loader2 className="w-12 h-12 text-mint-500 animate-spin" />
                <p className="text-muted-foreground">Генерация QR-кода...</p>
              </div>
            ) : qrData ? (
              <div className="flex flex-col items-center gap-4">
                <div className="text-center mb-2">
                  <h3 className="text-xl font-semibold">Стол №{qrData.table_number}</h3>
                  <p className="text-sm text-muted-foreground">Код: {qrData.table_code}</p>
                </div>
                
                <div className="bg-white p-4 rounded-xl shadow-lg">
                  <img 
                    src={qrData.qr_base64} 
                    alt={`QR код для стола ${qrData.table_number}`}
                    className="w-64 h-64"
                  />
                </div>
                
                <p className="text-xs text-muted-foreground text-center max-w-xs">
                  Отсканируйте QR-код камерой телефона для перехода в меню
                </p>
                
                <div className="text-xs text-muted-foreground bg-muted px-3 py-2 rounded-lg break-all">
                  {qrData.menu_url}
                </div>
              </div>
            ) : null}
          </div>
          <DialogFooter className="flex gap-2">
            <Button variant="outline" onClick={() => setQrDialogOpen(false)}>
              Закрыть
            </Button>
            <Button 
              className="bg-mint-500 hover:bg-mint-600"
              onClick={downloadQrCode}
              disabled={!qrData}
              data-testid="download-qr-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              Скачать PNG
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

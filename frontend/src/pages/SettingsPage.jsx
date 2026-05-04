import { useState, useEffect, useRef } from 'react';
import { Settings as SettingsIcon, Palette, Building2, QrCode, Plus, Trash2, RefreshCw, Copy, ExternalLink, Users, Save, Moon, Sun, Bell, Layers, Edit2, Download, Loader2, Link, Megaphone, Upload as UploadIcon, Image as ImageIcon, FileDown, Languages, Sparkles, CheckCircle2 } from 'lucide-react';
import ImageCropDialog from '@/components/ImageCropDialog';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { SUPPORTED_CURRENCIES } from '@/lib/currency';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
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
  
  const [tableForm, setTableForm] = useState({ number: '', name: '', is_active: true, is_preorder: false, is_delivery: false, is_website: false });
  const [employeeForm, setEmployeeForm] = useState({ name: '', role: '', telegram_id: '', is_active: true });
  const [sectionForm, setSectionForm] = useState({ name: '', sort_order: 0, is_active: true });
  const [callTypeForm, setCallTypeForm] = useState({ name: '', telegram_message: '', sort_order: 0, is_active: true });
  
  const [qrData, setQrData] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [splashUploading, setSplashUploading] = useState(false);
  const [cropOpen, setCropOpen] = useState(false);
  const [rawImageSrc, setRawImageSrc] = useState(null);

  // Splash Ads (multiple)
  const [splashAds, setSplashAds] = useState([]);
  const [adDialogOpen, setAdDialogOpen] = useState(false);
  const [editingAd, setEditingAd] = useState(null);
  const emptyAd = { title: '', text: '', image_url: '', button_text: 'Перейти к меню', link_text: '', link_url: '', fit_mode: 'contain', is_active: true, sort_order: 0 };
  const [adForm, setAdForm] = useState(emptyAd);

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

  const handleSplashImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // Read file as data URL and open cropper
    const reader = new FileReader();
    reader.onload = (evt) => {
      setRawImageSrc(evt.target.result);
      setCropOpen(true);
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleCroppedImageUpload = async (blob) => {
    setSplashUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', blob, 'splash.jpg');
      const resp = await axios.post(`${API}/upload`, fd, {
        headers: { ...authHeaders.headers, 'Content-Type': 'multipart/form-data' },
      });
      const url = `${BACKEND_URL}${resp.data.url}`;
      setAdForm((prev) => ({ ...prev, image_url: url }));
      toast.success('Изображение загружено');
      setCropOpen(false);
      setRawImageSrc(null);
    } catch {
      toast.error('Ошибка загрузки');
    } finally {
      setSplashUploading(false);
    }
  };

  const fetchSplashAds = async () => {
    if (!currentRestaurantId) return;
    try {
      const r = await axios.get(`${API}/restaurants/${currentRestaurantId}/splash-ads`, authHeaders);
      setSplashAds(r.data || []);
    } catch { /* silent */ }
  };

  useEffect(() => { fetchSplashAds(); /* eslint-disable-next-line */ }, [currentRestaurantId]);

  const openAddAdDialog = () => {
    setEditingAd(null);
    setAdForm({ ...emptyAd, sort_order: splashAds.length });
    setAdDialogOpen(true);
  };

  const openEditAdDialog = (ad) => {
    setEditingAd(ad);
    setAdForm({ ...emptyAd, ...ad });
    setAdDialogOpen(true);
  };

  const saveAd = async () => {
    try {
      if (editingAd) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/splash-ads/${editingAd.id}`, adForm, authHeaders);
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/splash-ads`, adForm, authHeaders);
      }
      toast.success('Заставка сохранена');
      setAdDialogOpen(false);
      fetchSplashAds();
    } catch {
      toast.error('Ошибка сохранения');
    }
  };

  const deleteAd = async (ad) => {
    if (!window.confirm(`Удалить заставку «${ad.title || 'без названия'}»?`)) return;
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/splash-ads/${ad.id}`, authHeaders);
      toast.success('Удалено');
      fetchSplashAds();
    } catch {
      toast.error('Ошибка удаления');
    }
  };

  const toggleAdActive = async (ad) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/splash-ads/${ad.id}`, { is_active: !ad.is_active }, authHeaders);
      fetchSplashAds();
    } catch {
      toast.error('Ошибка');
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
      setTableForm({ number: table.number, name: table.name || '', is_active: table.is_active, is_preorder: !!table.is_preorder, is_delivery: !!table.is_delivery, is_website: !!table.is_website });
    } else {
      setEditingTable(null);
      setTableForm({ number: tables.length + 1, name: '', is_active: true, is_preorder: false, is_delivery: false, is_website: false });
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

  const getTableUrl = (table) => {
    const slug = restaurant?.slug;
    if (slug) {
      return `${window.location.origin}/${slug}/${table.number}`;
    }
    return `${window.location.origin}/menu/${table.code}`;
  };

  const copyTableLink = (table) => {
    const link = getTableUrl(table);
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

  const downloadQrPdf = async (size) => {
    if (!qrData) return;
    try {
      const baseUrl = window.location.origin;
      const resp = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/tables/${qrData.table_id}/qr-pdf?size=${size}&base_url=${encodeURIComponent(baseUrl)}`,
        { ...authHeaders, responseType: 'blob' }
      );
      const url = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `qr_table_${qrData.table_number}_${size}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(`PDF (${size.toUpperCase()}) скачан`);
    } catch (e) {
      toast.error('Не удалось сформировать PDF');
    }
  };

  const downloadShareCard = async (fmt) => {
    if (!qrData) return;
    try {
      const baseUrl = window.location.origin;
      const resp = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/tables/${qrData.table_id}/share-card?fmt=${fmt}&base_url=${encodeURIComponent(baseUrl)}`,
        { ...authHeaders, responseType: 'blob' }
      );
      const url = URL.createObjectURL(new Blob([resp.data], { type: 'image/png' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `share_qr_table_${qrData.table_number}_${fmt}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(`Карточка для соцсетей (${fmt === 'story' ? 'Stories 9:16' : 'квадрат 1:1'}) скачана`);
    } catch (e) {
      toast.error('Не удалось сформировать карточку');
    }
  };

  const [bulkPdfLoading, setBulkPdfLoading] = useState(false);
  const downloadAllQrPdf = async (size) => {
    setBulkPdfLoading(true);
    try {
      const baseUrl = window.location.origin;
      const resp = await axios.get(
        `${API}/restaurants/${currentRestaurantId}/tables/qr-pdf-all?size=${size}&base_url=${encodeURIComponent(baseUrl)}`,
        { ...authHeaders, responseType: 'blob' }
      );
      const url = URL.createObjectURL(new Blob([resp.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `qr_all_tables_${size}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success(`PDF со всеми столами (${size.toUpperCase()}) скачан`);
    } catch (e) {
      toast.error(e.response?.status === 404 ? 'У ресторана нет активных столов' : 'Не удалось сформировать PDF');
    } finally {
      setBulkPdfLoading(false);
    }
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
          <TabsTrigger value="appearance" className="gap-2" data-testid="tab-appearance">
            <Palette className="w-4 h-4" />
            Оформление
          </TabsTrigger>
          <TabsTrigger value="splash" className="gap-2" data-testid="tab-splash">
            <Megaphone className="w-4 h-4" />
            Заставка
          </TabsTrigger>
          <TabsTrigger value="i18n" className="gap-2" data-testid="tab-i18n">
            <Languages className="w-4 h-4" />
            Переводы
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
                <Label>Валюта</Label>
                <Select
                  value={restaurantForm.currency || 'BYN'}
                  onValueChange={(v) => setRestaurantForm({ ...restaurantForm, currency: v })}
                >
                  <SelectTrigger data-testid="restaurant-currency-select" className="md:w-[320px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SUPPORTED_CURRENCIES.map((c) => (
                      <SelectItem key={c.code} value={c.code}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">Используется во всех ценниках, чеках, аналитике и Telegram-дайджесте.</p>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Link className="w-4 h-4" />
                  URL-адрес меню (slug)
                </Label>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground whitespace-nowrap">{window.location.origin}/</span>
                  <Input
                    value={restaurantForm.slug || ''}
                    onChange={(e) => setRestaurantForm({ ...restaurantForm, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                    placeholder="my-restaurant"
                    data-testid="restaurant-slug-input"
                  />
                  <span className="text-sm text-muted-foreground whitespace-nowrap">/1</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Латинские буквы, цифры и дефис. Будет использоваться в URL клиентского меню и QR-кодах
                </p>
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
            <CardHeader className="flex flex-row items-center justify-between gap-2 flex-wrap">
              <div>
                <CardTitle className="font-heading">Управление столами</CardTitle>
                <CardDescription>QR-коды и ссылки для каждого стола</CardDescription>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => downloadAllQrPdf('a5')}
                  disabled={bulkPdfLoading || tables.length === 0}
                  data-testid="bulk-qr-pdf-a5-btn"
                >
                  {bulkPdfLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                  Все QR (A5)
                </Button>
                <Button
                  variant="outline"
                  className="rounded-full"
                  onClick={() => downloadAllQrPdf('a6')}
                  disabled={bulkPdfLoading || tables.length === 0}
                  data-testid="bulk-qr-pdf-a6-btn"
                >
                  {bulkPdfLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileDown className="w-4 h-4 mr-2" />}
                  Все QR (A6)
                </Button>
                <Button
                  className="bg-mint-500 hover:bg-mint-600 rounded-full"
                  onClick={() => openTableDialog()}
                  data-testid="add-table-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Добавить стол
                </Button>
              </div>
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
                        <TableCell>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span>{table.name || `Стол ${table.number}`}</span>
                            {table.is_website && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-mint-500/15 text-mint-700 dark:text-mint-300 border border-mint-500/30" data-testid={`table-website-badge-${table.id}`}>
                                САЙТ
                              </span>
                            )}
                            {table.is_preorder && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-purple-500/15 text-purple-700 dark:text-purple-300">
                                ПРЕДЗАКАЗ
                              </span>
                            )}
                            {table.is_delivery && (
                              <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-orange-500/15 text-orange-700 dark:text-orange-300">
                                ДОСТАВКА
                              </span>
                            )}
                          </div>
                        </TableCell>
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
                              onClick={() => copyTableLink(table)}
                              title="Копировать ссылку"
                              data-testid={`copy-link-${table.id}`}
                            >
                              <Copy className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => window.open(getTableUrl(table), '_blank')}
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

        {/* Splash Tab */}
        <TabsContent value="splash" className="mt-6">
          <Card className="border-none shadow-md" data-testid="splash-card">
            <CardHeader>
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <CardTitle className="font-heading">Рекламные заставки</CardTitle>
                  <CardDescription>
                    Создайте несколько заставок — гостю при открытии меню будет случайно показана одна из активных.
                  </CardDescription>
                </div>
                <Button className="rounded-full bg-mint-500 hover:bg-mint-600 text-white gap-2" onClick={openAddAdDialog} data-testid="add-splash-btn">
                  <Plus className="w-4 h-4" />Добавить
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {splashAds.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  <Megaphone className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>Заставок пока нет. Нажмите «Добавить», чтобы создать первую.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {splashAds.map((ad) => (
                    <div key={ad.id} className="flex items-center gap-3 p-3 border border-border rounded-2xl" data-testid={`splash-ad-${ad.id}`}>
                      <div className="w-20 h-20 rounded-xl bg-muted flex-shrink-0 overflow-hidden flex items-center justify-center">
                        {ad.image_url ? (
                          <img src={ad.image_url} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <ImageIcon className="w-8 h-8 text-muted-foreground/40" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{ad.title || <span className="text-muted-foreground italic">Без названия</span>}</div>
                        <div className="text-xs text-muted-foreground line-clamp-2">{ad.text || '—'}</div>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${ad.is_active ? 'bg-mint-100 text-mint-700 dark:bg-mint-900/30 dark:text-mint-300' : 'bg-muted text-muted-foreground'}`}>
                            {ad.is_active ? 'Активна' : 'Отключена'}
                          </span>
                          {ad.link_text && <span className="text-xs text-muted-foreground">↗ {ad.link_text}</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <Switch checked={ad.is_active} onCheckedChange={() => toggleAdActive(ad)} data-testid={`toggle-splash-${ad.id}`} />
                        <Button variant="ghost" size="icon" onClick={() => openEditAdDialog(ad)} data-testid={`edit-splash-${ad.id}`}>
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="text-destructive hover:bg-destructive/10" onClick={() => deleteAd(ad)} data-testid={`delete-splash-${ad.id}`}>
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

        {/* I18N — Multilingual menu */}
        <TabsContent value="i18n" className="mt-6">
          <Card className="border-none shadow-md" data-testid="i18n-card">
            <CardHeader>
              <CardTitle className="font-heading flex items-center gap-2">
                <Languages className="w-5 h-5 text-mint-500" />
                Мультиязычность меню
              </CardTitle>
              <CardDescription>
                Гость в клиентском меню видит переключатель языка в шапке. Переводы блюд
                генерируются ИИ. Включайте только те языки, которые реально нужны вашим гостям —
                это уменьшит расход кредитов LLM.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="rounded-lg border bg-muted/30 p-4 text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-mint-500 mt-0.5 flex-shrink-0" />
                  <p className="text-muted-foreground">
                    <span className="font-semibold text-foreground">Когда срабатывает автоматически:</span>{' '}
                    при создании или редактировании блюда, категории или раздела меню — английский перевод
                    обновляется в фоне через несколько секунд.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <RefreshCw className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                  <p className="text-muted-foreground">
                    <span className="font-semibold text-foreground">Кнопка ниже</span> — для разового
                    запуска перевода всего меню (полезно сразу после импорта или для существующего ресторана).
                  </p>
                </div>
              </div>

              <LanguageToggles restaurantId={currentRestaurantId} token={token} />

              <I18nTranslateActions restaurantId={currentRestaurantId} token={token} />
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
            <div className="flex items-center gap-2">
              <Switch
                checked={!!tableForm.is_preorder}
                onCheckedChange={(checked) => setTableForm({ ...tableForm, is_preorder: checked, is_delivery: checked ? false : tableForm.is_delivery })}
                data-testid="table-preorder-switch"
              />
              <Label>Предзаказ (бронирование с указанием даты/времени)</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={!!tableForm.is_delivery}
                onCheckedChange={(checked) => setTableForm({ ...tableForm, is_delivery: checked, is_preorder: checked ? false : tableForm.is_preorder })}
                data-testid="table-delivery-switch"
              />
              <Label>Доставка (клиент вводит город, адрес, телефон)</Label>
            </div>
            <div className="flex items-start gap-2 rounded-lg border border-mint-500/30 bg-mint-500/5 p-2.5">
              <Switch
                checked={!!tableForm.is_website}
                onCheckedChange={(checked) => setTableForm({ ...tableForm, is_website: checked })}
                data-testid="table-website-switch"
              />
              <div className="flex-1">
                <Label>Стол «Сайт» (точка входа с домена)</Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Гость, набравший просто домен (например <code className="text-[11px]">catch-menu.by</code>), без кода стола — попадёт сюда. Обычно один стол на ресторан.
                </p>
              </div>
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
          <DialogFooter className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => setQrDialogOpen(false)}>
              Закрыть
            </Button>
            <Button
              variant="outline"
              onClick={downloadQrCode}
              disabled={!qrData}
              data-testid="download-qr-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              PNG
            </Button>
            <Button
              variant="outline"
              onClick={() => downloadQrPdf('a6')}
              disabled={!qrData}
              data-testid="download-qr-pdf-a6-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              PDF A6
            </Button>
            <Button
              className="bg-mint-500 hover:bg-mint-600"
              onClick={() => downloadQrPdf('a5')}
              disabled={!qrData}
              data-testid="download-qr-pdf-a5-btn"
            >
              <Download className="w-4 h-4 mr-2" />
              PDF A5
            </Button>
            <div className="w-full border-t my-1" />
            <div className="w-full text-xs text-muted-foreground -mb-1">
              Готовая карточка для соцсетей (с логотипом, QR и брендом)
            </div>
            <Button
              variant="outline"
              onClick={() => downloadShareCard('square')}
              disabled={!qrData}
              data-testid="download-share-card-square-btn"
              title="1080×1080 — для Instagram-постов, Telegram и WhatsApp"
            >
              <Download className="w-4 h-4 mr-2" />
              Соцсети 1:1
            </Button>
            <Button
              variant="outline"
              onClick={() => downloadShareCard('story')}
              disabled={!qrData}
              data-testid="download-share-card-story-btn"
              title="1080×1920 — для Instagram Stories / Reels"
            >
              <Download className="w-4 h-4 mr-2" />
              Stories 9:16
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ImageCropDialog
        open={cropOpen}
        onOpenChange={(o) => { setCropOpen(o); if (!o) setRawImageSrc(null); }}
        imageSrc={rawImageSrc}
        onCropDone={handleCroppedImageUpload}
        busy={splashUploading}
      />

      <Dialog open={adDialogOpen} onOpenChange={setAdDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="splash-ad-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">{editingAd ? 'Редактирование заставки' : 'Новая заставка'}</DialogTitle>
            <DialogDescription>
              Заполните поля. Гость случайно увидит одну из активных заставок при открытии меню.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Изображение / баннер</Label>
              <div className="flex flex-col sm:flex-row gap-3">
                {adForm.image_url ? (
                  <div className="relative">
                    <img src={adForm.image_url} alt="splash" className="w-full sm:w-48 h-32 object-cover rounded-xl border border-border" />
                    <Button size="icon" variant="destructive" className="absolute -top-2 -right-2 h-6 w-6 rounded-full" onClick={() => setAdForm({ ...adForm, image_url: '' })} data-testid="ad-image-remove">
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                ) : (
                  <div className="w-full sm:w-48 h-32 rounded-xl border border-dashed border-border bg-muted/30 flex items-center justify-center text-muted-foreground">
                    <ImageIcon className="w-8 h-8" />
                  </div>
                )}
                <div className="flex flex-col gap-2 flex-1">
                  <input type="file" accept="image/*" id="ad-image-file" className="hidden" onChange={handleSplashImageUpload} />
                  <Button variant="outline" className="rounded-full gap-2" onClick={() => document.getElementById('ad-image-file').click()} disabled={splashUploading} data-testid="ad-image-upload-btn">
                    {splashUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadIcon className="w-4 h-4" />}
                    {splashUploading ? 'Загрузка...' : 'Загрузить и обрезать'}
                  </Button>
                  <Input placeholder="или вставьте ссылку https://..." value={adForm.image_url || ''} onChange={(e) => setAdForm({ ...adForm, image_url: e.target.value })} />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Заголовок</Label>
                <Input value={adForm.title || ''} onChange={(e) => setAdForm({ ...adForm, title: e.target.value })} placeholder="Например: Подарок при заказе кальяна" data-testid="ad-title-input" />
              </div>
              <div className="space-y-2">
                <Label>Текст основной кнопки</Label>
                <Input value={adForm.button_text || ''} onChange={(e) => setAdForm({ ...adForm, button_text: e.target.value })} placeholder="Перейти к меню" data-testid="ad-button-input" />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Описание</Label>
              <Textarea rows={3} value={adForm.text || ''} onChange={(e) => setAdForm({ ...adForm, text: e.target.value })} placeholder="Расскажите про акцию..." data-testid="ad-text-input" />
            </div>

            <div className="space-y-2">
              <Label>Режим отображения</Label>
              <select value={adForm.fit_mode || 'contain'} onChange={(e) => setAdForm({ ...adForm, fit_mode: e.target.value })} className="w-full h-10 px-3 rounded-xl border border-border bg-background text-sm" data-testid="ad-fit-mode-select">
                <option value="contain">Целиком (без обрезки)</option>
                <option value="cover">Заполнить (с обрезкой)</option>
              </select>
            </div>

            <div className="border-t border-border pt-4">
              <Label className="text-sm font-medium mb-2 block">Дополнительная кнопка (необязательно)</Label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input value={adForm.link_text || ''} onChange={(e) => setAdForm({ ...adForm, link_text: e.target.value })} placeholder="Подписаться в Instagram" data-testid="ad-link-text-input" />
                <Input value={adForm.link_url || ''} onChange={(e) => setAdForm({ ...adForm, link_url: e.target.value })} placeholder="https://..." data-testid="ad-link-url-input" />
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-border pt-4">
              <Label className="font-medium">Активна (показывать гостям)</Label>
              <Switch checked={adForm.is_active} onCheckedChange={(v) => setAdForm({ ...adForm, is_active: v })} data-testid="ad-active-switch" />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setAdDialogOpen(false)}>Отмена</Button>
            <Button className="bg-mint-500 hover:bg-mint-600 text-white gap-2" onClick={saveAd} data-testid="save-splash-ad-btn">
              <Save className="w-4 h-4" />Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


// ============ Inline sub-component: language toggles ============

const LANGS_META = [
  { code: 'en', label: 'English', flag: '🇬🇧', note: 'Базовый язык для туристов' },
  { code: 'zh', label: '简体中文 (упр. китайский)', flag: '🇨🇳', note: 'Для гостей из КНР' },
];

function LanguageToggles({ restaurantId, token }) {
  const [enabled, setEnabled] = useState(['en']);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null); // lang code currently saving

  useEffect(() => {
    if (!restaurantId) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(`${API}/restaurants/${restaurantId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!cancelled) setEnabled(r.data?.enabled_languages || ['en']);
      } catch {
        // keep default
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [restaurantId, token]);

  const toggle = async (code) => {
    if (!restaurantId || saving) return;
    const next = enabled.includes(code)
      ? enabled.filter((x) => x !== code)
      : [...enabled, code];
    setSaving(code);
    try {
      await axios.put(
        `${API}/restaurants/${restaurantId}`,
        { enabled_languages: next },
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setEnabled(next);
      toast.success(
        enabled.includes(code)
          ? `Язык ${code.toUpperCase()} отключён — переключатель скрыт у гостей`
          : `Язык ${code.toUpperCase()} включён. Запустите перевод меню ниже, чтобы заполнить переводы.`,
      );
    } catch {
      toast.error('Не удалось обновить настройки языков');
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return <div className="text-sm text-muted-foreground">Загрузка настроек языков…</div>;
  }

  return (
    <div className="space-y-3" data-testid="language-toggles">
      <div className="text-sm font-semibold text-foreground">Доступные языки</div>
      {LANGS_META.map(({ code, label, flag, note }) => {
        const active = enabled.includes(code);
        const isSaving = saving === code;
        return (
          <button
            key={code}
            type="button"
            onClick={() => toggle(code)}
            disabled={isSaving}
            data-testid={`lang-toggle-${code}`}
            className={
              'w-full flex items-center justify-between gap-3 rounded-lg border p-3 transition-colors text-left disabled:opacity-60 ' +
              (active
                ? 'border-mint-500 bg-mint-500/5 hover:bg-mint-500/10'
                : 'border-border bg-muted/20 hover:bg-muted/40')
            }
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-2xl leading-none">{flag}</span>
              <div className="min-w-0">
                <div className="font-medium truncate">{label}</div>
                <div className="text-xs text-muted-foreground">{note}</div>
              </div>
            </div>
            <div
              className={
                'shrink-0 inline-flex items-center justify-center w-12 h-7 rounded-full text-[11px] font-semibold transition-colors ' +
                (active ? 'bg-mint-500 text-white' : 'bg-slate-200 text-slate-600')
              }
            >
              {isSaving ? '…' : active ? 'ON' : 'OFF'}
            </div>
          </button>
        );
      })}
      <p className="text-xs text-muted-foreground">
        Для русского ничего включать не нужно — он всегда базовый. Включение нового языка не
        переводит существующие блюда автоматически — после включения нажмите «Перевести всё
        меню» ниже.
      </p>
    </div>
  );
}


// ============ Inline sub-component: bulk translation panel ============

function I18nTranslateActions({ restaurantId, token }) {
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [force, setForce] = useState(false);
  const [targetLang, setTargetLang] = useState('all');
  // Polling: latest job from /translate-status, refreshed every 2s while running
  const [job, setJob] = useState(null);
  const pollRef = useRef(null);

  // Bootstrap: load latest job on mount so a refresh keeps showing progress
  useEffect(() => {
    if (!restaurantId) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await axios.get(
          `${API}/restaurants/${restaurantId}/translate-status`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        if (cancelled) return;
        if (r.data && r.data.id) {
          setJob(r.data);
          if (r.data.status === 'running') startPolling();
        }
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; stopPolling(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restaurantId, token]);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const startPolling = () => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const r = await axios.get(
          `${API}/restaurants/${restaurantId}/translate-status`,
          { headers: { Authorization: `Bearer ${token}` } },
        );
        const j = r.data;
        setJob(j);
        if (j?.status !== 'running') {
          stopPolling();
          if (j?.status === 'done') {
            const total = j.stats ? (j.stats.sections + j.stats.categories + j.stats.items) : 0;
            toast.success(`Перевод завершён — обработано ${total} объектов`);
          } else if (j?.status === 'error') {
            toast.error(`Ошибка перевода: ${j.error || 'unknown'}`, { duration: 10000 });
          }
        }
      } catch { /* keep polling */ }
    }, 2000);
  };

  const trigger = async () => {
    if (!restaurantId) return;
    setRunning(true);
    try {
      const params = new URLSearchParams();
      if (force) params.set('force', 'true');
      params.set('lang', targetLang);
      const r = await axios.post(
        `${API}/restaurants/${restaurantId}/translate-all?${params.toString()}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } },
      );
      setLastResult(r.data);
      const est = r.data?.estimate || {};
      const total = (est.sections || 0) + (est.categories || 0) + (est.items || 0);
      const langs = (r.data?.languages || []).join(', ').toUpperCase() || 'EN';
      if (total === 0) {
        toast.success(`Всё уже переведено (${langs})`);
      } else {
        toast.success(
          `Перевод запущен (${langs}) — ${total} объектов`,
        );
        // Reset job from previous run so the bar shows 0/N immediately
        setJob({
          status: 'running', phase: 'sections',
          total, done: 0,
          stats: { sections: 0, categories: 0, items: 0 },
          totals: est,
          languages: r.data?.languages || [],
          started_at: new Date().toISOString(),
        });
        startPolling();
      }
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (typeof detail === 'string') {
        toast.error(detail, { duration: 10000 });
        setLastResult({ error: detail });
      } else {
        toast.error('Не удалось запустить перевод');
      }
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Целевой язык</label>
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            data-testid="translate-lang-select"
            className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="all">Все включённые</option>
            <option value="en">🇬🇧 Английский</option>
            <option value="zh">🇨🇳 中文 (китайский)</option>
          </select>
        </div>

        <Button
          onClick={trigger}
          disabled={running || !restaurantId || job?.status === 'running'}
          className="bg-mint-500 hover:bg-mint-600 text-white gap-2"
          data-testid="translate-all-btn"
        >
          {running ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Запускаем...
            </>
          ) : job?.status === 'running' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Идёт перевод...
            </>
          ) : (
            <>
              <Languages className="w-4 h-4" />
              Перевести всё меню
            </>
          )}
        </Button>

        <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer h-10">
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
            className="rounded"
            data-testid="translate-force-checkbox"
          />
          Перезаписать существующие переводы
        </label>
      </div>

      {lastResult?.error && (
        <div className="rounded-lg border bg-rose-50 dark:bg-rose-900/10 border-rose-200 dark:border-rose-800/40 p-4">
          <div className="flex items-start gap-2">
            <Languages className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-900 dark:text-rose-100">Перевод не запустился</p>
              <p className="text-sm text-rose-700 dark:text-rose-300 mt-1 whitespace-pre-line">{lastResult.error}</p>
            </div>
          </div>
        </div>
      )}

      {job && (job.status === 'running' || job.status === 'done' || job.status === 'error') && (
        <TranslateProgress job={job} />
      )}
    </div>
  );
}

const PHASE_LABEL = {
  sections: 'Разделы',
  categories: 'Категории',
  items: 'Блюда',
  done: 'Готово',
};

function TranslateProgress({ job }) {
  const total = job.total || 1;
  const done = Math.min(job.done || 0, total);
  const pct = Math.round((done / total) * 100);
  const isRunning = job.status === 'running';
  const isDone = job.status === 'done';
  const isError = job.status === 'error';

  // Elapsed time
  const [elapsed, setElapsed] = useState('');
  useEffect(() => {
    if (!job.started_at) return;
    const startTs = new Date(job.started_at).getTime();
    const tick = () => {
      const endTs = job.finished_at ? new Date(job.finished_at).getTime() : Date.now();
      const sec = Math.max(0, Math.round((endTs - startTs) / 1000));
      const m = Math.floor(sec / 60);
      const s = sec % 60;
      setElapsed(m > 0 ? `${m}м ${s}с` : `${s}с`);
    };
    tick();
    if (isRunning) {
      const id = setInterval(tick, 1000);
      return () => clearInterval(id);
    }
  }, [job.started_at, job.finished_at, isRunning]);

  // ETA — naive: assume ~1.5s per remaining item (cache will accelerate)
  const remaining = Math.max(0, total - done);
  const etaSec = isRunning ? Math.ceil(remaining * 1.5 * (job.languages?.length || 1)) : 0;
  const etaText = etaSec > 60 ? `≈${Math.ceil(etaSec / 60)} мин` : `≈${etaSec} сек`;

  const colors = isError
    ? 'bg-rose-50 dark:bg-rose-900/10 border-rose-200 dark:border-rose-800/40'
    : isDone
      ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800/40'
      : 'bg-mint-50 dark:bg-mint-900/10 border-mint-200 dark:border-mint-800/40';

  return (
    <div className={`rounded-lg border p-4 space-y-3 ${colors}`} data-testid="translate-progress">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          {isRunning && <Loader2 className="w-5 h-5 animate-spin text-mint-600" />}
          {isDone && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
          {isError && <Languages className="w-5 h-5 text-rose-600" />}
          <div>
            <p className="font-semibold">
              {isRunning && `Идёт перевод — фаза «${PHASE_LABEL[job.phase] || job.phase}»`}
              {isDone && 'Перевод завершён'}
              {isError && 'Перевод прерван с ошибкой'}
            </p>
            <p className="text-xs text-muted-foreground">
              {(job.languages || []).map((l) => l.toUpperCase()).join(', ') || 'EN'}
              {' · '}
              прошло {elapsed}
              {isRunning && remaining > 0 && ` · осталось ${etaText}`}
            </p>
          </div>
        </div>
        <div className="text-2xl font-semibold tabular-nums" data-testid="translate-progress-pct">
          {pct}%
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-3 w-full rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${isError ? 'bg-rose-500' : isDone ? 'bg-emerald-500' : 'bg-mint-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <Stat
          label="Разделы"
          value={`${job.stats?.sections ?? 0} / ${job.totals?.sections ?? 0}`}
        />
        <Stat
          label="Категории"
          value={`${job.stats?.categories ?? 0} / ${job.totals?.categories ?? 0}`}
        />
        <Stat
          label="Блюда"
          value={`${job.stats?.items ?? 0} / ${job.totals?.items ?? 0}`}
        />
      </div>

      {isError && job.error && (
        <p className="text-sm text-rose-700 dark:text-rose-300 whitespace-pre-line">{job.error}</p>
      )}

      {isRunning && (
        <p className="text-xs text-muted-foreground">
          Можно закрыть страницу — прогресс восстановится при следующем входе.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md bg-white dark:bg-slate-900/50 px-3 py-2 border border-emerald-200/60 dark:border-emerald-800/30">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value ?? 0}</div>
    </div>
  );
}

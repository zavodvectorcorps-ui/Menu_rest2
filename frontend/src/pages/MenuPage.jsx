import { useState, useEffect, useRef } from 'react';
import { Plus, ImageIcon, Tag, Search, Image, Layers, Loader2, FileJson, Download } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';

import { SortableCategoryItem } from '@/components/menu/SortableCategoryItem';
import { SortableMenuItem } from '@/components/menu/SortableMenuItem';
import {
  CategoryDialog, ItemDialog, DeleteDialog,
  ImportJsonDialog, ImportModeDialog, LabelDialog,
} from '@/components/menu/MenuDialogs';

export default function MenuPage() {
  const [categories, setCategories] = useState([]);
  const [menuItems, setMenuItems] = useState([]);
  const [menuSections, setMenuSections] = useState([]);
  const [labels, setLabels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currency, setCurrency] = useState('BYN');
  
  // Dialog states
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importModeDialogOpen, setImportModeDialogOpen] = useState(false);
  const [labelDialogOpen, setLabelDialogOpen] = useState(false);
  
  // Form states
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [importJson, setImportJson] = useState('');
  const [importing, setImporting] = useState(false);
  const [pendingImportFile, setPendingImportFile] = useState(null);
  const [editingLabel, setEditingLabel] = useState(null);
  const [labelForm, setLabelForm] = useState({ name: '', color: '#ef4444' });
  const [downloadingImages, setDownloadingImages] = useState(false);
  const [caffestaProducts, setCaffestaProducts] = useState([]);
  
  const [categoryForm, setCategoryForm] = useState({ name: '', section_id: '', display_mode: 'card', sort_order: 0, is_active: true });
  const [itemForm, setItemForm] = useState({
    category_id: '', name: '', description: '', price: '', weight: '', image_url: '',
    is_available: true, is_business_lunch: false, is_promotion: false,
    is_hit: false, is_new: false, is_spicy: false, is_banner: false,
    sort_order: 0, label_ids: [], caffesta_product_id: ''
  });

  const jsonFileRef = useRef(null);
  const { currentRestaurantId, token } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    if (currentRestaurantId) fetchData();
  }, [currentRestaurantId]);

  const fetchData = async () => {
    if (!currentRestaurantId) return;
    try {
      const [categoriesRes, itemsRes, sectionsRes, settingsRes, labelsRes] = await Promise.all([
        axios.get(`${API}/restaurants/${currentRestaurantId}/categories`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/menu-items`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/menu-sections`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/settings`, authHeaders),
        axios.get(`${API}/restaurants/${currentRestaurantId}/labels`, authHeaders)
      ]);
      setCategories(categoriesRes.data);
      setMenuItems(itemsRes.data);
      setMenuSections(sectionsRes.data);
      setLabels(labelsRes.data);
      setCurrency(settingsRes.data?.currency || 'BYN');
      if (categoriesRes.data.length > 0 && !selectedCategory) {
        setSelectedCategory(categoriesRes.data[0].id);
      }
      // Load Caffesta products for mapping (non-blocking)
      try {
        const cafResp = await axios.get(`${API}/restaurants/${currentRestaurantId}/caffesta/products`, authHeaders);
        setCaffestaProducts(Array.isArray(cafResp.data) ? cafResp.data : []);
      } catch {
        // Caffesta not configured — ok, just no products
      }
    } catch {
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const getSectionName = (sectionId) => menuSections.find(s => s.id === sectionId)?.name || '';

  // Category DnD
  const handleCategoryDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = categories.findIndex(c => c.id === active.id);
      const newIndex = categories.findIndex(c => c.id === over.id);
      const newCategories = arrayMove(categories, oldIndex, newIndex);
      setCategories(newCategories);
      try {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/categories/reorder`, newCategories.map(c => c.id), authHeaders);
        toast.success('Порядок категорий сохранён');
      } catch { toast.error('Ошибка сохранения порядка'); fetchData(); }
    }
  };

  const handleItemDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const filtered = menuItems.filter(i => i.category_id === selectedCategory);
      const oldIndex = filtered.findIndex(i => i.id === active.id);
      const newIndex = filtered.findIndex(i => i.id === over.id);
      const reordered = arrayMove(filtered, oldIndex, newIndex);
      const others = menuItems.filter(i => i.category_id !== selectedCategory);
      setMenuItems([...others, ...reordered]);
      try {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/menu-items/reorder`, reordered.map(i => i.id), authHeaders);
        toast.success('Порядок позиций сохранён');
      } catch { toast.error('Ошибка сохранения порядка'); fetchData(); }
    }
  };

  // Category CRUD
  const openCategoryDialog = (category = null) => {
    if (category) {
      setEditingCategory(category);
      setCategoryForm({ name: category.name, section_id: category.section_id || '', display_mode: category.display_mode || 'card', sort_order: category.sort_order, is_active: category.is_active });
    } else {
      setEditingCategory(null);
      setCategoryForm({ name: '', section_id: menuSections[0]?.id || '', display_mode: 'card', sort_order: categories.length, is_active: true });
    }
    setCategoryDialogOpen(true);
  };

  const saveCategoryHandler = async () => {
    try {
      const data = { ...categoryForm, section_id: categoryForm.section_id || null };
      if (editingCategory) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/categories/${editingCategory.id}`, data, authHeaders);
        toast.success('Категория обновлена');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/categories`, data, authHeaders);
        toast.success('Категория создана');
      }
      setCategoryDialogOpen(false);
      fetchData();
    } catch { toast.error('Ошибка сохранения категории'); }
  };

  const quickToggleCategoryActive = async (category) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/categories/${category.id}`, { is_active: !category.is_active }, authHeaders);
      fetchData();
    } catch { toast.error('Ошибка'); }
  };

  const quickToggleCategoryDisplay = async (category) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/categories/${category.id}`, { display_mode: category.display_mode === 'card' ? 'compact' : 'card' }, authHeaders);
      fetchData();
    } catch { toast.error('Ошибка'); }
  };

  // Item CRUD
  const openItemDialog = (item = null, isBanner = false) => {
    if (item) {
      setEditingItem(item);
      setItemForm({
        category_id: item.category_id, name: item.name, description: item.description || '',
        price: item.price?.toString() || '0', weight: item.weight || '', image_url: item.image_url || '',
        is_available: item.is_available, is_business_lunch: item.is_business_lunch,
        is_promotion: item.is_promotion, is_hit: item.is_hit, is_new: item.is_new,
        is_spicy: item.is_spicy, is_banner: item.is_banner, sort_order: item.sort_order,
        label_ids: item.label_ids || [], caffesta_product_id: item.caffesta_product_id ?? ''
      });
    } else {
      setEditingItem(null);
      setItemForm({
        category_id: selectedCategory || '', name: '', description: '', price: '0', weight: '',
        image_url: '', is_available: true, is_business_lunch: false, is_promotion: false,
        is_hit: false, is_new: false, is_spicy: false, is_banner: isBanner,
        sort_order: menuItems.filter(i => i.category_id === selectedCategory).length, label_ids: [],
        caffesta_product_id: ''
      });
    }
    setItemDialogOpen(true);
  };

  const saveItemHandler = async () => {
    try {
      const data = {
        ...itemForm,
        price: parseFloat(itemForm.price) || 0,
        sort_order: parseInt(itemForm.sort_order) || 0,
        caffesta_product_id: itemForm.caffesta_product_id ? parseInt(itemForm.caffesta_product_id) : null
      };
      if (editingItem) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/menu-items/${editingItem.id}`, data, authHeaders);
        toast.success('Позиция обновлена');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/menu-items`, data, authHeaders);
        toast.success('Позиция добавлена');
      }
      setItemDialogOpen(false);
      fetchData();
    } catch { toast.error('Ошибка сохранения позиции'); }
  };

  // Delete
  const openDeleteDialog = (target, type) => { setDeleteTarget({ ...target, type }); setDeleteDialogOpen(true); };

  const confirmDelete = async () => {
    try {
      if (deleteTarget.type === 'category') {
        await axios.delete(`${API}/restaurants/${currentRestaurantId}/categories/${deleteTarget.id}`, authHeaders);
        toast.success('Категория удалена');
        if (selectedCategory === deleteTarget.id) setSelectedCategory(categories.find(c => c.id !== deleteTarget.id)?.id || null);
      } else {
        await axios.delete(`${API}/restaurants/${currentRestaurantId}/menu-items/${deleteTarget.id}`, authHeaders);
        toast.success('Позиция удалена');
      }
      setDeleteDialogOpen(false);
      fetchData();
    } catch { toast.error('Ошибка удаления'); }
  };

  const toggleItemAvailability = async (item) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/menu-items/${item.id}`, { is_available: !item.is_available }, authHeaders);
      fetchData();
      toast.success(item.is_available ? 'Позиция скрыта' : 'Позиция доступна');
    } catch { toast.error('Ошибка обновления'); }
  };

  const toggleItemLabel = (labelId) => {
    setItemForm(prev => ({
      ...prev,
      label_ids: prev.label_ids.includes(labelId) ? prev.label_ids.filter(id => id !== labelId) : [...prev.label_ids, labelId]
    }));
  };

  // Import
  const handleImportFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingImportFile(file);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'json') {
      const reader = new FileReader();
      reader.onload = (event) => {
        try { JSON.parse(event.target.result); setImportJson(event.target.result); }
        catch { toast.error('Неверный формат JSON файла'); setPendingImportFile(null); return; }
        setImportModeDialogOpen(true);
      };
      reader.readAsText(file);
    } else {
      setImportModeDialogOpen(true);
    }
    e.target.value = '';
  };

  const executeImport = async (mode) => {
    setImportModeDialogOpen(false);
    const file = pendingImportFile;
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (ext === 'json' && importJson) {
      let jsonData;
      try { jsonData = JSON.parse(importJson); } catch { toast.error('Неверный формат JSON'); return; }
      setImporting(true);
      try {
        const response = await axios.post(`${API}/restaurants/${currentRestaurantId}/import-menu`, { data: jsonData, mode }, authHeaders);
        toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
        setImportJson(''); setSelectedCategory(null); fetchData();
      } catch (error) { toast.error(error.response?.data?.detail || 'Ошибка импорта'); }
      finally { setImporting(false); setPendingImportFile(null); }
    } else {
      setImporting(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(`${API}/restaurants/${currentRestaurantId}/import-file?mode=${mode}`, formData, { headers: { ...authHeaders.headers, 'Content-Type': 'multipart/form-data' } });
        toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
        setSelectedCategory(null); fetchData();
      } catch (error) { toast.error(error.response?.data?.detail || 'Ошибка импорта файла'); }
      finally { setImporting(false); setPendingImportFile(null); }
    }
  };

  const handleImportMenu = async () => {
    if (!importJson.trim()) { toast.error('Введите JSON данные'); return; }
    let jsonData;
    try { jsonData = JSON.parse(importJson); } catch { toast.error('Неверный формат JSON'); return; }
    setImporting(true);
    try {
      const response = await axios.post(`${API}/restaurants/${currentRestaurantId}/import-menu`, { data: jsonData, mode: 'append' }, authHeaders);
      toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
      setImportDialogOpen(false); setImportJson(''); fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Ошибка импорта'); }
    finally { setImporting(false); }
  };

  // Labels
  const openLabelDialog = () => { setEditingLabel(null); setLabelForm({ name: '', color: '#ef4444' }); setLabelDialogOpen(true); };

  const saveLabelHandler = async () => {
    if (!labelForm.name.trim()) return;
    try {
      if (editingLabel) {
        await axios.put(`${API}/restaurants/${currentRestaurantId}/labels/${editingLabel.id}`, labelForm, authHeaders);
        toast.success('Ярлык обновлён');
      } else {
        await axios.post(`${API}/restaurants/${currentRestaurantId}/labels`, labelForm, authHeaders);
        toast.success('Ярлык создан');
      }
      setLabelDialogOpen(false); fetchData();
    } catch { toast.error('Ошибка сохранения ярлыка'); }
  };

  const deleteLabelHandler = async (labelId) => {
    try { await axios.delete(`${API}/restaurants/${currentRestaurantId}/labels/${labelId}`, authHeaders); toast.success('Ярлык удалён'); fetchData(); }
    catch { toast.error('Ошибка удаления'); }
  };

  // Download images
  const downloadAllImages = async () => {
    setDownloadingImages(true);
    try {
      const resp = await axios.post(`${API}/restaurants/${currentRestaurantId}/download-images`, {}, authHeaders);
      toast.success(resp.data.message);
      if (resp.data.total > 0) {
        const interval = setInterval(async () => {
          const items = await axios.get(`${API}/restaurants/${currentRestaurantId}/menu-items`, authHeaders);
          if (!items.data.some(i => i.image_url?.startsWith('http'))) {
            clearInterval(interval); setDownloadingImages(false);
            toast.success('Все фотографии перенесены на сервер!'); fetchData();
          }
        }, 10000);
        setTimeout(() => { clearInterval(interval); setDownloadingImages(false); fetchData(); }, 300000);
      } else { setDownloadingImages(false); }
    } catch { toast.error('Ошибка скачивания изображений'); setDownloadingImages(false); }
  };

  const hasExternalImages = menuItems.some(i => i.image_url?.startsWith('http'));
  const filteredItems = menuItems.filter(item => {
    const matchesCategory = !selectedCategory || item.category_id === selectedCategory;
    const matchesSearch = !searchQuery || item.name.toLowerCase().includes(searchQuery.toLowerCase()) || item.description?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (loading) return <div className="flex items-center justify-center h-64"><div className="spinner" /></div>;

  return (
    <div className="space-y-6 animate-fadeIn" data-testid="menu-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-heading font-bold text-foreground">Управление меню</h1>
          <p className="text-muted-foreground">Перетаскивайте для изменения порядка</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => openCategoryDialog()}>
            <Plus className="w-4 h-4" />Категория
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => openItemDialog(null, true)} disabled={!selectedCategory}>
            <Image className="w-4 h-4" />Баннер
          </Button>
          <Button className="gap-2 rounded-full bg-mint-500 hover:bg-mint-600" onClick={() => openItemDialog(null, false)} disabled={!selectedCategory}>
            <Plus className="w-4 h-4" />Позиция
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => jsonFileRef.current?.click()} disabled={importing} data-testid="import-json-btn">
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileJson className="w-4 h-4" />}
            {importing ? 'Импорт...' : 'Импорт меню'}
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={openLabelDialog} data-testid="manage-labels-btn">
            <Tag className="w-4 h-4" />Ярлыки
          </Button>
          {hasExternalImages && (
            <Button variant="outline" className="gap-2 rounded-full" onClick={downloadAllImages} disabled={downloadingImages} data-testid="download-images-btn">
              {downloadingImages ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              {downloadingImages ? 'Скачивание...' : 'Скачать фото'}
            </Button>
          )}
          <input ref={jsonFileRef} type="file" accept=".json,.data" className="hidden" onChange={handleImportFileSelect} />
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <Input placeholder="Поиск по меню..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10 rounded-full" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Categories sidebar */}
        <Card className="lg:col-span-1 border-none shadow-md h-fit max-h-[70vh] overflow-hidden flex flex-col">
          <CardHeader className="pb-3 flex-shrink-0">
            <CardTitle className="text-lg font-heading flex items-center gap-2">
              <Layers className="w-4 h-4 text-muted-foreground" />Категории
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 overflow-y-auto flex-1">
            {categories.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">Нет категорий</p>
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleCategoryDragEnd}>
                <SortableContext items={categories.map(c => c.id)} strategy={verticalListSortingStrategy}>
                  {categories.map((category) => (
                    <SortableCategoryItem
                      key={category.id}
                      category={category}
                      isSelected={selectedCategory === category.id}
                      itemCount={menuItems.filter(i => i.category_id === category.id).length}
                      sectionName={getSectionName(category.section_id)}
                      onSelect={setSelectedCategory}
                      onEdit={openCategoryDialog}
                      onDelete={(cat) => openDeleteDialog(cat, 'category')}
                      onToggleActive={quickToggleCategoryActive}
                      onToggleDisplay={quickToggleCategoryDisplay}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </CardContent>
        </Card>

        {/* Menu items */}
        <div className="lg:col-span-3 space-y-4">
          {filteredItems.length === 0 ? (
            <Card className="border-none shadow-md">
              <CardContent className="py-12 text-center">
                <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">{searchQuery ? 'Ничего не найдено' : 'В этой категории пока нет позиций'}</p>
              </CardContent>
            </Card>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleItemDragEnd}>
              <SortableContext items={filteredItems.map(i => i.id)} strategy={verticalListSortingStrategy}>
                {filteredItems.map((item) => (
                  <SortableMenuItem
                    key={item.id}
                    item={item}
                    currency={currency}
                    onEdit={openItemDialog}
                    onDelete={(it) => openDeleteDialog(it, 'item')}
                    onToggleAvailability={toggleItemAvailability}
                  />
                ))}
              </SortableContext>
            </DndContext>
          )}
        </div>
      </div>

      {/* Dialogs */}
      <CategoryDialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen} editing={editingCategory} form={categoryForm} setForm={setCategoryForm} menuSections={menuSections} onSave={saveCategoryHandler} />
      <ItemDialog open={itemDialogOpen} onOpenChange={setItemDialogOpen} editing={editingItem} form={itemForm} setForm={setItemForm} categories={categories} labels={labels} currency={currency} onSave={saveItemHandler} onToggleLabel={toggleItemLabel} caffestaProducts={caffestaProducts} />
      <DeleteDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} target={deleteTarget} onConfirm={confirmDelete} />
      <ImportJsonDialog open={importDialogOpen} onOpenChange={setImportDialogOpen} importJson={importJson} setImportJson={setImportJson} importing={importing} onImport={handleImportMenu} />
      <ImportModeDialog open={importModeDialogOpen} onOpenChange={(open) => { if (!open) { setImportModeDialogOpen(false); setPendingImportFile(null); } }} pendingFile={pendingImportFile} importing={importing} onExecute={executeImport} />
      <LabelDialog open={labelDialogOpen} onOpenChange={setLabelDialogOpen} editing={editingLabel} setEditing={setEditingLabel} form={labelForm} setForm={setLabelForm} labels={labels} onSave={saveLabelHandler} onDelete={deleteLabelHandler} />
    </div>
  );
}

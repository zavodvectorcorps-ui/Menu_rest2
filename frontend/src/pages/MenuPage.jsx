import { useState, useEffect, useRef } from 'react';
import { Plus, Edit2, Trash2, GripVertical, ImageIcon, Flame, Star, Sparkles, Tag, Search, Image, Layers, Upload, X, Loader2, FileJson, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { API, useApp } from '@/App';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// DnD Kit imports
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
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

// Image Upload Component
function ImageUpload({ value, onChange }) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Недопустимый формат. Разрешены: JPG, PNG, GIF, WebP');
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Файл слишком большой. Максимум 5MB');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const imageUrl = `${BACKEND_URL}${response.data.url}`;
      onChange(imageUrl);
      toast.success('Изображение загружено');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = () => {
    onChange('');
  };

  return (
    <div className="space-y-2">
      <Label>Изображение</Label>
      
      {value ? (
        <div className="relative">
          <img 
            src={value} 
            alt="Preview" 
            className="w-full h-40 object-cover rounded-lg border border-border"
          />
          <Button
            variant="destructive"
            size="icon"
            className="absolute top-2 right-2 h-8 w-8 rounded-full"
            onClick={handleRemove}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      ) : (
        <div 
          className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-mint-500 hover:bg-mint-50/50 dark:hover:bg-mint-900/10 transition-colors"
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-mint-500 animate-spin" />
              <p className="text-sm text-muted-foreground">Загрузка...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Нажмите для загрузки или перетащите файл
              </p>
              <p className="text-xs text-muted-foreground">
                JPG, PNG, GIF, WebP до 5MB
              </p>
            </div>
          )}
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={handleFileSelect}
        disabled={uploading}
      />
      
      <div className="flex items-center gap-2">
        <Input
          placeholder="Или введите URL изображения"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="text-sm"
        />
      </div>
    </div>
  );
}

// Sortable Category Item
function SortableCategoryItem({ category, isSelected, itemCount, sectionName, onSelect, onEdit, onDelete }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: category.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${
        isSelected 
          ? 'bg-mint-500 text-white' 
          : 'hover:bg-accent'
      } ${isDragging ? 'shadow-lg' : ''}`}
      onClick={() => onSelect(category.id)}
      data-testid={`category-${category.id}`}
    >
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <button
          className={`cursor-grab active:cursor-grabbing p-1 rounded hover:bg-black/10 flex-shrink-0 ${isSelected ? 'hover:bg-white/20' : ''}`}
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
        >
          <GripVertical className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <span className="font-medium block text-sm leading-tight" title={category.name}>{category.name}</span>
          {sectionName && (
            <span className={`text-xs ${isSelected ? 'text-white/70' : 'text-muted-foreground'}`}>{sectionName}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-0.5 flex-shrink-0 ml-1">
        <span className={`text-xs w-5 text-center ${isSelected ? 'text-white/80' : 'text-muted-foreground'}`}>
          {itemCount}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className={`h-6 w-6 ${isSelected ? 'hover:bg-white/20' : ''}`}
          onClick={(e) => { e.stopPropagation(); onEdit(category); }}
        >
          <Edit2 className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className={`h-6 w-6 ${isSelected ? 'hover:bg-white/20' : 'hover:text-destructive'}`}
          onClick={(e) => { e.stopPropagation(); onDelete(category); }}
        >
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
}

// Sortable Menu Item
function SortableMenuItem({ item, onEdit, onDelete, onToggleAvailability, currency }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Banner item
  if (item.is_banner) {
    return (
      <Card 
        ref={setNodeRef}
        style={style}
        className={`border-none shadow-md transition-all ${!item.is_available ? 'opacity-60' : ''} ${isDragging ? 'shadow-xl z-50' : ''}`}
        data-testid={`banner-${item.id}`}
      >
        <CardContent className="p-4">
          <div className="flex gap-4">
            <button
              className="cursor-grab active:cursor-grabbing p-1 self-start text-muted-foreground hover:text-foreground"
              {...attributes}
              {...listeners}
            >
              <GripVertical className="w-5 h-5" />
            </button>

            <div className="flex-1">
              <div className="flex items-center justify-between mb-2">
                <Badge className="bg-purple-500 text-white">
                  <Image className="w-3 h-3 mr-1" />
                  Баннер
                </Badge>
                <div className="flex items-center gap-1">
                  <Switch
                    checked={item.is_available}
                    onCheckedChange={() => onToggleAvailability(item)}
                  />
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(item)}>
                    <Edit2 className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => onDelete(item)}>
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              
              {item.image_url && (
                <img src={item.image_url} alt={item.name} className="w-full h-32 object-cover rounded-lg mb-2" />
              )}
              
              {item.name && <h3 className="font-heading font-semibold text-foreground">{item.name}</h3>}
              {item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Regular menu item
  return (
    <Card 
      ref={setNodeRef}
      style={style}
      className={`border-none shadow-md transition-all ${!item.is_available ? 'opacity-60' : ''} ${isDragging ? 'shadow-xl z-50' : ''}`}
      data-testid={`menu-item-${item.id}`}
    >
      <CardContent className="p-4">
        <div className="flex gap-4">
          <button
            className="cursor-grab active:cursor-grabbing p-1 self-center text-muted-foreground hover:text-foreground"
            {...attributes}
            {...listeners}
          >
            <GripVertical className="w-5 h-5" />
          </button>

          <div className="w-20 h-20 rounded-xl bg-muted flex-shrink-0 overflow-hidden">
            {item.image_url ? (
              <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <ImageIcon className="w-6 h-6 text-muted-foreground/50" />
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-heading font-semibold text-foreground truncate text-sm">{item.name}</h3>
                <div className="flex flex-wrap gap-1 mt-1">
                  {item.is_hit && <Badge className="bg-red-500 text-white text-xs px-1.5 py-0">Хит</Badge>}
                  {item.is_new && <Badge className="bg-emerald-500 text-white text-xs px-1.5 py-0">Новинка</Badge>}
                  {item.is_spicy && <Badge className="bg-orange-500 text-white text-xs px-1.5 py-0">Острое</Badge>}
                  {item.is_promotion && <Badge className="bg-purple-500 text-white text-xs px-1.5 py-0">Акция</Badge>}
                  {item.is_business_lunch && <Badge className="bg-blue-500 text-white text-xs px-1.5 py-0">Бизнес-ланч</Badge>}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <Switch checked={item.is_available} onCheckedChange={() => onToggleAvailability(item)} />
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onEdit(item)}>
                  <Edit2 className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8 hover:text-destructive" onClick={() => onDelete(item)}>
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            
            {item.description && (
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{item.description}</p>
            )}
            
            <div className="flex items-center justify-between mt-2">
              <span className="text-base font-bold text-mint-500">{item.price} {currency}</span>
              {item.weight && <span className="text-xs text-muted-foreground">{item.weight}</span>}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

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
  
  const [categoryForm, setCategoryForm] = useState({ name: '', section_id: '', display_mode: 'card', sort_order: 0, is_active: true });
  const [itemForm, setItemForm] = useState({
    category_id: '',
    name: '',
    description: '',
    price: '',
    weight: '',
    image_url: '',
    is_available: true,
    is_business_lunch: false,
    is_promotion: false,
    is_hit: false,
    is_new: false,
    is_spicy: false,
    is_banner: false,
    sort_order: 0,
    label_ids: []
  });

  // File input ref for JSON import
  const jsonFileRef = useRef(null);

  // Get context
  const { currentRestaurantId, token } = useApp();
  const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    if (currentRestaurantId) {
      fetchData();
    }
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
    } catch (error) {
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const getSectionName = (sectionId) => {
    const section = menuSections.find(s => s.id === sectionId);
    return section?.name || '';
  };

  // Handle category drag end
  const handleCategoryDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIndex = categories.findIndex(c => c.id === active.id);
      const newIndex = categories.findIndex(c => c.id === over.id);
      const newCategories = arrayMove(categories, oldIndex, newIndex);
      setCategories(newCategories);
      
      try {
        const reorderIds = newCategories.map(cat => cat.id);
        await axios.post(`${API}/restaurants/${currentRestaurantId}/categories/reorder`, reorderIds, authHeaders);
        toast.success('Порядок категорий сохранён');
      } catch (error) {
        toast.error('Ошибка сохранения порядка');
        fetchData();
      }
    }
  };

  // Handle menu item drag end
  const handleItemDragEnd = async (event) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const filteredItems = menuItems.filter(item => item.category_id === selectedCategory);
      const oldIndex = filteredItems.findIndex(i => i.id === active.id);
      const newIndex = filteredItems.findIndex(i => i.id === over.id);
      const newFilteredItems = arrayMove(filteredItems, oldIndex, newIndex);
      
      const otherItems = menuItems.filter(item => item.category_id !== selectedCategory);
      const newMenuItems = [...otherItems, ...newFilteredItems];
      setMenuItems(newMenuItems);
      
      try {
        const reorderIds = newFilteredItems.map(item => item.id);
        await axios.post(`${API}/restaurants/${currentRestaurantId}/menu-items/reorder`, reorderIds, authHeaders);
        toast.success('Порядок позиций сохранён');
      } catch (error) {
        toast.error('Ошибка сохранения порядка');
        fetchData();
      }
    }
  };

  // Category handlers
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
    } catch (error) {
      toast.error('Ошибка сохранения категории');
    }
  };

  // Item handlers
  const openItemDialog = (item = null, isBanner = false) => {
    if (item) {
      setEditingItem(item);
      setItemForm({
        category_id: item.category_id,
        name: item.name,
        description: item.description || '',
        price: item.price?.toString() || '0',
        weight: item.weight || '',
        image_url: item.image_url || '',
        is_available: item.is_available,
        is_business_lunch: item.is_business_lunch,
        is_promotion: item.is_promotion,
        is_hit: item.is_hit,
        is_new: item.is_new,
        is_spicy: item.is_spicy,
        is_banner: item.is_banner,
        sort_order: item.sort_order,
        label_ids: item.label_ids || []
      });
    } else {
      setEditingItem(null);
      setItemForm({
        category_id: selectedCategory || '',
        name: '',
        description: '',
        price: '0',
        weight: '',
        image_url: '',
        is_available: true,
        is_business_lunch: false,
        is_promotion: false,
        is_hit: false,
        is_new: false,
        is_spicy: false,
        is_banner: isBanner,
        sort_order: menuItems.filter(i => i.category_id === selectedCategory).length,
        label_ids: []
      });
    }
    setItemDialogOpen(true);
  };

  const saveItemHandler = async () => {
    try {
      const data = {
        ...itemForm,
        price: parseFloat(itemForm.price) || 0,
        sort_order: parseInt(itemForm.sort_order) || 0
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
    } catch (error) {
      toast.error('Ошибка сохранения позиции');
    }
  };

  // Delete handlers
  const openDeleteDialog = (target, type) => {
    setDeleteTarget({ ...target, type });
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    try {
      if (deleteTarget.type === 'category') {
        await axios.delete(`${API}/restaurants/${currentRestaurantId}/categories/${deleteTarget.id}`, authHeaders);
        toast.success('Категория удалена');
        if (selectedCategory === deleteTarget.id) {
          setSelectedCategory(categories.find(c => c.id !== deleteTarget.id)?.id || null);
        }
      } else {
        await axios.delete(`${API}/restaurants/${currentRestaurantId}/menu-items/${deleteTarget.id}`, authHeaders);
        toast.success('Позиция удалена');
      }
      setDeleteDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  const toggleItemAvailability = async (item) => {
    try {
      await axios.put(`${API}/restaurants/${currentRestaurantId}/menu-items/${item.id}`, { is_available: !item.is_available }, authHeaders);
      fetchData();
      toast.success(item.is_available ? 'Позиция скрыта' : 'Позиция доступна');
    } catch (error) {
      toast.error('Ошибка обновления');
    }
  };

  // Import menu file handlers (.data / .json)
  const handleImportFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPendingImportFile(file);
    
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'json') {
      // JSON - read content for preview
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          JSON.parse(event.target.result);
          setImportJson(event.target.result);
        } catch {
          toast.error('Неверный формат JSON файла');
          setPendingImportFile(null);
          return;
        }
        setImportModeDialogOpen(true);
      };
      reader.readAsText(file);
    } else {
      // .data file - show mode selection
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
      // JSON import via body
      let jsonData;
      try {
        jsonData = JSON.parse(importJson);
      } catch {
        toast.error('Неверный формат JSON');
        return;
      }
      setImporting(true);
      try {
        const response = await axios.post(
          `${API}/restaurants/${currentRestaurantId}/import-menu`,
          { data: jsonData, mode },
          authHeaders
        );
        toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
        setImportJson('');
        setSelectedCategory(null);
        fetchData();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Ошибка импорта');
      } finally {
        setImporting(false);
        setPendingImportFile(null);
      }
    } else {
      // File upload (.data or .json)
      setImporting(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const response = await axios.post(
          `${API}/restaurants/${currentRestaurantId}/import-file?mode=${mode}`,
          formData,
          { headers: { ...authHeaders.headers, 'Content-Type': 'multipart/form-data' } }
        );
        toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
        setSelectedCategory(null);
        fetchData();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Ошибка импорта файла');
      } finally {
        setImporting(false);
        setPendingImportFile(null);
      }
    }
  };

  const handleImportMenu = async () => {
    if (!importJson.trim()) {
      toast.error('Введите JSON данные');
      return;
    }
    
    let jsonData;
    try {
      jsonData = JSON.parse(importJson);
    } catch (error) {
      toast.error('Неверный формат JSON');
      return;
    }
    
    setImporting(true);
    try {
      const response = await axios.post(
        `${API}/restaurants/${currentRestaurantId}/import-menu`,
        { data: jsonData, mode: 'append' },
        authHeaders
      );
      toast.success(`Импортировано: ${response.data.imported_categories} категорий, ${response.data.imported_items} позиций`);
      setImportDialogOpen(false);
      setImportJson('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка импорта');
    } finally {
      setImporting(false);
    }
  };

  // Label handlers
  const openLabelDialog = (label = null) => {
    setEditingLabel(label);
    setLabelForm(label ? { name: label.name, color: label.color } : { name: '', color: '#ef4444' });
    setLabelDialogOpen(true);
  };

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
      setLabelDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения ярлыка');
    }
  };

  const deleteLabelHandler = async (labelId) => {
    try {
      await axios.delete(`${API}/restaurants/${currentRestaurantId}/labels/${labelId}`, authHeaders);
      toast.success('Ярлык удалён');
      fetchData();
    } catch (error) {
      toast.error('Ошибка удаления');
    }
  };

  const toggleItemLabel = (labelId) => {
    setItemForm(prev => ({
      ...prev,
      label_ids: prev.label_ids.includes(labelId)
        ? prev.label_ids.filter(id => id !== labelId)
        : [...prev.label_ids, labelId]
    }));
  };

  const filteredItems = menuItems.filter(item => {
    const matchesCategory = !selectedCategory || item.category_id === selectedCategory;
    const matchesSearch = !searchQuery || 
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

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
            <Plus className="w-4 h-4" />
            Категория
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => openItemDialog(null, true)} disabled={!selectedCategory}>
            <Image className="w-4 h-4" />
            Баннер
          </Button>
          <Button className="gap-2 rounded-full bg-mint-500 hover:bg-mint-600" onClick={() => openItemDialog(null, false)} disabled={!selectedCategory}>
            <Plus className="w-4 h-4" />
            Позиция
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => jsonFileRef.current?.click()} disabled={importing} data-testid="import-json-btn">
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileJson className="w-4 h-4" />}
            {importing ? 'Импорт...' : 'Импорт меню'}
          </Button>
          <Button variant="outline" className="gap-2 rounded-full" onClick={() => openLabelDialog()} data-testid="manage-labels-btn">
            <Tag className="w-4 h-4" />
            Ярлыки
          </Button>
          <input
            ref={jsonFileRef}
            type="file"
            accept=".json,.data"
            className="hidden"
            onChange={handleImportFileSelect}
          />
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <Input
          placeholder="Поиск по меню..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 rounded-full"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Categories sidebar */}
        <Card className="lg:col-span-1 border-none shadow-md h-fit max-h-[70vh] overflow-hidden flex flex-col">
          <CardHeader className="pb-3 flex-shrink-0">
            <CardTitle className="text-lg font-heading flex items-center gap-2">
              <Layers className="w-4 h-4 text-muted-foreground" />
              Категории
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
                <p className="text-muted-foreground">
                  {searchQuery ? 'Ничего не найдено' : 'В этой категории пока нет позиций'}
                </p>
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

      {/* Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingCategory ? 'Редактировать категорию' : 'Новая категория'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Название</Label>
              <Input
                value={categoryForm.name}
                onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
                placeholder="Например: Горячие блюда"
              />
            </div>
            <div className="space-y-2">
              <Label>Раздел меню</Label>
              <Select
                value={categoryForm.section_id}
                onValueChange={(value) => setCategoryForm({ ...categoryForm, section_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите раздел" />
                </SelectTrigger>
                <SelectContent>
                  {menuSections.map((section) => (
                    <SelectItem key={section.id} value={section.id}>{section.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Режим отображения</Label>
              <Select
                value={categoryForm.display_mode}
                onValueChange={(value) => setCategoryForm({ ...categoryForm, display_mode: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Выберите режим" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="card">Карточка с картинкой</SelectItem>
                  <SelectItem value="compact">Компактный список</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {categoryForm.display_mode === 'card' 
                  ? 'Позиции будут отображаться с картинками (для коктейлей, блюд)' 
                  : 'Позиции будут отображаться строкой: название, цена, объём (для виски, вина)'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={categoryForm.is_active}
                onCheckedChange={(checked) => setCategoryForm({ ...categoryForm, is_active: checked })}
              />
              <Label>Активна</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>Отмена</Button>
            <Button onClick={saveCategoryHandler} className="bg-mint-500 hover:bg-mint-600" disabled={!categoryForm.name}>
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Item Dialog */}
      <Dialog open={itemDialogOpen} onOpenChange={setItemDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingItem ? (itemForm.is_banner ? 'Редактировать баннер' : 'Редактировать позицию') : (itemForm.is_banner ? 'Новый баннер' : 'Новая позиция')}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Категория</Label>
                <Select value={itemForm.category_id} onValueChange={(value) => setItemForm({ ...itemForm, category_id: value })}>
                  <SelectTrigger><SelectValue placeholder="Выберите категорию" /></SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>{itemForm.is_banner ? 'Заголовок (опционально)' : 'Название'}</Label>
                <Input
                  value={itemForm.name}
                  onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
                  placeholder={itemForm.is_banner ? 'Заголовок баннера' : 'Название блюда'}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Описание</Label>
              <Textarea
                value={itemForm.description}
                onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })}
                placeholder={itemForm.is_banner ? 'Текст баннера' : 'Описание блюда, состав...'}
                rows={3}
              />
            </div>

            {!itemForm.is_banner && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Цена ({currency})</Label>
                  <Input
                    type="number"
                    value={itemForm.price}
                    onChange={(e) => setItemForm({ ...itemForm, price: e.target.value })}
                    placeholder="0"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Объём / Выход</Label>
                  <Input
                    value={itemForm.weight}
                    onChange={(e) => setItemForm({ ...itemForm, weight: e.target.value })}
                    placeholder="200 г"
                  />
                </div>
              </div>
            )}

            <ImageUpload 
              value={itemForm.image_url}
              onChange={(url) => setItemForm({ ...itemForm, image_url: url })}
            />

            {!itemForm.is_banner && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2">
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_available} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_available: checked })} />
                  <Label>В наличии</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_hit} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_hit: checked })} />
                  <Label className="flex items-center gap-1"><Star className="w-4 h-4" /> Хит</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_new} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_new: checked })} />
                  <Label className="flex items-center gap-1"><Sparkles className="w-4 h-4" /> Новинка</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_spicy} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_spicy: checked })} />
                  <Label className="flex items-center gap-1"><Flame className="w-4 h-4" /> Острое</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_promotion} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_promotion: checked })} />
                  <Label className="flex items-center gap-1"><Tag className="w-4 h-4" /> Акция</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch checked={itemForm.is_business_lunch} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_business_lunch: checked })} />
                  <Label>Бизнес-ланч</Label>
                </div>
              </div>
            )}

            {/* Custom Labels */}
            {!itemForm.is_banner && labels.length > 0 && (
              <div className="space-y-2 pt-2">
                <Label>Ярлыки</Label>
                <div className="flex flex-wrap gap-2" data-testid="item-labels-selector">
                  {labels.map((label) => (
                    <button
                      key={label.id}
                      type="button"
                      onClick={() => toggleItemLabel(label.id)}
                      className={`px-3 py-1 rounded-full text-xs font-medium transition-all border-2 ${
                        itemForm.label_ids.includes(label.id)
                          ? 'border-transparent text-white'
                          : 'border-dashed opacity-50 hover:opacity-80'
                      }`}
                      style={{
                        backgroundColor: itemForm.label_ids.includes(label.id) ? label.color : 'transparent',
                        borderColor: itemForm.label_ids.includes(label.id) ? label.color : label.color,
                        color: itemForm.label_ids.includes(label.id) ? 'white' : label.color
                      }}
                      data-testid={`label-toggle-${label.id}`}
                    >
                      {label.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {itemForm.is_banner && (
              <div className="flex items-center gap-2">
                <Switch checked={itemForm.is_available} onCheckedChange={(checked) => setItemForm({ ...itemForm, is_available: checked })} />
                <Label>Показывать баннер</Label>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemDialogOpen(false)}>Отмена</Button>
            <Button 
              onClick={saveItemHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!itemForm.category_id || (!itemForm.is_banner && !itemForm.name)}
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Подтверждение удаления</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground py-4">
            Вы уверены, что хотите удалить {deleteTarget?.type === 'category' ? 'категорию' : 'позицию'}{' '}
            <strong>"{deleteTarget?.name}"</strong>?
            {deleteTarget?.type === 'category' && (
              <span className="block mt-2 text-destructive">Все позиции в этой категории также будут удалены!</span>
            )}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Отмена</Button>
            <Button variant="destructive" onClick={confirmDelete}>Удалить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import JSON Dialog */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Импорт меню из JSON</DialogTitle>
            <DialogDescription>
              Вставьте или отредактируйте JSON-данные меню. Формат: {"{"}"categories": [{"{"}"name": "...", "items": [...]{"}"}{"]"}{"}"} 
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Textarea
              value={importJson}
              onChange={(e) => setImportJson(e.target.value)}
              placeholder='{"categories": [{"name": "Закуски", "items": [{"name": "Цезарь", "price": 15.0}]}]}'
              className="font-mono text-sm min-h-[250px]"
              data-testid="import-json-textarea"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setImportDialogOpen(false); setImportJson(''); }}>Отмена</Button>
            <Button
              onClick={handleImportMenu}
              className="bg-mint-500 hover:bg-mint-600 gap-2"
              disabled={importing || !importJson.trim()}
              data-testid="import-json-submit"
            >
              {importing && <Loader2 className="w-4 h-4 animate-spin" />}
              {importing ? 'Импорт...' : 'Импортировать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Mode Dialog */}
      <Dialog open={importModeDialogOpen} onOpenChange={(open) => { if (!open) { setImportModeDialogOpen(false); setPendingImportFile(null); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Режим импорта</DialogTitle>
            <DialogDescription>
              {pendingImportFile?.name && <span className="block mb-2 text-sm font-medium">{pendingImportFile.name}</span>}
              Как обработать импортируемое меню?
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 py-4">
            <button
              onClick={() => executeImport('replace')}
              className="flex items-start gap-4 p-4 rounded-xl border-2 border-border hover:border-destructive/50 hover:bg-destructive/5 transition-all text-left group"
              disabled={importing}
              data-testid="import-mode-replace"
            >
              <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-red-500/20">
                <RefreshCw className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <h4 className="font-medium text-sm">Полное обновление</h4>
                <p className="text-xs text-muted-foreground mt-0.5">Удалить всё текущее меню и загрузить новое из файла</p>
              </div>
            </button>
            <button
              onClick={() => executeImport('append')}
              className="flex items-start gap-4 p-4 rounded-xl border-2 border-border hover:border-mint-500/50 hover:bg-mint-500/5 transition-all text-left group"
              disabled={importing}
              data-testid="import-mode-append"
            >
              <div className="w-10 h-10 rounded-xl bg-mint-500/10 flex items-center justify-center flex-shrink-0 group-hover:bg-mint-500/20">
                <Plus className="w-5 h-5 text-mint-500" />
              </div>
              <div>
                <h4 className="font-medium text-sm">Дополнить меню</h4>
                <p className="text-xs text-muted-foreground mt-0.5">Сохранить текущее меню и добавить новые позиции</p>
              </div>
            </button>
          </div>
          {importing && (
            <div className="flex items-center justify-center gap-2 py-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm text-muted-foreground">Импорт...</span>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Label Management Dialog */}
      <Dialog open={labelDialogOpen} onOpenChange={setLabelDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-heading">{editingLabel ? 'Редактировать ярлык' : 'Ярлыки'}</DialogTitle>
            <DialogDescription>Ярлыки отображаются на карточках блюд в клиентском меню</DialogDescription>
          </DialogHeader>

          {/* Existing labels list (shown when not editing) */}
          {!editingLabel && labels.length > 0 && (
            <div className="space-y-2 py-2">
              {labels.map((label) => (
                <div key={label.id} className="flex items-center justify-between p-2 rounded-lg bg-muted/50" data-testid={`label-item-${label.id}`}>
                  <div className="flex items-center gap-2">
                    <span className="w-4 h-4 rounded-full" style={{ backgroundColor: label.color }} />
                    <span className="text-sm font-medium">{label.name}</span>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setEditingLabel(label); setLabelForm({ name: label.name, color: label.color }); }}>
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => deleteLabelHandler(label.id)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Label form */}
          <div className="space-y-3 py-2">
            <div className="space-y-2">
              <Label>Название</Label>
              <Input
                value={labelForm.name}
                onChange={(e) => setLabelForm({ ...labelForm, name: e.target.value })}
                placeholder="Хит, Сезонное, Выбор гостей..."
                data-testid="label-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Цвет</Label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={labelForm.color}
                  onChange={(e) => setLabelForm({ ...labelForm, color: e.target.value })}
                  className="w-10 h-10 rounded-lg cursor-pointer border border-border"
                  data-testid="label-color-input"
                />
                <div className="flex gap-2 flex-wrap">
                  {['#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899'].map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setLabelForm({ ...labelForm, color: c })}
                      className={`w-7 h-7 rounded-full transition-transform ${labelForm.color === c ? 'ring-2 ring-offset-2 ring-offset-background scale-110' : ''}`}
                      style={{ backgroundColor: c, ringColor: c }}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <span className="text-sm text-muted-foreground">Предпросмотр:</span>
              <span
                className="px-3 py-1 rounded-full text-xs font-medium text-white"
                style={{ backgroundColor: labelForm.color }}
              >
                {labelForm.name || 'Ярлык'}
              </span>
            </div>
          </div>
          <DialogFooter>
            {editingLabel && (
              <Button variant="outline" onClick={() => { setEditingLabel(null); setLabelForm({ name: '', color: '#ef4444' }); }}>
                Назад
              </Button>
            )}
            <Button onClick={saveLabelHandler} className="bg-mint-500 hover:bg-mint-600" disabled={!labelForm.name.trim()} data-testid="save-label-btn">
              {editingLabel ? 'Сохранить' : 'Создать ярлык'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, ChevronDown, ChevronUp, GripVertical, Check, X, ImageIcon, Flame, Star, Sparkles, Tag, Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { API } from '@/App';
import axios from 'axios';

export default function MenuPage() {
  const [categories, setCategories] = useState([]);
  const [menuItems, setMenuItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Dialog states
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [itemDialogOpen, setItemDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  
  // Form states
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  
  const [categoryForm, setCategoryForm] = useState({ name: '', sort_order: 0, is_active: true });
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
    sort_order: 0
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [categoriesRes, itemsRes] = await Promise.all([
        axios.get(`${API}/categories`),
        axios.get(`${API}/menu-items`)
      ]);
      setCategories(categoriesRes.data);
      setMenuItems(itemsRes.data);
      if (categoriesRes.data.length > 0 && !selectedCategory) {
        setSelectedCategory(categoriesRes.data[0].id);
      }
    } catch (error) {
      toast.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  // Category handlers
  const openCategoryDialog = (category = null) => {
    if (category) {
      setEditingCategory(category);
      setCategoryForm({ name: category.name, sort_order: category.sort_order, is_active: category.is_active });
    } else {
      setEditingCategory(null);
      setCategoryForm({ name: '', sort_order: categories.length, is_active: true });
    }
    setCategoryDialogOpen(true);
  };

  const saveCategoryHandler = async () => {
    try {
      if (editingCategory) {
        await axios.put(`${API}/categories/${editingCategory.id}`, categoryForm);
        toast.success('Категория обновлена');
      } else {
        await axios.post(`${API}/categories`, categoryForm);
        toast.success('Категория создана');
      }
      setCategoryDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Ошибка сохранения категории');
    }
  };

  // Item handlers
  const openItemDialog = (item = null) => {
    if (item) {
      setEditingItem(item);
      setItemForm({
        category_id: item.category_id,
        name: item.name,
        description: item.description || '',
        price: item.price.toString(),
        weight: item.weight || '',
        image_url: item.image_url || '',
        is_available: item.is_available,
        is_business_lunch: item.is_business_lunch,
        is_promotion: item.is_promotion,
        is_hit: item.is_hit,
        is_new: item.is_new,
        is_spicy: item.is_spicy,
        sort_order: item.sort_order
      });
    } else {
      setEditingItem(null);
      setItemForm({
        category_id: selectedCategory || '',
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
        sort_order: menuItems.filter(i => i.category_id === selectedCategory).length
      });
    }
    setItemDialogOpen(true);
  };

  const saveItemHandler = async () => {
    try {
      const data = {
        ...itemForm,
        price: parseFloat(itemForm.price),
        sort_order: parseInt(itemForm.sort_order)
      };
      
      if (editingItem) {
        await axios.put(`${API}/menu-items/${editingItem.id}`, data);
        toast.success('Позиция обновлена');
      } else {
        await axios.post(`${API}/menu-items`, data);
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
        await axios.delete(`${API}/categories/${deleteTarget.id}`);
        toast.success('Категория удалена');
        if (selectedCategory === deleteTarget.id) {
          setSelectedCategory(categories.find(c => c.id !== deleteTarget.id)?.id || null);
        }
      } else {
        await axios.delete(`${API}/menu-items/${deleteTarget.id}`);
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
      await axios.put(`${API}/menu-items/${item.id}`, { is_available: !item.is_available });
      fetchData();
      toast.success(item.is_available ? 'Позиция скрыта' : 'Позиция доступна');
    } catch (error) {
      toast.error('Ошибка обновления');
    }
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
          <p className="text-muted-foreground">Категории и позиции вашего ресторана</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="gap-2 rounded-full"
            onClick={() => openCategoryDialog()}
            data-testid="add-category-btn"
          >
            <Plus className="w-4 h-4" />
            Категория
          </Button>
          <Button
            className="gap-2 rounded-full bg-mint-500 hover:bg-mint-600"
            onClick={() => openItemDialog()}
            disabled={!selectedCategory}
            data-testid="add-item-btn"
          >
            <Plus className="w-4 h-4" />
            Позиция
          </Button>
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
          data-testid="menu-search-input"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Categories sidebar */}
        <Card className="lg:col-span-1 border-none shadow-md h-fit" data-testid="categories-list">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-heading">Категории</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {categories.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Нет категорий
              </p>
            ) : (
              categories.map((category) => (
                <div
                  key={category.id}
                  className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${
                    selectedCategory === category.id 
                      ? 'bg-mint-500 text-white' 
                      : 'hover:bg-accent'
                  }`}
                  onClick={() => setSelectedCategory(category.id)}
                  data-testid={`category-${category.id}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{category.name}</span>
                    {!category.is_active && (
                      <Badge variant="secondary" className="text-xs">Скрыта</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`text-sm ${selectedCategory === category.id ? 'text-white/80' : 'text-muted-foreground'}`}>
                      {menuItems.filter(i => i.category_id === category.id).length}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-7 w-7 ${selectedCategory === category.id ? 'hover:bg-white/20' : ''}`}
                      onClick={(e) => { e.stopPropagation(); openCategoryDialog(category); }}
                      data-testid={`edit-category-${category.id}`}
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-7 w-7 ${selectedCategory === category.id ? 'hover:bg-white/20' : 'hover:text-destructive'}`}
                      onClick={(e) => { e.stopPropagation(); openDeleteDialog(category, 'category'); }}
                      data-testid={`delete-category-${category.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Menu items */}
        <div className="lg:col-span-3 space-y-4" data-testid="menu-items-list">
          {filteredItems.length === 0 ? (
            <Card className="border-none shadow-md">
              <CardContent className="py-12 text-center">
                <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                <p className="text-muted-foreground">
                  {searchQuery ? 'Ничего не найдено' : 'В этой категории пока нет позиций'}
                </p>
                {!searchQuery && selectedCategory && (
                  <Button
                    className="mt-4 rounded-full bg-mint-500 hover:bg-mint-600"
                    onClick={() => openItemDialog()}
                    data-testid="add-first-item-btn"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Добавить первую позицию
                  </Button>
                )}
              </CardContent>
            </Card>
          ) : (
            filteredItems.map((item) => (
              <Card 
                key={item.id} 
                className={`border-none shadow-md transition-all ${!item.is_available ? 'opacity-60' : ''}`}
                data-testid={`menu-item-${item.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex gap-4">
                    {/* Image */}
                    <div className="w-24 h-24 rounded-xl bg-muted flex-shrink-0 overflow-hidden">
                      {item.image_url ? (
                        <img 
                          src={item.image_url} 
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <ImageIcon className="w-8 h-8 text-muted-foreground/50" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h3 className="font-heading font-semibold text-foreground truncate">
                            {item.name}
                          </h3>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {item.is_hit && <Badge className="bg-red-500 text-white text-xs">Хит</Badge>}
                            {item.is_new && <Badge className="bg-emerald-500 text-white text-xs">Новинка</Badge>}
                            {item.is_spicy && <Badge className="bg-orange-500 text-white text-xs">Острое</Badge>}
                            {item.is_promotion && <Badge className="bg-purple-500 text-white text-xs">Акция</Badge>}
                            {item.is_business_lunch && <Badge className="bg-blue-500 text-white text-xs">Бизнес-ланч</Badge>}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Switch
                            checked={item.is_available}
                            onCheckedChange={() => toggleItemAvailability(item)}
                            data-testid={`toggle-availability-${item.id}`}
                          />
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openItemDialog(item)}
                            data-testid={`edit-item-${item.id}`}
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 hover:text-destructive"
                            onClick={() => openDeleteDialog(item, 'item')}
                            data-testid={`delete-item-${item.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                      
                      {item.description && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                          {item.description}
                        </p>
                      )}
                      
                      <div className="flex items-center justify-between mt-3">
                        <span className="text-lg font-bold text-mint-500">
                          {item.price} ₽
                        </span>
                        {item.weight && (
                          <span className="text-sm text-muted-foreground">
                            {item.weight}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Category Dialog */}
      <Dialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen}>
        <DialogContent data-testid="category-dialog">
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
                data-testid="category-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Порядок сортировки</Label>
              <Input
                type="number"
                value={categoryForm.sort_order}
                onChange={(e) => setCategoryForm({ ...categoryForm, sort_order: parseInt(e.target.value) || 0 })}
                data-testid="category-sort-input"
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={categoryForm.is_active}
                onCheckedChange={(checked) => setCategoryForm({ ...categoryForm, is_active: checked })}
                data-testid="category-active-switch"
              />
              <Label>Активна</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCategoryDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveCategoryHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!categoryForm.name}
              data-testid="save-category-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Item Dialog */}
      <Dialog open={itemDialogOpen} onOpenChange={setItemDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="item-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingItem ? 'Редактировать позицию' : 'Новая позиция'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Категория</Label>
                <Select
                  value={itemForm.category_id}
                  onValueChange={(value) => setItemForm({ ...itemForm, category_id: value })}
                >
                  <SelectTrigger data-testid="item-category-select">
                    <SelectValue placeholder="Выберите категорию" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>{cat.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Название</Label>
                <Input
                  value={itemForm.name}
                  onChange={(e) => setItemForm({ ...itemForm, name: e.target.value })}
                  placeholder="Название блюда"
                  data-testid="item-name-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Описание</Label>
              <Textarea
                value={itemForm.description}
                onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })}
                placeholder="Описание блюда, состав..."
                rows={3}
                data-testid="item-description-input"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Цена (₽)</Label>
                <Input
                  type="number"
                  value={itemForm.price}
                  onChange={(e) => setItemForm({ ...itemForm, price: e.target.value })}
                  placeholder="0"
                  data-testid="item-price-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Объём / Выход</Label>
                <Input
                  value={itemForm.weight}
                  onChange={(e) => setItemForm({ ...itemForm, weight: e.target.value })}
                  placeholder="200 г"
                  data-testid="item-weight-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Сортировка</Label>
                <Input
                  type="number"
                  value={itemForm.sort_order}
                  onChange={(e) => setItemForm({ ...itemForm, sort_order: e.target.value })}
                  data-testid="item-sort-input"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>URL изображения</Label>
              <Input
                value={itemForm.image_url}
                onChange={(e) => setItemForm({ ...itemForm, image_url: e.target.value })}
                placeholder="https://..."
                data-testid="item-image-input"
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 pt-2">
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_available}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_available: checked })}
                  data-testid="item-available-switch"
                />
                <Label className="flex items-center gap-1">
                  <Check className="w-4 h-4" /> В наличии
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_hit}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_hit: checked })}
                  data-testid="item-hit-switch"
                />
                <Label className="flex items-center gap-1">
                  <Star className="w-4 h-4" /> Хит
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_new}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_new: checked })}
                  data-testid="item-new-switch"
                />
                <Label className="flex items-center gap-1">
                  <Sparkles className="w-4 h-4" /> Новинка
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_spicy}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_spicy: checked })}
                  data-testid="item-spicy-switch"
                />
                <Label className="flex items-center gap-1">
                  <Flame className="w-4 h-4" /> Острое
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_promotion}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_promotion: checked })}
                  data-testid="item-promotion-switch"
                />
                <Label className="flex items-center gap-1">
                  <Tag className="w-4 h-4" /> Акция
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={itemForm.is_business_lunch}
                  onCheckedChange={(checked) => setItemForm({ ...itemForm, is_business_lunch: checked })}
                  data-testid="item-lunch-switch"
                />
                <Label>Бизнес-ланч</Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setItemDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              onClick={saveItemHandler}
              className="bg-mint-500 hover:bg-mint-600"
              disabled={!itemForm.name || !itemForm.category_id || !itemForm.price}
              data-testid="save-item-btn"
            >
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent data-testid="delete-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">Подтверждение удаления</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground py-4">
            Вы уверены, что хотите удалить {deleteTarget?.type === 'category' ? 'категорию' : 'позицию'}{' '}
            <strong>"{deleteTarget?.name}"</strong>?
            {deleteTarget?.type === 'category' && (
              <span className="block mt-2 text-destructive">
                Все позиции в этой категории также будут удалены!
              </span>
            )}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Отмена
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmDelete}
              data-testid="confirm-delete-btn"
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

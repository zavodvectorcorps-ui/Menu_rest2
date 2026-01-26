import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Plus, Edit2, Trash2, Shield, User, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useApp, API } from '@/App';
import axios from 'axios';

export default function UsersPage() {
  const { token, user: currentUser, restaurants } = useApp();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [form, setForm] = useState({
    username: '',
    password: '',
    role: 'manager',
    restaurant_ids: [],
    is_active: true
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUsers(response.data);
    } catch (error) {
      toast.error('Ошибка загрузки пользователей');
    } finally {
      setLoading(false);
    }
  };

  const openDialog = (user = null) => {
    if (user) {
      setEditingUser(user);
      setForm({
        username: user.username,
        password: '',
        role: user.role,
        restaurant_ids: user.restaurant_ids || [],
        is_active: user.is_active !== false
      });
    } else {
      setEditingUser(null);
      setForm({
        username: '',
        password: '',
        role: 'manager',
        restaurant_ids: [],
        is_active: true
      });
    }
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.username) {
      toast.error('Введите логин');
      return;
    }
    if (!editingUser && !form.password) {
      toast.error('Введите пароль');
      return;
    }

    try {
      const data = { ...form };
      if (!data.password) delete data.password;

      if (editingUser) {
        await axios.put(`${API}/users/${editingUser.id}`, data, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Пользователь обновлен');
      } else {
        await axios.post(`${API}/users`, data, {
          headers: { Authorization: `Bearer ${token}` }
        });
        toast.success('Пользователь создан');
      }
      setDialogOpen(false);
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка сохранения');
    }
  };

  const handleDelete = async (userId) => {
    if (!confirm('Удалить пользователя?')) return;
    
    try {
      await axios.delete(`${API}/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Пользователь удален');
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const toggleRestaurant = (restaurantId) => {
    const current = form.restaurant_ids || [];
    if (current.includes(restaurantId)) {
      setForm({ ...form, restaurant_ids: current.filter(id => id !== restaurantId) });
    } else {
      setForm({ ...form, restaurant_ids: [...current, restaurantId] });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-mint-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="users-page">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-heading font-bold">Пользователи</h2>
          <p className="text-muted-foreground">Управление доступом к системе</p>
        </div>
        <Button onClick={() => openDialog()} className="bg-mint-500 hover:bg-mint-600" data-testid="add-user-btn">
          <Plus className="w-4 h-4 mr-2" />
          Добавить пользователя
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Пользователь</TableHead>
                <TableHead>Роль</TableHead>
                <TableHead>Рестораны</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        user.role === 'superadmin' ? 'bg-amber-100 dark:bg-amber-900/30' : 'bg-mint-100 dark:bg-mint-900/30'
                      }`}>
                        {user.role === 'superadmin' ? (
                          <Shield className="w-5 h-5 text-amber-600" />
                        ) : (
                          <User className="w-5 h-5 text-mint-600" />
                        )}
                      </div>
                      <span className="font-medium">{user.username}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.role === 'superadmin' ? 'default' : 'secondary'}>
                      {user.role === 'superadmin' ? 'Суперадмин' : 'Менеджер'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {user.role === 'superadmin' ? (
                      <span className="text-muted-foreground">Все рестораны</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {(user.restaurant_ids || []).map(rid => {
                          const r = restaurants.find(r => r.id === rid);
                          return r ? (
                            <Badge key={rid} variant="outline" className="text-xs">
                              {r.name}
                            </Badge>
                          ) : null;
                        })}
                        {(!user.restaurant_ids || user.restaurant_ids.length === 0) && (
                          <span className="text-muted-foreground text-sm">Нет доступа</span>
                        )}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_active !== false ? 'success' : 'destructive'}>
                      {user.is_active !== false ? 'Активен' : 'Неактивен'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openDialog(user)}
                        disabled={user.id === currentUser?.id}
                        data-testid={`edit-user-${user.id}`}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="hover:text-destructive"
                        onClick={() => handleDelete(user.id)}
                        disabled={user.id === currentUser?.id}
                        data-testid={`delete-user-${user.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* User Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent data-testid="user-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">
              {editingUser ? 'Редактировать пользователя' : 'Новый пользователь'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Логин</Label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="username"
                data-testid="user-username"
              />
            </div>
            <div className="space-y-2">
              <Label>{editingUser ? 'Новый пароль (оставьте пустым чтобы не менять)' : 'Пароль'}</Label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="••••••"
                data-testid="user-password"
              />
            </div>
            <div className="space-y-2">
              <Label>Роль</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger data-testid="user-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="superadmin">Суперадмин (доступ ко всем ресторанам)</SelectItem>
                  <SelectItem value="manager">Менеджер (доступ только к выбранным)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.role === 'manager' && (
              <div className="space-y-2">
                <Label>Доступ к ресторанам</Label>
                <div className="space-y-2 max-h-40 overflow-y-auto border rounded-lg p-3">
                  {restaurants.map((restaurant) => (
                    <div key={restaurant.id} className="flex items-center gap-3">
                      <Switch
                        checked={(form.restaurant_ids || []).includes(restaurant.id)}
                        onCheckedChange={() => toggleRestaurant(restaurant.id)}
                      />
                      <span className="text-sm">{restaurant.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Switch
                checked={form.is_active}
                onCheckedChange={(checked) => setForm({ ...form, is_active: checked })}
              />
              <Label>Активен</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Отмена</Button>
            <Button onClick={handleSave} className="bg-mint-500 hover:bg-mint-600" data-testid="save-user-btn">
              Сохранить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

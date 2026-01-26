import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ShoppingCart, Plus, Minus, Bell, X, Send, Check, Flame, Star, Sparkles, Tag, ChevronRight, ImageIcon, Clock, MapPin, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { Toaster } from '@/components/ui/sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ClientMenuPage() {
  const { tableCode } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [orderNotes, setOrderNotes] = useState('');
  const [submittingOrder, setSubmittingOrder] = useState(false);
  const [callingStaff, setCallingStaff] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const response = await axios.get(`${API}/public/menu/${tableCode}`);
        setData(response.data);
        if (response.data.categories.length > 0) {
          setSelectedCategory(response.data.categories[0].id);
        }
      } catch (err) {
        if (err.response?.status === 404) {
          setError('Стол не найден');
        } else if (err.response?.status === 400) {
          setError(err.response.data.detail || 'Меню недоступно');
        } else {
          setError('Ошибка загрузки меню');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMenu();
  }, [tableCode]);

  const addToCart = (item) => {
    const existing = cart.find(c => c.id === item.id);
    if (existing) {
      setCart(cart.map(c => c.id === item.id ? { ...c, quantity: c.quantity + 1 } : c));
    } else {
      setCart([...cart, { ...item, quantity: 1 }]);
    }
    toast.success(`${item.name} добавлен в корзину`);
  };

  const updateCartQuantity = (itemId, delta) => {
    setCart(cart.map(c => {
      if (c.id === itemId) {
        const newQuantity = c.quantity + delta;
        return newQuantity > 0 ? { ...c, quantity: newQuantity } : null;
      }
      return c;
    }).filter(Boolean));
  };

  const removeFromCart = (itemId) => {
    setCart(cart.filter(c => c.id !== itemId));
  };

  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  const submitOrder = async () => {
    if (cart.length === 0) return;

    setSubmittingOrder(true);
    try {
      await axios.post(`${API}/orders`, {
        table_code: tableCode,
        items: cart.map(item => ({
          menu_item_id: item.id,
          name: item.name,
          quantity: item.quantity,
          price: item.price
        })),
        notes: orderNotes
      });
      setOrderSuccess(true);
      setCart([]);
      setOrderNotes('');
      setTimeout(() => setOrderSuccess(false), 5000);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка оформления заказа');
    } finally {
      setSubmittingOrder(false);
      setCartOpen(false);
    }
  };

  const callStaff = async () => {
    setCallingStaff(true);
    try {
      await axios.post(`${API}/staff-calls`, { table_code: tableCode });
      toast.success('Официант скоро подойдёт к вашему столу');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка вызова персонала');
    } finally {
      setCallingStaff(false);
    }
  };

  const filteredItems = data?.items.filter(item => item.category_id === selectedCategory) || [];

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-mint-500/20 flex items-center justify-center">
            <div className="w-10 h-10 rounded-full bg-mint-500 animate-ping" />
          </div>
          <p className="text-muted-foreground font-medium">Загрузка меню...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center">
          <div className="w-20 h-20 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
            <X className="w-10 h-10 text-red-500" />
          </div>
          <h1 className="text-2xl font-heading font-bold text-foreground mb-2">{error}</h1>
          <p className="text-muted-foreground">Пожалуйста, обратитесь к персоналу ресторана</p>
        </div>
      </div>
    );
  }

  const { restaurant, settings, categories, table } = data;

  return (
    <div className="min-h-screen bg-background" data-testid="client-menu-page">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-card/95 backdrop-blur-md border-b border-border">
        <div className="px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {restaurant.logo_url ? (
                <img src={restaurant.logo_url} alt={restaurant.name} className="w-10 h-10 rounded-xl object-cover" />
              ) : (
                <div className="w-10 h-10 rounded-xl bg-mint-500 flex items-center justify-center text-white font-bold">
                  {restaurant.name?.charAt(0)}
                </div>
              )}
              <div>
                <h1 className="font-heading font-bold text-foreground">{restaurant.name}</h1>
                <p className="text-xs text-muted-foreground">Стол №{table.number}</p>
              </div>
            </div>
            
            {settings.staff_call_enabled && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-full border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20"
                onClick={callStaff}
                disabled={callingStaff}
                data-testid="call-staff-btn"
              >
                <Bell className="w-4 h-4 mr-1" />
                {callingStaff ? '...' : 'Вызвать'}
              </Button>
            )}
          </div>

          {restaurant.slogan && (
            <p className="text-sm text-muted-foreground mt-2 italic">{restaurant.slogan}</p>
          )}
        </div>

        {/* Category tabs */}
        <div className="overflow-x-auto scrollbar-hide">
          <div className="flex px-4 pb-3 gap-2 min-w-max">
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap ${
                  selectedCategory === cat.id
                    ? 'bg-mint-500 text-white shadow-lg shadow-mint-500/30'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                data-testid={`category-tab-${cat.id}`}
              >
                {cat.name}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Menu items */}
      <main className="px-4 py-6 pb-32">
        {orderSuccess && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800" data-testid="order-success-message">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                <Check className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-heading font-semibold text-emerald-800 dark:text-emerald-200">
                  Заказ принят!
                </h3>
                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                  Ваш заказ передан на кухню. Спасибо!
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="grid gap-4" data-testid="menu-items-grid">
          {filteredItems.length === 0 ? (
            <div className="text-center py-12">
              <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">В этой категории пока нет блюд</p>
            </div>
          ) : (
            filteredItems.map((item) => (
              <div
                key={item.id}
                className="bg-card rounded-2xl shadow-md overflow-hidden menu-item-card"
                data-testid={`menu-item-${item.id}`}
              >
                <div className="flex">
                  {/* Image */}
                  <div className="w-28 h-28 flex-shrink-0 bg-muted">
                    {item.image_url ? (
                      <img
                        src={item.image_url}
                        alt={item.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ImageIcon className="w-8 h-8 text-muted-foreground/30" />
                      </div>
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 p-3 flex flex-col">
                    <div className="flex-1">
                      <div className="flex items-start gap-1 flex-wrap mb-1">
                        <h3 className="font-heading font-semibold text-foreground text-sm leading-tight">
                          {item.name}
                        </h3>
                        {item.is_hit && (
                          <Badge className="bg-red-500 text-white text-[10px] px-1.5 py-0">
                            <Star className="w-3 h-3 mr-0.5" />Хит
                          </Badge>
                        )}
                        {item.is_new && (
                          <Badge className="bg-emerald-500 text-white text-[10px] px-1.5 py-0">
                            <Sparkles className="w-3 h-3 mr-0.5" />Новинка
                          </Badge>
                        )}
                        {item.is_spicy && (
                          <Badge className="bg-orange-500 text-white text-[10px] px-1.5 py-0">
                            <Flame className="w-3 h-3 mr-0.5" />Острое
                          </Badge>
                        )}
                      </div>
                      
                      {item.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                          {item.description}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-bold text-mint-500">{item.price} ₽</span>
                        {item.weight && (
                          <span className="text-xs text-muted-foreground ml-2">{item.weight}</span>
                        )}
                      </div>
                      
                      {settings.online_orders_enabled && (
                        <Button
                          size="sm"
                          className="h-8 rounded-full bg-mint-500 hover:bg-mint-600 text-white px-3"
                          onClick={() => addToCart(item)}
                          data-testid={`add-to-cart-${item.id}`}
                        >
                          <Plus className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      {/* Restaurant info footer */}
      <div className="px-4 py-6 bg-muted/50 border-t border-border mb-20">
        <div className="space-y-3">
          {restaurant.address && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="w-4 h-4" />
              <span>{restaurant.address}</span>
            </div>
          )}
          {restaurant.working_hours && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>{restaurant.working_hours}</span>
            </div>
          )}
          {restaurant.phone && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Phone className="w-4 h-4" />
              <a href={`tel:${restaurant.phone}`} className="hover:text-mint-500">
                {restaurant.phone}
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Cart button */}
      {settings.online_orders_enabled && cart.length > 0 && (
        <div className="fixed bottom-4 left-4 right-4 z-50" data-testid="cart-button-container">
          <Button
            className="w-full h-14 rounded-2xl bg-mint-500 hover:bg-mint-600 text-white shadow-lg shadow-mint-500/30"
            onClick={() => setCartOpen(true)}
            data-testid="open-cart-btn"
          >
            <ShoppingCart className="w-5 h-5 mr-2" />
            <span className="font-semibold">{cartCount} поз.</span>
            <ChevronRight className="w-5 h-5 mx-2" />
            <span className="font-bold">{cartTotal} ₽</span>
          </Button>
        </div>
      )}

      {/* Cart Dialog */}
      <Dialog open={cartOpen} onOpenChange={setCartOpen}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-hidden flex flex-col" data-testid="cart-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading">Ваш заказ</DialogTitle>
          </DialogHeader>
          
          <div className="flex-1 overflow-y-auto py-4 space-y-3">
            {cart.map((item) => (
              <div key={item.id} className="flex items-center gap-3 p-3 rounded-xl bg-muted/50" data-testid={`cart-item-${item.id}`}>
                <div className="flex-1">
                  <h4 className="font-medium text-foreground text-sm">{item.name}</h4>
                  <p className="text-sm text-mint-500 font-semibold">{item.price} ₽</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 rounded-full"
                    onClick={() => updateCartQuantity(item.id, -1)}
                    data-testid={`decrease-${item.id}`}
                  >
                    <Minus className="w-3 h-3" />
                  </Button>
                  <span className="w-6 text-center font-semibold">{item.quantity}</span>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8 rounded-full"
                    onClick={() => updateCartQuantity(item.id, 1)}
                    data-testid={`increase-${item.id}`}
                  >
                    <Plus className="w-3 h-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => removeFromCart(item.id)}
                    data-testid={`remove-${item.id}`}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}

            <div className="pt-3">
              <Textarea
                placeholder="Комментарий к заказу (аллергии, пожелания...)"
                value={orderNotes}
                onChange={(e) => setOrderNotes(e.target.value)}
                rows={2}
                className="resize-none"
                data-testid="order-notes-input"
              />
            </div>
          </div>

          <div className="border-t border-border pt-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-lg font-heading font-semibold">Итого:</span>
              <span className="text-2xl font-bold text-mint-500">{cartTotal} ₽</span>
            </div>
            
            <Button
              className="w-full h-12 rounded-xl bg-mint-500 hover:bg-mint-600 text-white font-semibold"
              onClick={submitOrder}
              disabled={submittingOrder || cart.length === 0}
              data-testid="submit-order-btn"
            >
              {submittingOrder ? (
                <>
                  <div className="spinner mr-2" />
                  Оформление...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5 mr-2" />
                  Оформить заказ
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Toaster position="top-center" richColors />
    </div>
  );
}

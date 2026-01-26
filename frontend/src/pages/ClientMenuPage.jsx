import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ShoppingCart, Plus, Minus, Bell, X, Send, Check, Flame, Star, Sparkles, Tag, ChevronRight, ImageIcon, Clock, MapPin, Phone, ChevronDown } from 'lucide-react';
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
  const [selectedSection, setSelectedSection] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [orderNotes, setOrderNotes] = useState('');
  const [submittingOrder, setSubmittingOrder] = useState(false);
  const [callModalOpen, setCallModalOpen] = useState(false);
  const [callingStaff, setCallingStaff] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const response = await axios.get(`${API}/public/menu/${tableCode}`);
        setData(response.data);
        
        // Select first section with categories
        const sections = response.data.sections || [];
        if (sections.length > 0) {
          setSelectedSection(sections[0].id);
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

  // Apply theme from settings
  useEffect(() => {
    if (data?.settings?.theme) {
      if (data.settings.theme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    }
    
    // Cleanup - restore to light when leaving
    return () => {
      document.documentElement.classList.remove('dark');
    };
  }, [data?.settings?.theme]);

  // Get categories for selected section
  const sectionCategories = data?.categories.filter(cat => cat.section_id === selectedSection) || [];
  
  // Set first category when section changes
  useEffect(() => {
    if (sectionCategories.length > 0 && !sectionCategories.find(c => c.id === selectedCategory)) {
      setSelectedCategory(sectionCategories[0].id);
    }
  }, [selectedSection, sectionCategories]);

  const addToCart = (item) => {
    if (item.is_banner) return; // Don't add banners to cart
    
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

  const callStaff = async (callTypeId) => {
    setCallingStaff(true);
    try {
      await axios.post(`${API}/staff-calls`, { 
        table_code: tableCode,
        call_type_id: callTypeId 
      });
      const callType = data?.call_types?.find(ct => ct.id === callTypeId);
      toast.success(callType ? `${callType.name} - запрос отправлен` : 'Запрос отправлен');
      setCallModalOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Ошибка отправки запроса');
    } finally {
      setCallingStaff(false);
    }
  };

  const filteredItems = data?.items.filter(item => item.category_id === selectedCategory) || [];
  const currency = data?.settings?.currency || 'BYN';
  const currentCategory = data?.categories.find(cat => cat.id === selectedCategory);
  const displayMode = currentCategory?.display_mode || 'card';

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

  const { restaurant, settings, sections, table, call_types } = data;

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
            
            {settings.staff_call_enabled && call_types && call_types.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="rounded-full border-amber-500 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20"
                onClick={() => setCallModalOpen(true)}
                data-testid="call-staff-btn"
              >
                <Bell className="w-4 h-4 mr-1" />
                Вызов
              </Button>
            )}
          </div>

          {restaurant.slogan && (
            <p className="text-sm text-muted-foreground mt-2 italic">{restaurant.slogan}</p>
          )}
        </div>

        {/* Section tabs (Гастрономическое, Барное, Кальянное) */}
        <div className="px-4 pb-3">
          <div className="flex gap-2 overflow-x-auto scrollbar-hide">
            {sections.filter(s => s.is_active).map((section) => (
              <button
                key={section.id}
                onClick={() => setSelectedSection(section.id)}
                className={`px-4 py-2.5 rounded-xl text-sm font-semibold transition-all whitespace-nowrap ${
                  selectedSection === section.id
                    ? 'bg-mint-500 text-white shadow-lg shadow-mint-500/30'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
                data-testid={`section-tab-${section.id}`}
              >
                {section.name}
              </button>
            ))}
          </div>
        </div>

        {/* Category tabs within section */}
        {sectionCategories.length > 0 && (
          <div className="overflow-x-auto scrollbar-hide border-t border-border/50">
            <div className="flex px-4 py-2 gap-2 min-w-max">
              {sectionCategories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap ${
                    selectedCategory === cat.id
                      ? 'bg-brown-500 text-white'
                      : 'bg-transparent text-muted-foreground hover:text-foreground'
                  }`}
                  data-testid={`category-tab-${cat.id}`}
                >
                  {cat.name}
                </button>
              ))}
            </div>
          </div>
        )}
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

        <div className={displayMode === 'compact' ? 'space-y-1' : 'space-y-4'} data-testid="menu-items-grid">
          {filteredItems.length === 0 ? (
            <div className="text-center py-12">
              <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">В этой категории пока нет позиций</p>
            </div>
          ) : (
            <>
              {/* Compact mode - list view */}
              {displayMode === 'compact' && (
                <div className="bg-card rounded-2xl shadow-md overflow-hidden">
                  {filteredItems.map((item, index) => (
                    item.is_banner ? (
                      // Banner in compact mode
                      <div
                        key={item.id}
                        className="p-4 border-b border-border last:border-b-0"
                        data-testid={`banner-${item.id}`}
                      >
                        {item.image_url && (
                          <img src={item.image_url} alt={item.name} className="w-full h-auto rounded-lg mb-2" />
                        )}
                        {item.name && <h3 className="font-heading font-semibold text-foreground">{item.name}</h3>}
                        {item.description && <p className="text-sm text-muted-foreground">{item.description}</p>}
                      </div>
                    ) : (
                      // Compact menu item - just name, weight, price
                      <div
                        key={item.id}
                        className={`flex items-center justify-between px-4 py-3 ${index !== filteredItems.length - 1 ? 'border-b border-border/50' : ''}`}
                        data-testid={`menu-item-${item.id}`}
                      >
                        <div className="flex-1 min-w-0 pr-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground truncate">{item.name}</span>
                            {item.is_hit && <Star className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
                            {item.is_new && <Sparkles className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />}
                          </div>
                          {item.weight && (
                            <span className="text-xs text-muted-foreground">{item.weight}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className="font-bold text-mint-500 whitespace-nowrap">{item.price} {currency}</span>
                          {settings.online_orders_enabled && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-8 w-8 rounded-full hover:bg-mint-100 dark:hover:bg-mint-900/30 p-0"
                              onClick={() => addToCart(item)}
                              data-testid={`add-to-cart-${item.id}`}
                            >
                              <Plus className="w-4 h-4 text-mint-500" />
                            </Button>
                          )}
                        </div>
                      </div>
                    )
                  ))}
                </div>
              )}

              {/* Card mode - original view with images */}
              {displayMode === 'card' && filteredItems.map((item) => (
                item.is_banner ? (
                  // Banner item - full width image
                  <div
                    key={item.id}
                    className="rounded-2xl overflow-hidden shadow-md"
                    data-testid={`banner-${item.id}`}
                  >
                    {item.image_url && (
                      <img
                        src={item.image_url}
                        alt={item.name}
                        className="w-full h-auto object-cover"
                      />
                    )}
                    {(item.name || item.description) && (
                      <div className="p-4 bg-card">
                        {item.name && (
                          <h3 className="font-heading font-semibold text-foreground">{item.name}</h3>
                        )}
                        {item.description && (
                          <p className="text-sm text-muted-foreground mt-1">{item.description}</p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  // Regular menu item with image
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
                            <span className="font-bold text-mint-500">{item.price} {currency}</span>
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
                )
              ))}
            </>
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
            <span className="font-bold">{cartTotal} {currency}</span>
          </Button>
        </div>
      )}

      {/* Call Staff Modal */}
      <Dialog open={callModalOpen} onOpenChange={setCallModalOpen}>
        <DialogContent className="max-w-sm" data-testid="call-modal">
          <DialogHeader>
            <DialogTitle className="font-heading text-center">Выберите действие</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-4">
            {call_types?.map((callType) => (
              <Button
                key={callType.id}
                variant="outline"
                className="w-full h-14 justify-start text-left rounded-xl hover:bg-mint-50 hover:border-mint-500 dark:hover:bg-mint-900/20"
                onClick={() => callStaff(callType.id)}
                disabled={callingStaff}
                data-testid={`call-type-${callType.id}`}
              >
                <Bell className="w-5 h-5 mr-3 text-mint-500" />
                <span className="font-medium">{callType.name}</span>
              </Button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

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
                  <p className="text-sm text-mint-500 font-semibold">{item.price} {currency}</p>
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
              <span className="text-2xl font-bold text-mint-500">{cartTotal} {currency}</span>
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

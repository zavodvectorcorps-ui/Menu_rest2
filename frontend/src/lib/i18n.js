// Lightweight i18n for the client menu. Not a full library — just a
// translation map + tiny hook that persists the chosen language.

import { useEffect, useState, useCallback } from 'react';

export const SUPPORTED_LANGS = [
  { code: 'ru', label: 'RU', flag: '🇷🇺', full: 'Русский' },
  { code: 'en', label: 'EN', flag: '🇬🇧', full: 'English' },
];

const STORAGE_KEY = 'client_menu_lang';

const STRINGS = {
  ru: {
    // Header / layout
    loading: 'Загрузка меню...',
    error_title: 'Меню недоступно',
    error_generic: 'Не удалось загрузить меню',
    search_placeholder: 'Поиск блюд...',
    search_no_results: 'Ничего не найдено',
    menu_empty: 'Меню пока пусто',
    category_empty: 'В этой категории пока нет блюд',
    table_label: 'Стол',

    // Cart
    cart_title: 'Корзина',
    cart_empty: 'Корзина пуста',
    cart_empty_hint: 'Добавляйте блюда из меню',
    cart_subtotal: 'Итого',
    cart_checkout: 'Оформить заказ',
    cart_show_waiter: 'Показать заказ официанту',
    cart_clear: 'Очистить',
    cart_done: 'Готово',
    cart_back: 'Назад',
    remove: 'Удалить',

    // Order form
    order_notes: 'Комментарий к заказу',
    order_notes_placeholder: 'Например: без лука, без острого...',
    order_your_name: 'Ваше имя',
    order_phone: 'Телефон',
    order_address: 'Адрес',
    order_city: 'Город',
    order_preorder_date: 'Дата',
    order_preorder_time: 'Время',
    submit_order: 'Оформить заказ',
    submitting: 'Отправка...',
    order_sent: 'Заказ отправлен',
    order_sent_hint: 'Мы уже готовим его для вас',
    order_status: 'Статус заказа',
    order_status_pending: 'Принят',
    order_status_in_progress: 'Готовится',
    order_status_completed: 'Готов',
    order_status_cancelled: 'Отменён',

    // Staff call
    call_waiter: 'Вызвать официанта',
    call_choose_reason: 'Что вам нужно?',
    call_sending: 'Отправка...',
    call_sent: 'Официант уже идёт',
    call_sent_hint: 'Мы передали ваш вызов',
    cancel: 'Отмена',

    // Badges
    badge_hit: 'Хит',
    badge_new: 'Новинка',
    badge_spicy: 'Острое',
    badge_takeaway: 'На вынос',
    badge_promotion: 'Акция',
    badge_business_lunch: 'Бизнес-ланч',

    // Misc
    close: 'Закрыть',
    open: 'Открыть',
    details: 'Подробнее',
    weight: 'Вес',
    price: 'Цена',
  },
  en: {
    loading: 'Loading menu...',
    error_title: 'Menu unavailable',
    error_generic: 'Could not load menu',
    search_placeholder: 'Search dishes...',
    search_no_results: 'No matches found',
    menu_empty: 'Menu is empty',
    category_empty: 'No dishes in this category yet',
    table_label: 'Table',

    cart_title: 'Cart',
    cart_empty: 'Cart is empty',
    cart_empty_hint: 'Add dishes from the menu',
    cart_subtotal: 'Subtotal',
    cart_checkout: 'Place order',
    cart_show_waiter: 'Show order to the waiter',
    cart_clear: 'Clear',
    cart_done: 'Done',
    cart_back: 'Back',
    remove: 'Remove',

    order_notes: 'Order notes',
    order_notes_placeholder: 'e.g. no onions, not spicy...',
    order_your_name: 'Your name',
    order_phone: 'Phone',
    order_address: 'Address',
    order_city: 'City',
    order_preorder_date: 'Date',
    order_preorder_time: 'Time',
    submit_order: 'Place order',
    submitting: 'Sending...',
    order_sent: 'Order sent',
    order_sent_hint: 'We are preparing it for you',
    order_status: 'Order status',
    order_status_pending: 'Accepted',
    order_status_in_progress: 'In progress',
    order_status_completed: 'Ready',
    order_status_cancelled: 'Cancelled',

    call_waiter: 'Call waiter',
    call_choose_reason: 'What do you need?',
    call_sending: 'Sending...',
    call_sent: 'The waiter is on the way',
    call_sent_hint: 'Your request has been delivered',
    cancel: 'Cancel',

    badge_hit: 'Hit',
    badge_new: 'New',
    badge_spicy: 'Spicy',
    badge_takeaway: 'Takeaway',
    badge_promotion: 'Promo',
    badge_business_lunch: 'Business lunch',

    close: 'Close',
    open: 'Open',
    details: 'Details',
    weight: 'Weight',
    price: 'Price',
  },
};

export function useI18n() {
  const [lang, setLangState] = useState(() => {
    const saved = (typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY)) || '';
    if (saved && STRINGS[saved]) return saved;
    // Auto-detect from navigator
    const nav = (typeof navigator !== 'undefined' && (navigator.language || '').toLowerCase()) || '';
    if (nav.startsWith('en')) return 'en';
    return 'ru';
  });

  const setLang = useCallback((next) => {
    if (!STRINGS[next]) return;
    setLangState(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* noop */ }
  }, []);

  useEffect(() => {
    if (typeof document !== 'undefined') document.documentElement.setAttribute('lang', lang);
  }, [lang]);

  const t = useCallback(
    (key) => (STRINGS[lang] && STRINGS[lang][key]) || (STRINGS.ru && STRINGS.ru[key]) || key,
    [lang]
  );

  return { lang, setLang, t };
}

/**
 * Return a localized field from a document.
 * getLocalized(item, 'name', 'en') === item.name_en if it's a non-empty string, else item.name
 */
export function getLocalized(doc, field, lang) {
  if (!doc) return '';
  if (lang && lang !== 'ru') {
    const key = `${field}_${lang}`;
    const val = doc[key];
    if (typeof val === 'string' && val.trim()) return val;
  }
  return doc[field] || '';
}

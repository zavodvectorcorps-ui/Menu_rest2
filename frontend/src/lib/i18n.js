// Lightweight i18n for the client menu. Not a full library — just a
// translation map + tiny hook that persists the chosen language.

import { useEffect, useState, useCallback } from 'react';

export const SUPPORTED_LANGS = [
  { code: 'ru', label: 'RU', flag: '🇷🇺', full: 'Русский' },
  { code: 'en', label: 'EN', flag: '🇬🇧', full: 'English' },
  { code: 'zh', label: '中文', flag: '🇨🇳', full: '简体中文' },
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
  zh: {
    loading: '正在加载菜单...',
    error_title: '菜单不可用',
    error_generic: '无法加载菜单',
    search_placeholder: '搜索菜品...',
    search_no_results: '未找到匹配项',
    menu_empty: '菜单为空',
    category_empty: '此分类暂无菜品',
    table_label: '桌号',

    cart_title: '购物车',
    cart_empty: '购物车为空',
    cart_empty_hint: '请从菜单中添加菜品',
    cart_subtotal: '小计',
    cart_checkout: '下单',
    cart_show_waiter: '把订单展示给服务员',
    cart_clear: '清空',
    cart_done: '完成',
    cart_back: '返回',
    remove: '删除',

    order_notes: '订单备注',
    order_notes_placeholder: '例如：不要洋葱、不辣...',
    order_your_name: '您的姓名',
    order_phone: '电话',
    order_address: '地址',
    order_city: '城市',
    order_preorder_date: '日期',
    order_preorder_time: '时间',
    submit_order: '提交订单',
    submitting: '正在发送...',
    order_sent: '订单已发送',
    order_sent_hint: '我们正在为您准备',
    order_status: '订单状态',
    order_status_pending: '已接受',
    order_status_in_progress: '正在制作',
    order_status_completed: '已完成',
    order_status_cancelled: '已取消',

    call_waiter: '呼叫服务员',
    call_choose_reason: '需要什么帮助？',
    call_sending: '正在发送...',
    call_sent: '服务员马上到',
    call_sent_hint: '您的请求已发送',
    cancel: '取消',

    badge_hit: '招牌',
    badge_new: '新品',
    badge_spicy: '辣',
    badge_takeaway: '外带',
    badge_promotion: '促销',
    badge_business_lunch: '商务套餐',

    close: '关闭',
    open: '打开',
    details: '详情',
    weight: '克重',
    price: '价格',
  },
};

export function useI18n(availableLangs = null) {
  // availableLangs: optional list of lang codes (e.g. ['ru', 'en', 'zh']).
  // If provided, the chosen lang is constrained to that set.
  const allowed = (availableLangs && availableLangs.length)
    ? new Set(['ru', ...availableLangs])
    : null;

  const [lang, setLangState] = useState(() => {
    const saved = (typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY)) || '';
    if (saved && STRINGS[saved] && (!allowed || allowed.has(saved))) return saved;
    // Auto-detect from navigator
    const nav = (typeof navigator !== 'undefined' && (navigator.language || '').toLowerCase()) || '';
    if (nav.startsWith('zh') && (!allowed || allowed.has('zh'))) return 'zh';
    if (nav.startsWith('en') && (!allowed || allowed.has('en'))) return 'en';
    return 'ru';
  });

  // If the restaurant disables the currently active lang (e.g. ZH was turned off),
  // fall back to RU automatically.
  useEffect(() => {
    if (allowed && !allowed.has(lang)) setLangState('ru');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableLangs && availableLangs.join(',')]);

  const setLang = useCallback((next) => {
    if (!STRINGS[next]) return;
    if (allowed && !allowed.has(next)) return;
    setLangState(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* noop */ }
  }, [allowed]);

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

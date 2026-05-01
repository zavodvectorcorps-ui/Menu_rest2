// Currency helpers — central place to keep ISO codes and display symbols.

export const SUPPORTED_CURRENCIES = [
  { code: 'BYN', symbol: 'Br', label: 'BYN — Белорусский рубль' },
  { code: 'USD', symbol: '$',  label: 'USD — Доллар США' },
  { code: 'EUR', symbol: '€',  label: 'EUR — Евро' },
  { code: 'RUB', symbol: '₽',  label: 'RUB — Российский рубль' },
  { code: 'PLN', symbol: 'zł', label: 'PLN — Польский злотый' },
  { code: 'KZT', symbol: '₸',  label: 'KZT — Тенге' },
  { code: 'UAH', symbol: '₴',  label: 'UAH — Гривна' },
];

export function currencySymbol(code) {
  const c = (code || 'BYN').toUpperCase();
  return SUPPORTED_CURRENCIES.find(x => x.code === c)?.symbol || c;
}

export function formatPrice(amount, code) {
  const sym = currencySymbol(code);
  const num = Number(amount || 0);
  return `${num.toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ${sym}`;
}

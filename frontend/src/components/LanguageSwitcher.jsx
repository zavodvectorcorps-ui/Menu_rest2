import { useState, useRef, useEffect } from 'react';
import { SUPPORTED_LANGS } from '@/lib/i18n';
import { Globe, Check } from 'lucide-react';

/**
 * Language switcher. Two visual variants:
 *   `variant="pill"` (default) — full pill row with flags+labels, for desktop
 *   `variant="icon"` — compact icon button that opens a small popover with
 *                       flag+label rows. Used in mobile sticky header.
 * Pass `availableLangs=['en','zh']` to restrict which non-RU languages are
 * shown — RU is always shown.
 */
export default function LanguageSwitcher({ lang, setLang, availableLangs = null, className = '', variant = 'pill' }) {
  const allowed = (availableLangs && availableLangs.length)
    ? new Set(['ru', ...availableLangs])
    : null;
  const visible = allowed
    ? SUPPORTED_LANGS.filter((l) => allowed.has(l.code))
    : SUPPORTED_LANGS;
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('touchstart', onDown, { passive: true });
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('touchstart', onDown);
    };
  }, [open]);

  if (visible.length <= 1) return null;

  if (variant === 'icon') {
    const current = visible.find((l) => l.code === lang) || visible[0];
    return (
      <div ref={wrapRef} className={`relative ${className}`} data-testid="language-switcher">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label="Switch language"
          aria-expanded={open}
          data-testid="lang-toggle-btn"
          className="w-8 h-8 md:w-9 md:h-9 rounded-full border border-border text-foreground/70 hover:bg-muted flex items-center justify-center relative"
        >
          <Globe className="w-4 h-4" />
          <span className="absolute -bottom-0.5 -right-0.5 text-[9px] font-bold bg-mint-500 text-white rounded-full w-3.5 h-3.5 flex items-center justify-center leading-none">
            {current.code === 'zh' ? '中' : current.code.toUpperCase().slice(0, 1)}
          </span>
        </button>
        {open && (
          <div
            className="absolute right-0 top-[calc(100%+6px)] z-50 min-w-[128px] rounded-xl border border-border bg-card shadow-lg p-1"
            role="menu"
          >
            {visible.map((l) => {
              const active = l.code === lang;
              return (
                <button
                  key={l.code}
                  type="button"
                  onClick={() => { setLang(l.code); setOpen(false); }}
                  data-testid={`lang-btn-${l.code}`}
                  className={
                    'w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ' +
                    (active ? 'bg-mint-500 text-white' : 'text-foreground hover:bg-muted')
                  }
                  aria-pressed={active}
                  role="menuitemradio"
                  aria-checked={active}
                >
                  <span className="text-base leading-none">{l.flag}</span>
                  <span className="flex-1 text-left">{l.label}</span>
                  {active && <Check className="w-3.5 h-3.5" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-1 p-1 rounded-full border border-black/10 bg-white/90 backdrop-blur shadow-sm ${className}`}
      data-testid="language-switcher"
    >
      {visible.map((l) => {
        const active = lang === l.code;
        return (
          <button
            key={l.code}
            type="button"
            onClick={() => setLang(l.code)}
            data-testid={`lang-btn-${l.code}`}
            aria-pressed={active}
            className={
              'px-2.5 h-7 rounded-full text-xs font-semibold transition-colors flex items-center gap-1 ' +
              (active
                ? 'bg-slate-900 text-white'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100')
            }
          >
            <span className="text-sm leading-none">{l.flag}</span>
            <span>{l.label}</span>
          </button>
        );
      })}
    </div>
  );
}

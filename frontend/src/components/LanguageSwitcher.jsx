import { SUPPORTED_LANGS } from '@/lib/i18n';

/**
 * Tiny pill-style language switcher. Two-language compact toggle.
 * Used in the client menu header.
 */
export default function LanguageSwitcher({ lang, setLang, className = '' }) {
  return (
    <div
      className={`inline-flex items-center gap-1 p-1 rounded-full border border-black/10 bg-white/90 backdrop-blur shadow-sm ${className}`}
      data-testid="language-switcher"
    >
      {SUPPORTED_LANGS.map((l) => {
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

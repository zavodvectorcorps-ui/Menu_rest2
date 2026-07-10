// Simple RU→EN transliteration + kebab-case slugifier.
// Used for anchor links to menu categories (e.g. "Бургеры" -> "burgery").

const CYR_MAP = {
  а: 'a', б: 'b', в: 'v', г: 'g', д: 'd', е: 'e', ё: 'e', ж: 'zh', з: 'z',
  и: 'i', й: 'i', к: 'k', л: 'l', м: 'm', н: 'n', о: 'o', п: 'p', р: 'r',
  с: 's', т: 't', у: 'u', ф: 'f', х: 'h', ц: 'c', ч: 'ch', ш: 'sh', щ: 'sch',
  ъ: '', ы: 'y', ь: '', э: 'e', ю: 'yu', я: 'ya',
};

/**
 * Convert an arbitrary category name into a URL-safe slug.
 * Preserves ASCII letters/digits, transliterates Cyrillic, replaces
 * anything else with a single hyphen. Returns empty string for empty
 * input.
 *
 * @param {string} text
 * @returns {string}
 */
export function slugify(text) {
  if (!text) return '';
  let out = '';
  for (const ch of String(text).toLowerCase()) {
    if (Object.prototype.hasOwnProperty.call(CYR_MAP, ch)) {
      out += CYR_MAP[ch];
    } else {
      out += ch;
    }
  }
  return out
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

/**
 * Компактный бейдж пищевой ценности блюда (на 100 г).
 * Показывает БЖУ + калорийность в виде "Б 20 • Ж 12 • У 5 • 210 ккал".
 * Если ни одно поле не заполнено — не рендерит ничего (return null).
 * Заявленный формат:
 *   Б {protein} • Ж {fat} • У {carbs} г • {kcal} ккал / {kj} кДж
 * Пропускает пустые/null-поля.
 */
export function NutritionBadge({ item, className = '', variant = 'inline', dict = null }) {
  if (!item) return null;
  const p = item.nutrition_protein;
  const f = item.nutrition_fat;
  const c = item.nutrition_carbs;
  const kcal = item.nutrition_kcal;
  const kj = item.nutrition_kj;

  const hasAny = [p, f, c, kcal, kj].some((v) => v !== null && v !== undefined && v !== '' && !Number.isNaN(Number(v)));
  if (!hasAny) return null;

  const L = dict || {
    protein: 'Б',
    fat: 'Ж',
    carbs: 'У',
    kcal: 'ккал',
    kj: 'кДж',
    per_100g: 'на 100 г',
  };

  const fmt = (v) => {
    const n = Number(v);
    if (Number.isNaN(n)) return null;
    // Отсекаем ".0", оставляем максимум 1 знак после запятой
    return Math.abs(n - Math.round(n)) < 0.05 ? Math.round(n).toString() : n.toFixed(1);
  };

  const parts = [];
  const fp = fmt(p); if (fp !== null && p !== null && p !== undefined && p !== '') parts.push(`${L.protein} ${fp}`);
  const ff = fmt(f); if (ff !== null && f !== null && f !== undefined && f !== '') parts.push(`${L.fat} ${ff}`);
  const fc = fmt(c); if (fc !== null && c !== null && c !== undefined && c !== '') parts.push(`${L.carbs} ${fc}`);

  const energyParts = [];
  const fk = fmt(kcal); if (fk !== null && kcal !== null && kcal !== undefined && kcal !== '') energyParts.push(`${fk} ${L.kcal}`);
  const fj = fmt(kj);   if (fj !== null && kj !== null && kj !== undefined && kj !== '') energyParts.push(`${fj} ${L.kj}`);

  const macros = parts.join(' • ');
  const energy = energyParts.join(' / ');
  const full = [macros, energy].filter(Boolean).join(' • ');

  if (variant === 'block') {
    return (
      <div
        className={`text-[11px] text-muted-foreground/90 leading-snug ${className}`}
        data-testid={`nutrition-badge-${item.id}`}
        title={`${L.per_100g}: ${full}`}
      >
        <span className="opacity-70 mr-1">{L.per_100g}:</span>
        {full}
      </div>
    );
  }

  return (
    <span
      className={`text-[11px] text-muted-foreground/90 whitespace-nowrap ${className}`}
      data-testid={`nutrition-badge-${item.id}`}
      title={`${L.per_100g}: ${full}`}
    >
      {full}
    </span>
  );
}

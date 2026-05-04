import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import {
  Sparkles, Globe, QrCode, BarChart3, Bot, Wallet,
  ShoppingBag, ArrowRight, Zap, Languages, ChefHat, MessageSquare,
  Lock, Rocket, Star, ExternalLink, Copy, User, Eye, Clock,
  CheckCircle2, TrendingUp, Smartphone, Bell, RefreshCcw,
} from 'lucide-react';

import { API } from '@/App';

/**
 * Public marketing/demo page — accessible at /demo without auth.
 * Restaurant-owner focused: business benefits, real screenshots, live demo access.
 */
export default function DemoPage() {
  const [scrollY, setScrollY] = useState(0);
  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const [demoMenu, setDemoMenu] = useState(null);
  useEffect(() => {
    axios.get(`${API}/public/demo-menu-info`).then((r) => setDemoMenu(r.data)).catch(() => {});
  }, []);

  const demoMenuUrl = demoMenu ? `${window.location.origin}${demoMenu.path}` : null;

  // SEO meta tags
  useEffect(() => {
    const prevTitle = document.title;
    document.title = 'REST-MENU — Цифровое меню для ресторанов | QR, заказы, аналитика';
    const metas = [
      { name: 'description', content: 'Готовая платформа цифрового меню для ресторанов: QR-меню для гостей, приём заказов в зал и на доставку, Telegram-уведомления и аналитика — без разработки и абонентских мук.' },
      { name: 'keywords', content: 'цифровое меню для ресторана, QR меню, онлайн меню ресторана, заказы по QR, меню для кафе' },
      { name: 'robots', content: 'index, follow' },
      { property: 'og:type', content: 'website' },
      { property: 'og:title', content: 'REST-MENU — Цифровое меню для ресторанов' },
      { property: 'og:description', content: 'QR-меню, онлайн-заказы, Telegram-уведомления и аналитика. Запуск за день — без программирования.' },
      { property: 'og:image', content: `${window.location.origin}/og-image.jpg` },
      { property: 'og:image:width', content: '1200' },
      { property: 'og:image:height', content: '630' },
      { property: 'og:image:type', content: 'image/jpeg' },
      { property: 'og:url', content: `${window.location.origin}/demo` },
      { property: 'og:site_name', content: 'REST-MENU' },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: 'REST-MENU — Цифровое меню для ресторанов' },
      { name: 'twitter:description', content: 'QR-меню, онлайн-заказы, аналитика и Telegram — за день.' },
      { name: 'twitter:image', content: `${window.location.origin}/og-image.jpg` },
      { name: 'theme-color', content: '#0a0e1a' },
    ];
    const created = [];
    metas.forEach(({ name, property, content }) => {
      const sel = name ? `meta[name="${name}"]` : `meta[property="${property}"]`;
      let n = document.head.querySelector(sel);
      if (!n) { n = document.createElement('meta'); if (name) n.setAttribute('name', name); if (property) n.setAttribute('property', property); document.head.appendChild(n); created.push(n); }
      n.setAttribute('content', content);
    });
    let canonical = document.head.querySelector('link[rel="canonical"]');
    const canonicalCreated = !canonical;
    if (!canonical) { canonical = document.createElement('link'); canonical.setAttribute('rel', 'canonical'); document.head.appendChild(canonical); }
    canonical.setAttribute('href', `${window.location.origin}/demo`);
    return () => {
      document.title = prevTitle;
      created.forEach((n) => n.remove());
      if (canonicalCreated && canonical) canonical.remove();
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-white overflow-x-hidden font-sans" data-testid="demo-page">

      {/* ===== Top bar ===== */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-xl bg-[#0a0e1a]/70 border-b border-white/5">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between">
          <a href="#top" className="flex items-center gap-2 group">
            <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-mint-400 to-emerald-500 flex items-center justify-center shadow-lg shadow-mint-500/30">
              <ChefHat className="w-4 h-4 text-[#0a0e1a]" />
            </span>
            <span className="font-semibold tracking-tight group-hover:text-mint-300 transition-colors">REST-MENU</span>
          </a>
          <div className="hidden md:flex items-center gap-6 text-sm text-white/60">
            <a href="#benefits" className="hover:text-white transition-colors">Возможности</a>
            <a href="#screens" className="hover:text-white transition-colors">Как выглядит</a>
            <a href="#try" className="hover:text-white transition-colors">Попробовать</a>
          </div>
          <Link to="/login" className="px-4 h-9 inline-flex items-center gap-1.5 rounded-full bg-white text-[#0a0e1a] text-sm font-semibold hover:bg-mint-300 transition-colors" data-testid="demo-cta-login">
            Войти <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ===== Hero ===== */}
      <section id="top" className="relative pt-28 pb-20 overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full bg-mint-500/10 blur-[120px]" style={{ transform: `translateY(${scrollY * 0.15}px)` }} />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-purple-500/10 blur-[120px]" style={{ transform: `translateY(${scrollY * -0.1}px)` }} />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:32px_32px]" />
        </div>

        <div className="max-w-6xl mx-auto px-5 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-mint-500/30 bg-mint-500/10 text-mint-300 text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Готовая платформа для ресторанов
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05]">
              Цифровое меню,<br />
              <span className="bg-gradient-to-r from-mint-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent">
                заказы и аналитика
              </span>
              <br />
              <span className="text-white/70 text-3xl sm:text-4xl lg:text-5xl">— в одном кабинете</span>
            </h1>
            <p className="mt-6 text-lg text-white/60 leading-relaxed max-w-xl">
              Гости сканируют QR на столе, листают меню с фото и оформляют заказ.
              Вы видите всё в админке, получаете уведомления в Telegram и понимаете,
              какие блюда продаются.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a href="#try" className="px-6 h-12 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-mint-400 to-emerald-500 text-[#0a0e1a] font-semibold hover:shadow-2xl hover:shadow-mint-500/30 transition-all hover:-translate-y-0.5" data-testid="demo-hero-cta-primary">
                Попробовать сейчас <ArrowRight className="w-5 h-5" />
              </a>
              <a href="#screencast" className="px-6 h-12 inline-flex items-center gap-2 rounded-full border border-white/15 hover:bg-white/5 transition-colors text-sm">
                Как это выглядит
              </a>
            </div>

            <div className="mt-8 flex items-center gap-5 text-sm text-white/50">
              <div className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-mint-400" /> Без разработки</div>
              <div className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-mint-400" /> Запуск за день</div>
              <div className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-mint-400" /> Свой домен</div>
            </div>
          </div>

          {/* Hero media — static OG card */}
          <div className="relative" style={{ transform: `translateY(${scrollY * 0.05}px)` }}>
            <div className="absolute -inset-6 bg-gradient-to-tr from-mint-500/20 via-purple-500/20 to-cyan-500/20 blur-3xl rounded-full" />
            <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
              <img
                src="/og-image.jpg"
                alt="REST-MENU — цифровое меню, QR, POS, Telegram"
                className="w-full h-auto block"
                data-testid="demo-hero-image"
                loading="eager"
              />
            </div>
            {/* Floating badges */}
            <div className="absolute -left-4 top-8 hidden md:block">
              <FloatingChip icon={<Bell className="w-3.5 h-3.5" />} text="Новый заказ" tone="emerald" delay={0} />
            </div>
            <div className="absolute -right-4 bottom-12 hidden md:block">
              <FloatingChip icon={<Star className="w-3.5 h-3.5" />} text="+12% к выручке" tone="amber" delay={400} />
            </div>
          </div>
        </div>
      </section>

      {/* ===== Live screencast ===== */}
      <section id="screencast" className="py-16 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-5">
          <div className="text-center mb-8">
            <div className="text-mint-400 text-xs font-semibold tracking-wider uppercase mb-2">Демо за 22 секунды</div>
            <h2 className="text-2xl sm:text-4xl font-bold leading-tight">
              Посмотрите, как это работает
            </h2>
            <p className="mt-3 text-sm text-white/55 max-w-xl mx-auto">
              От сканирования QR до уведомления в админке — реальная запись из сервиса. Без монтажа, без украшений.
            </p>
          </div>

          <div className="relative">
            <div className="absolute -inset-6 bg-gradient-to-tr from-mint-500/15 via-purple-500/15 to-cyan-500/15 blur-3xl rounded-full pointer-events-none" />
            <div className="relative">
              <DemoHeroVideo />
            </div>
          </div>
        </div>
      </section>

      {/* ===== Selling stats ===== */}
      <section id="metrics" className="py-16 border-y border-white/5 bg-white/[0.015]">
        <div className="max-w-6xl mx-auto px-5">
          <div className="max-w-2xl mb-10">
            <div className="text-mint-400 text-xs font-semibold tracking-wider uppercase mb-1.5">Платформа в работе</div>
            <h2 className="text-2xl sm:text-3xl font-bold leading-tight">
              Цифры, которые говорят за себя
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            <SellingMetric value="+24%" label="К среднему чеку" sub="у ресторанов с самостоятельным заказом" tone="mint" testid="stat-avg-check" />
            <SellingMetric value="−40%" label="Времени официантов" sub="на приём заказов и счёт" tone="emerald" testid="stat-staff-time" />
            <SellingMetric value="< 1 день" label="Запуск" sub="от заявки до первого QR на столе" tone="cyan" testid="stat-launch" />
            <SellingMetric value="99.9%" label="Аптайм" sub="меню всегда доступно гостю" tone="amber" testid="stat-uptime" />
            <SellingMetric value="0 ₽" label="За приложения" sub="меню открывается в любом браузере" tone="purple" testid="stat-zero-app" />
          </div>
        </div>
      </section>

      {/* ===== Benefits ===== */}
      <section id="benefits" className="py-24">
        <div className="max-w-6xl mx-auto px-5">
          <div className="max-w-2xl mb-14">
            <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Что вы получаете</div>
            <h2 className="text-3xl sm:text-5xl font-bold leading-tight">
              Решение конкретных задач<br />
              <span className="text-white/50">владельца ресторана</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            <BenefitCard
              icon={<QrCode />}
              title="Гости заказывают сами"
              desc="QR-код на столе → меню с фото → корзина → заказ на кухню. Официанты не бегают между залом и компьютером, очереди уходят, средний чек растёт."
              tone="mint"
            />
            <BenefitCard
              icon={<Bot />}
              title="Уведомления в Telegram"
              desc="Каждый новый заказ и вызов официанта приходят прямо в чат ресторана. Утренний дайджест с продажами за вчера. Алерты по марже."
              tone="cyan"
            />
            <BenefitCard
              icon={<BarChart3 />}
              title="Понятная аналитика"
              desc="Сколько заказов и просмотров за день. Что заказывают чаще всего. Какие блюда перестали продаваться. Решения — на цифрах."
              tone="emerald"
            />
            <BenefitCard
              icon={<Wallet />}
              title="Доставка и предзаказ"
              desc="Гость может оформить заказ домой или на конкретное время. Адрес, телефон, комментарий — приходят в админку готовыми."
              tone="amber"
            />
            <BenefitCard
              icon={<Languages />}
              title="Меню для туристов"
              desc="Один клик — и всё меню переведено на английский (или другой язык). Гость переключает флажком в шапке. Никакой ручной работы."
              tone="purple"
            />
            <BenefitCard
              icon={<Globe />}
              title="Свой домен и бренд"
              desc="menu.вашресторан.by вместо длинной ссылки. Логотип, цвета, слоган. Гости видят ваш бренд, а не платформу."
              tone="rose"
            />
          </div>
        </div>
      </section>

      {/* ===== AI Multilingual feature ===== */}
      <section id="multilang" className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] rounded-full bg-purple-500/8 blur-[140px]" />
        </div>
        <div className="max-w-6xl mx-auto px-5">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* LEFT: text */}
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-300 text-xs font-medium mb-5">
                <Sparkles className="w-3.5 h-3.5" />
                AI · Автоматический перевод
              </div>
              <h2 className="text-3xl sm:text-5xl font-bold leading-[1.1] mb-5">
                Меню для иностранных гостей —{' '}
                <span className="bg-gradient-to-r from-purple-300 to-pink-300 bg-clip-text text-transparent">
                  без ручной работы
                </span>
              </h2>
              <p className="text-white/60 leading-relaxed mb-8 max-w-lg">
                Добавили блюдо на русском — английская версия появляется через несколько секунд автоматически.
                Ваш переводчик — Google Gemini AI с кулинарным контекстом: знает, что «борщ» это <em>Borscht</em>,
                а не <em>beet soup</em>, и сохраняет аппетитный тон.
              </p>

              <ul className="space-y-3 mb-8">
                <FeatureBullet icon={<Zap className="w-4 h-4" />} text="Авто-перевод при сохранении блюда — за 2-3 секунды" />
                <FeatureBullet icon={<RefreshCcw className="w-4 h-4" />} text="Изменили цену или описание — перевод регенерируется" />
                <FeatureBullet icon={<Languages className="w-4 h-4" />} text="Переключение RU / EN флагом в шапке клиентского меню" />
                <FeatureBullet icon={<ShoppingBag className="w-4 h-4" />} text="Корзина, бейджи, статусы заказа — всё переведено" />
              </ul>

              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-200/80">
                <span className="font-semibold text-amber-300">Один клик</span> — и всё существующее меню переводится одной командой в админке («Настройки → Переводы»).
              </div>
            </div>

            {/* RIGHT: bilingual menu card */}
            <div className="relative">
              <div className="absolute -inset-8 bg-gradient-to-tr from-purple-500/15 via-pink-500/10 to-mint-500/10 blur-3xl rounded-full" />

              <div className="relative grid grid-cols-2 gap-3">
                <BilingualCard
                  flag="🇷🇺"
                  lang="Русский"
                  title="Сырники со сметаной"
                  desc="Воздушные творожные шарики с вишнево-розмариновым соусом"
                  cat="Завтраки до 16:00"
                />
                <BilingualCard
                  flag="🇬🇧"
                  lang="English"
                  title="Syrniki with sour cream"
                  desc="Airy cottage cheese balls with cherry-rosemary sauce"
                  cat="Breakfasts until 4 PM"
                  highlight
                />

                <BilingualCard
                  flag="🇷🇺"
                  lang="Русский"
                  title="Тост с лососем и авокадо"
                  desc="С кремом из мяты и базилика"
                  cat="Закуски"
                  compact
                />
                <BilingualCard
                  flag="🇬🇧"
                  lang="English"
                  title="Salmon avocado toast"
                  desc="With mint-basil cream"
                  cat="Starters"
                  highlight
                  compact
                />
              </div>

              {/* Arrow indicator */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-purple-500/30 border border-purple-400/50 backdrop-blur-md flex items-center justify-center text-purple-200 z-10 shadow-2xl">
                <ArrowRight className="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Screenshots — how it looks ===== */}
      <section id="screens" className="py-24 border-y border-white/5 bg-gradient-to-b from-transparent via-white/[0.015] to-transparent">
        <div className="max-w-6xl mx-auto px-5">
          <div className="max-w-2xl mb-14">
            <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Как выглядит</div>
            <h2 className="text-3xl sm:text-5xl font-bold leading-tight">
              Не моки.<br />
              <span className="text-white/50">Реальные скриншоты сервиса.</span>
            </h2>
          </div>

          {/* Big featured screenshot — admin orders */}
          <ScreenshotBlock
            tag="Админка → Заказы"
            title="Все заказы на одном экране"
            desc="Зелёная кнопка «Завершить» — и заказ закрыт. Жёлтая «В работу» — кухня видит, что приняли в готовку. Красная — отменить. Без обучения сотрудников."
            image="/demo-shots/orders.jpg"
            testid="screen-orders"
          />

          <div className="grid md:grid-cols-2 gap-6 mt-6">
            <ScreenshotBlock
              tag="Админка → Аналитика"
              title="Видите всё за период"
              desc="Просмотры, заказы, выручка, вызовы — за день, неделю, месяц. Графики по дням, топ блюд."
              image="/demo-shots/analytics.jpg"
              compact
              testid="screen-analytics"
            />
            <ScreenshotBlock
              tag="Админка → Меню"
              title="Меню обновляется за секунду"
              desc="Драг-н-дроп категорий, фотки блюд, баннеры с акциями. Изменили цену — гость сразу видит новую."
              image="/demo-shots/menu_admin.jpg"
              compact
              testid="screen-menu"
            />
          </div>

          <div className="grid md:grid-cols-2 gap-6 mt-12 items-center">
            <div>
              <span className="inline-block text-[10px] font-bold uppercase tracking-widest text-mint-300 px-2.5 py-1 rounded-full bg-mint-500/15 border border-mint-500/30 mb-4">
                Глазами гостя
              </span>
              <h3 className="text-2xl sm:text-3xl font-bold leading-tight mb-4">
                Так гость видит ваше меню
              </h3>
              <p className="text-white/60 leading-relaxed mb-6">
                Тёмная тема, фото блюд, секции и категории, поиск, переключатель языка.
                На любом телефоне — в браузере, без установки приложений.
              </p>
              <ul className="space-y-3">
                <FeatureBullet icon={<Smartphone className="w-4 h-4" />} text="Mobile-first дизайн под телефон" />
                <FeatureBullet icon={<Languages className="w-4 h-4" />} text="Переключение RU / EN — одним флагом" />
                <FeatureBullet icon={<Bell className="w-4 h-4" />} text="Кнопка «Вызвать официанта» с шаблонами" />
                <FeatureBullet icon={<ShoppingBag className="w-4 h-4" />} text="Корзина и оформление в один тап" />
              </ul>
            </div>
            <div className="flex justify-center md:justify-end gap-4">
              <PhoneFrame src="/demo-shots/client_menu_en.jpg" alt="Клиентское меню — главная" testid="screen-client-1" />
              <PhoneFrame src="/demo-shots/client_menu_scrolled.jpg" alt="Клиентское меню — категория" testid="screen-client-2" className="hidden lg:block" />
            </div>
          </div>
        </div>
      </section>

      {/* ===== Try as guest ===== */}
      <section id="try" className="py-24">
        <div className="max-w-6xl mx-auto px-5">
          <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Попробуйте</div>
          <h2 className="text-3xl sm:text-5xl font-bold mb-4 leading-tight">
            Закажите ужин у нас
          </h2>
          <p className="text-white/55 max-w-2xl leading-relaxed">
            Это настоящее клиентское меню демо-ресторана «{demoMenu?.restaurant_name || 'Мята'}», стол №{demoMenu?.table_number || 1}.
            Отсканируйте QR с телефона или откройте по ссылке — добавляйте блюда в корзину, всё работает.
          </p>

          <div className="mt-12 grid md:grid-cols-2 gap-10 items-center">
            <div className="relative mx-auto md:ml-0">
              <div className="absolute -inset-6 bg-gradient-to-tr from-mint-500/20 via-cyan-500/10 to-purple-500/20 blur-3xl rounded-full" />
              <div className="relative w-[280px] h-[560px] rounded-[44px] border-[10px] border-[#1a1f2e] bg-[#0d1424] shadow-2xl overflow-hidden">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-28 h-6 bg-[#1a1f2e] rounded-b-2xl z-10" />
                <div className="h-full flex flex-col items-center justify-center text-center p-6 pt-10 bg-gradient-to-b from-[#0d1424] to-[#141b2e]">
                  <div className="text-[10px] uppercase tracking-widest text-white/40 mb-3">Меню ресторана</div>
                  <div className="font-bold text-lg mb-4 text-white leading-tight">
                    {demoMenu?.restaurant_name || 'Мята Спортивная'}
                  </div>
                  <div className="p-4 rounded-2xl bg-white shadow-inner">
                    {demoMenuUrl ? (
                      <QRCodeSVG value={demoMenuUrl} size={180} level="M" includeMargin={false} data-testid="demo-guest-qr" />
                    ) : (
                      <div className="w-[180px] h-[180px] rounded-lg bg-slate-200 animate-pulse" />
                    )}
                  </div>
                  <div className="mt-4 text-xs text-white/50">Стол №{demoMenu?.table_number || 1}</div>
                  <div className="mt-6 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-mint-500/20 border border-mint-500/30 text-mint-300 text-[11px]">
                    <Zap className="w-3 h-3" /> Наведите камеру телефона
                  </div>
                </div>
              </div>
            </div>

            <div>
              <div className="space-y-4">
                <GuestFeature icon={<Eye />} title="Полностью рабочее меню" desc="Не превью и не моки — те же экраны, что отдаются настоящим гостям." />
                <GuestFeature icon={<ShoppingBag />} title="Живая корзина" desc="Добавьте блюда, оформите заказ — он попадёт в админку (можно посмотреть после входа)." />
                <GuestFeature icon={<Languages />} title="RU / EN переключатель" desc="Попробуйте переключить язык — все блюда переведены автоматически через AI." />
                <GuestFeature icon={<Clock />} title="Без регистрации гостю" desc="Гость попадает в меню по ссылке или QR — телефон, регистрация, приложения не нужны." />
              </div>

              {demoMenuUrl && (
                <a href={demoMenuUrl} target="_blank" rel="noopener noreferrer" className="mt-8 px-6 h-12 inline-flex items-center gap-2 rounded-full bg-white text-[#0a0e1a] font-semibold hover:bg-mint-300 transition-colors" data-testid="demo-guest-open-link">
                  Открыть меню в новой вкладке <ExternalLink className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ===== Final CTA — Demo access + Contact ===== */}
      <section id="contact" className="py-24 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-5">
          <div className="relative rounded-3xl overflow-hidden border border-white/10 p-10 sm:p-14 bg-gradient-to-br from-mint-500/10 via-purple-500/10 to-transparent">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(93,169,164,0.2),transparent_60%)]" />
            <div className="relative grid md:grid-cols-2 gap-10 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-mint-500/20 border border-mint-500/40 text-mint-300 text-xs font-medium mb-5">
                  <Rocket className="w-3.5 h-3.5" />
                  Попробуйте админку
                </div>
                <h2 className="text-3xl sm:text-4xl font-bold leading-tight">
                  Зайдите внутрь<br />с тестовым аккаунтом
                </h2>
                <p className="mt-4 text-white/60 leading-relaxed">
                  Полный доступ к админке двух демо-ресторанов: меню, заказы, аналитика,
                  настройки Telegram-бота. Можно тыкать всё — данные не сбрасываются.
                </p>

                <CredentialBox login="demo" password="demo2026" />

                <Link to="/login" className="mt-6 px-6 h-12 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-mint-400 to-emerald-500 text-[#0a0e1a] font-semibold hover:shadow-2xl hover:shadow-mint-500/30 transition-all hover:-translate-y-0.5" data-testid="demo-final-cta">
                  Открыть админку <ArrowRight className="w-5 h-5" />
                </Link>
              </div>

              <div className="md:border-l md:border-white/10 md:pl-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-sky-500/20 border border-sky-500/40 text-sky-300 text-xs font-medium mb-5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  Подключить свой ресторан
                </div>
                <h3 className="text-2xl sm:text-3xl font-bold leading-tight">
                  Хотите такую же<br />платформу для себя?
                </h3>
                <p className="mt-4 text-white/60 leading-relaxed">
                  Запуск за 1 день: импортируем меню, выпускаем QR-коды, подключаем Telegram-бот.
                  Дальше — добавляете официантов и работаете.
                </p>

                <a href="https://t.me/king_saas" target="_blank" rel="noopener noreferrer" className="mt-6 px-6 h-12 inline-flex items-center gap-2 rounded-full bg-[#229ED9] hover:bg-[#1c8ec3] text-white font-semibold transition-all hover:-translate-y-0.5 shadow-lg shadow-sky-500/30" data-testid="demo-telegram-contact">
                  <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295-.002 0-.003 0-.005 0l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.121l-6.869 4.326-2.96-.924c-.64-.203-.658-.64.135-.954l11.566-4.458c.538-.196 1.006.128.832.941z" />
                  </svg>
                  Написать @king_saas
                  <ExternalLink className="w-4 h-4 opacity-60" />
                </a>

                <div className="mt-6 text-sm text-white/40 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Обычно отвечаю в течение часа
                </div>
              </div>
            </div>
          </div>

          <div className="text-center mt-8">
            <a href="#top" className="px-6 h-11 inline-flex items-center gap-2 rounded-full border border-white/15 hover:bg-white/5 transition-colors text-sm text-white/70">
              Наверх
            </a>
          </div>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="py-10 border-t border-white/5 text-center text-sm text-white/40">
        <div className="max-w-6xl mx-auto px-5 flex flex-wrap items-center justify-between gap-4">
          <div>© 2026 REST-MENU · Платформа цифрового меню для ресторанов</div>
          <a href="https://t.me/king_saas" target="_blank" rel="noopener noreferrer" className="hover:text-white/80 transition-colors inline-flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5" />
            @king_saas
          </a>
        </div>
      </footer>
    </div>
  );
}

// ============ Sub-components ============

const SUBTITLES = [
  { from: 0,    to: 3.2,  text: 'Гость сканирует QR — открывается меню', icon: <QrCode className="w-3.5 h-3.5" /> },
  { from: 3.2,  to: 7,    text: 'Листает категории, видит фото и описания',  icon: <Smartphone className="w-3.5 h-3.5" /> },
  { from: 7,   to: 11.5,  text: 'Один клик — меню переведено на английский', icon: <Languages className="w-3.5 h-3.5" /> },
  { from: 11.5, to: 16,   text: 'Ресторан видит заказы в админке',  icon: <ShoppingBag className="w-3.5 h-3.5" /> },
  { from: 16,   to: 23,   text: 'И всю аналитику за период — графики, топ блюд', icon: <BarChart3 className="w-3.5 h-3.5" /> },
];

function DemoHeroVideo() {
  const [v, setV] = useState(null);
  const [t, setT] = useState(0);
  useEffect(() => {
    if (!v) return;
    const onTime = () => setT(v.currentTime);
    v.addEventListener('timeupdate', onTime);
    return () => v.removeEventListener('timeupdate', onTime);
  }, [v]);

  const current = SUBTITLES.find((s) => t >= s.from && t < s.to);

  return (
    <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-black aspect-[16/9]" data-testid="demo-hero-video-wrap">
      <video
        ref={(el) => setV(el)}
        src="/demo.mp4"
        poster="/og-image.jpg"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        className="w-full h-full object-cover block"
        data-testid="demo-hero-video"
      />

      {/* Bottom gradient for legibility */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-black/85 via-black/40 to-transparent" />

      {/* Subtitle */}
      <div className="absolute bottom-4 inset-x-4 flex justify-center pointer-events-none">
        <div
          key={current?.from ?? 'none'}
          className={
            'inline-flex items-center gap-2 px-4 py-2 rounded-full bg-black/70 backdrop-blur-md border border-white/15 text-sm font-medium text-white shadow-2xl ' +
            (current ? 'animate-[subFade_400ms_ease-out]' : 'opacity-0')
          }
          data-testid="demo-video-subtitle"
        >
          {current && (
            <>
              <span className="text-mint-300">{current.icon}</span>
              <span>{current.text}</span>
            </>
          )}
        </div>
        <style>{`@keyframes subFade { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }`}</style>
      </div>

      {/* Live indicator */}
      <div className="absolute top-3 left-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/60 backdrop-blur-sm border border-white/10 text-[11px] font-semibold">
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-400" />
        </span>
        <span className="text-white/90">Демо</span>
      </div>

      {/* Progress bar — segments */}
      <div className="absolute top-0 inset-x-0 flex gap-0.5 px-1 pt-1 pointer-events-none">
        {SUBTITLES.map((s, i) => {
          const len = s.to - s.from;
          const local = Math.max(0, Math.min(len, t - s.from));
          const pct = (local / len) * 100;
          return (
            <div key={i} className="flex-1 h-0.5 rounded-full bg-white/15 overflow-hidden">
              <div className="h-full bg-mint-400 transition-[width] duration-100" style={{ width: `${pct}%` }} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FloatingChip({ icon, text, tone, delay }) {
  const tones = {
    emerald: 'from-emerald-500/30 to-emerald-500/10 border-emerald-500/30 text-emerald-200',
    amber: 'from-amber-500/30 to-amber-500/10 border-amber-500/30 text-amber-200',
  };
  return (
    <div
      className={`px-3 py-2 rounded-xl border bg-gradient-to-br ${tones[tone]} backdrop-blur-md flex items-center gap-2 text-xs font-semibold shadow-2xl`}
      style={{ animation: `float 4s ease-in-out ${delay}ms infinite` }}
    >
      {icon}
      {text}
      <style>{`@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }`}</style>
    </div>
  );
}

function BilingualCard({ flag, lang, title, desc, cat, highlight = false, compact = false }) {
  return (
    <div
      className={
        'rounded-xl border p-4 backdrop-blur-sm transition-all ' +
        (highlight
          ? 'border-purple-400/40 bg-gradient-to-br from-purple-500/15 to-pink-500/10 shadow-lg shadow-purple-500/10'
          : 'border-white/10 bg-white/[0.03]')
      }
    >
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2.5">
        <span className="text-base leading-none">{flag}</span>
        <span className={highlight ? 'text-purple-200' : 'text-white/40'}>{lang}</span>
      </div>
      <div className={'text-[10px] uppercase tracking-wider mb-1 ' + (highlight ? 'text-purple-300/70' : 'text-white/30')}>
        {cat}
      </div>
      <div className={'font-semibold leading-snug ' + (compact ? 'text-sm' : 'text-base')}>{title}</div>
      <div className={'text-white/55 mt-1 leading-snug ' + (compact ? 'text-[11px]' : 'text-xs')}>{desc}</div>
    </div>
  );
}

function SellingMetric({ value, label, sub, tone, testid }) {
  const toneMap = {
    mint: 'from-mint-500/20 to-mint-500/5 border-mint-500/30 text-mint-300',
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30 text-emerald-300',
    cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/30 text-cyan-300',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/30 text-amber-300',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30 text-purple-300',
  };
  const valueColor = toneMap[tone].split(' ').pop();
  return (
    <div
      className={`group relative rounded-2xl border bg-gradient-to-br ${toneMap[tone]} p-5 hover:-translate-y-0.5 transition-transform`}
      data-testid={testid}
    >
      <div className={`text-3xl sm:text-4xl font-bold tabular-nums tracking-tight ${valueColor}`}>{value}</div>
      <div className="text-sm font-semibold text-white/85 mt-2">{label}</div>
      <div className="text-xs text-white/45 mt-1 leading-snug">{sub}</div>
    </div>
  );
}

function LiveMetric({ value, delta, label, icon, testid }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (typeof value !== 'number') return;
    const start = performance.now();
    const duration = 900;
    let raf;
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  const loading = typeof value !== 'number';
  return (
    <div className="relative rounded-2xl border border-white/10 bg-white/[0.02] p-4 hover:border-mint-500/30 hover:bg-white/[0.04] transition-all group" data-testid={testid}>
      <div className="flex items-center justify-between mb-3">
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center [&>svg]:w-4 [&>svg]:h-4 text-mint-300 group-hover:scale-110 transition-transform">{icon}</div>
        {!!delta && delta > 0 && (
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/20">+{delta} / 24ч</span>
        )}
      </div>
      <div className="text-2xl sm:text-3xl font-bold tracking-tight">
        {loading ? <span className="inline-block w-12 h-7 rounded bg-white/5 animate-pulse" /> : display.toLocaleString('ru-RU')}
      </div>
      <div className="text-xs text-white/50 mt-1">{label}</div>
    </div>
  );
}

function BenefitCard({ icon, title, desc, tone }) {
  const tones = {
    mint: 'from-mint-500/15 to-mint-500/5 hover:border-mint-500/40',
    cyan: 'from-cyan-500/15 to-cyan-500/5 hover:border-cyan-500/40',
    emerald: 'from-emerald-500/15 to-emerald-500/5 hover:border-emerald-500/40',
    amber: 'from-amber-500/15 to-amber-500/5 hover:border-amber-500/40',
    purple: 'from-purple-500/15 to-purple-500/5 hover:border-purple-500/40',
    rose: 'from-rose-500/15 to-rose-500/5 hover:border-rose-500/40',
  };
  return (
    <div className={`group rounded-2xl border border-white/10 bg-gradient-to-br ${tones[tone]} p-6 transition-all hover:-translate-y-0.5`}>
      <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center mb-4 [&>svg]:w-5 [&>svg]:h-5 text-mint-300 group-hover:scale-110 transition-transform">{icon}</div>
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="text-sm text-white/60 leading-relaxed">{desc}</p>
    </div>
  );
}

function ScreenshotBlock({ tag, title, desc, image, compact = false, testid }) {
  return (
    <div className={`rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden hover:border-white/20 transition-all ${compact ? '' : ''}`} data-testid={testid}>
      <div className="p-6 sm:p-7">
        <span className="inline-block text-[10px] font-bold uppercase tracking-widest text-mint-300 px-2.5 py-1 rounded-full bg-mint-500/15 border border-mint-500/30 mb-3">
          {tag}
        </span>
        <h3 className={`font-bold leading-tight mb-2 ${compact ? 'text-xl' : 'text-2xl sm:text-3xl'}`}>{title}</h3>
        <p className="text-sm text-white/55 leading-relaxed max-w-xl">{desc}</p>
      </div>
      <div className="border-t border-white/10 bg-[#0d1424]">
        {/* faux browser chrome */}
        <div className="h-7 px-3 border-b border-white/5 flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <img src={image} alt={title} className="w-full h-auto block" loading="lazy" />
      </div>
    </div>
  );
}

function PhoneFrame({ src, alt, testid, className = '' }) {
  return (
    <div className={`relative ${className}`} data-testid={testid}>
      <div className="absolute -inset-4 bg-gradient-to-tr from-mint-500/15 to-purple-500/15 blur-2xl rounded-full" />
      <div className="relative w-[260px] h-[540px] rounded-[40px] border-[8px] border-[#1a1f2e] bg-black shadow-2xl overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-5 bg-[#1a1f2e] rounded-b-2xl z-10" />
        <img src={src} alt={alt} className="w-full h-full object-cover object-top" loading="lazy" />
      </div>
    </div>
  );
}

function FeatureBullet({ icon, text }) {
  return (
    <li className="flex items-start gap-3 text-sm text-white/70">
      <span className="w-7 h-7 rounded-lg bg-mint-500/15 border border-mint-500/30 text-mint-300 flex items-center justify-center flex-shrink-0">
        {icon}
      </span>
      <span className="pt-1">{text}</span>
    </li>
  );
}

function GuestFeature({ icon, title, desc }) {
  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-lg bg-white/[0.04] border border-white/10 flex items-center justify-center flex-shrink-0 [&>svg]:w-5 [&>svg]:h-5 text-mint-300">{icon}</div>
      <div>
        <h4 className="font-semibold text-white">{title}</h4>
        <p className="text-sm text-white/55 mt-0.5 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function CredentialBox({ login, password }) {
  const [copied, setCopied] = useState(null);
  const copy = async (text, field) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(field);
      setTimeout(() => setCopied(null), 1500);
    } catch { /* noop */ }
  };
  return (
    <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 backdrop-blur-sm p-5 font-mono">
      <Row label="login" value={login} copied={copied === 'login'} onCopy={() => copy(login, 'login')} icon={<User className="w-3.5 h-3.5" />} testid="demo-cred-login" />
      <div className="h-px bg-white/5 my-3" />
      <Row label="password" value={password} copied={copied === 'password'} onCopy={() => copy(password, 'password')} icon={<Lock className="w-3.5 h-3.5" />} testid="demo-cred-password" />
    </div>
  );
}

function Row({ label, value, copied, onCopy, icon, testid }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/40">
        {icon}
        {label}
      </div>
      <div className="flex items-center gap-2">
        <code className="text-mint-300 text-sm sm:text-base" data-testid={testid}>{value}</code>
        <button type="button" onClick={onCopy} className="w-8 h-8 rounded-lg border border-white/10 hover:border-mint-500/40 hover:bg-white/5 flex items-center justify-center transition-colors" aria-label={`Copy ${label}`} data-testid={`${testid}-copy`}>
          {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-mint-400" /> : <Copy className="w-3.5 h-3.5 text-white/50" />}
        </button>
      </div>
    </div>
  );
}

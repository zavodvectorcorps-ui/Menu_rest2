import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles, Smartphone, Globe, QrCode, Bell, BarChart3, Bot, Wallet,
  Shield, Layers, Building2, ArrowRight, Check, Zap, Languages,
  ChefHat, ShoppingBag, MessageSquare, Lock, Rocket, Star, Github,
  Server, Code2, Database, Cloud, FileText, ExternalLink,
} from 'lucide-react';

/**
 * Public marketing/demo page — accessible at /demo without auth.
 * Used as a portfolio piece showcasing the SaaS restaurant menu platform.
 */
export default function DemoPage() {
  // Subtle parallax for hero
  const [scrollY, setScrollY] = useState(0);
  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
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
            <a href="#features" className="hover:text-white transition-colors">Возможности</a>
            <a href="#stack" className="hover:text-white transition-colors">Стек</a>
            <a href="#metrics" className="hover:text-white transition-colors">Цифры</a>
          </div>
          <Link
            to="/login"
            className="px-4 h-9 inline-flex items-center gap-1.5 rounded-full bg-white text-[#0a0e1a] text-sm font-semibold hover:bg-mint-300 transition-colors"
            data-testid="demo-cta-login"
          >
            Войти в админку <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ===== Hero ===== */}
      <section id="top" className="relative pt-32 pb-32 overflow-hidden">
        {/* Background gradient orbs + grid */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full bg-mint-500/10 blur-[120px]" style={{ transform: `translateY(${scrollY * 0.15}px)` }} />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] rounded-full bg-purple-500/10 blur-[120px]" style={{ transform: `translateY(${scrollY * -0.1}px)` }} />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.04)_1px,transparent_1px)] [background-size:32px_32px]" />
        </div>

        <div className="max-w-6xl mx-auto px-5 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-mint-500/30 bg-mint-500/10 text-mint-300 text-xs font-medium mb-8">
            <Sparkles className="w-3.5 h-3.5" />
            SaaS платформа для ресторанов
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05]">
            Цифровое меню,<br />
            <span className="bg-gradient-to-r from-mint-300 via-emerald-300 to-cyan-300 bg-clip-text text-transparent">
              которое продаёт
            </span>
          </h1>
          <p className="mt-7 text-lg sm:text-xl text-white/60 max-w-2xl mx-auto leading-relaxed">
            Multi-tenant платформа для ресторанов: онлайн-меню по QR, заказы в зал и на доставку,
            интеграция с POS, Telegram-уведомления и аналитика — всё в одной админке с feature-flags
            на каждого клиента.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/login"
              className="px-6 h-12 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-mint-400 to-emerald-500 text-[#0a0e1a] font-semibold hover:shadow-2xl hover:shadow-mint-500/30 transition-all hover:-translate-y-0.5"
              data-testid="demo-hero-cta-primary"
            >
              Открыть админку <ArrowRight className="w-5 h-5" />
            </Link>
            <a
              href="#features"
              className="px-6 h-12 inline-flex items-center gap-2 rounded-full border border-white/15 hover:bg-white/5 transition-colors text-sm"
            >
              Посмотреть возможности
            </a>
          </div>

          {/* Hero mockup — stylized "browser frame" with admin preview */}
          <div className="mt-20 relative max-w-5xl mx-auto" style={{ transform: `translateY(${scrollY * 0.05}px) perspective(1500px) rotateX(${Math.max(0, 10 - scrollY / 30)}deg)` }}>
            <div className="absolute -inset-4 bg-gradient-to-r from-mint-500/20 via-purple-500/20 to-cyan-500/20 blur-2xl rounded-3xl" />
            <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-[#0d1424] shadow-2xl">
              {/* Faux browser chrome */}
              <div className="h-9 bg-[#0d1424] border-b border-white/10 flex items-center px-4 gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/60" />
                <div className="w-3 h-3 rounded-full bg-amber-500/60" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/60" />
                <div className="ml-4 px-3 h-6 rounded-md bg-white/5 text-[11px] text-white/40 flex items-center font-mono">
                  rest-menu.by/admin/analytics
                </div>
              </div>
              {/* Mock dashboard screenshot via stylized layout */}
              <div className="grid grid-cols-12 gap-3 p-4 bg-gradient-to-br from-[#0d1424] to-[#0a0f1a]">
                <div className="col-span-3 space-y-2">
                  <div className="h-8 rounded-lg bg-white/5" />
                  <div className="h-7 rounded-lg bg-mint-500/20 border-l-2 border-mint-400" />
                  <div className="h-7 rounded-lg bg-white/5" />
                  <div className="h-7 rounded-lg bg-white/5" />
                  <div className="h-7 rounded-lg bg-white/5" />
                  <div className="h-7 rounded-lg bg-white/5" />
                </div>
                <div className="col-span-9 space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <FakeMetric icon={<Wallet />} label="Выручка" value="14 280 BYN" trend="+12%" />
                    <FakeMetric icon={<ShoppingBag />} label="Заказов" value="237" trend="+8%" />
                    <FakeMetric icon={<Star />} label="Ср. чек" value="60 BYN" trend="+3%" />
                  </div>
                  <div className="h-44 rounded-lg bg-gradient-to-br from-mint-500/10 to-purple-500/5 border border-white/5 p-3">
                    <div className="text-xs text-white/40 mb-2">Продажи по часам</div>
                    <div className="flex items-end gap-1 h-32">
                      {[40, 25, 18, 22, 35, 50, 65, 80, 95, 78, 90, 70, 55, 38].map((h, i) => (
                        <div key={i} className="flex-1 rounded-sm bg-gradient-to-t from-mint-500/40 to-mint-300/80" style={{ height: `${h}%` }} />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Metrics ===== */}
      <section id="metrics" className="py-20 border-y border-white/5 bg-white/[0.015]">
        <div className="max-w-6xl mx-auto px-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { v: '8+', l: 'модулей с feature-flag' },
              { v: '3', l: 'режима отображения меню' },
              { v: '1 клик', l: 'привязка домена' },
              { v: '< 2 мин', l: 'на нового клиента' },
            ].map((m, i) => (
              <div key={i} className="text-center">
                <div className="text-4xl sm:text-5xl font-bold bg-gradient-to-br from-white to-white/40 bg-clip-text text-transparent">{m.v}</div>
                <div className="text-sm text-white/50 mt-2">{m.l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Features ===== */}
      <section id="features" className="py-28">
        <div className="max-w-6xl mx-auto px-5">
          <div className="max-w-2xl mb-16">
            <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Возможности</div>
            <h2 className="text-4xl sm:text-5xl font-bold leading-tight">
              Всё что нужно ресторану.<br />
              <span className="text-white/50">Ничего лишнего.</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            <FeatureCard
              icon={<Building2 />}
              title="Multi-tenant SaaS"
              desc="Один сервер обслуживает десятки ресторанов. Каждому — свой набор включённых модулей: можно продать клиенту только меню, а можно — меню + Telegram + Caffesta + аналитику."
              tag="Архитектура"
              color="from-purple-500/20 to-purple-500/5"
            />
            <FeatureCard
              icon={<QrCode />}
              title="Меню по QR за 30 секунд"
              desc="QR-код для каждого стола генерируется автоматически. Печать в PDF (A5/A6) с логотипом и номером стола. Можно скачать одним PDF все QR разом — для типографии."
              tag="UX"
              color="from-mint-500/20 to-mint-500/5"
            />
            <FeatureCard
              icon={<Globe />}
              title="Кастомные домены"
              desc="Привяжите menu.client.by к ресторану — гость попадёт сразу в меню без редиректов. Один скрипт + DNS, и Let's Encrypt сертификат выпускается автоматически."
              tag="Whitelabel"
              color="from-cyan-500/20 to-cyan-500/5"
            />
            <FeatureCard
              icon={<ShoppingBag />}
              title="3 типа заказов"
              desc="В зале (по столу), Предзаказ (с указанием времени), Доставка (с адресом и телефоном). Также режим «Корзина без заказа» — гость собирает блюда и показывает официанту."
              tag="Заказы"
              color="from-amber-500/20 to-amber-500/5"
            />
            <FeatureCard
              icon={<Bot />}
              title="Telegram-бот"
              desc="Уведомления о заказах и вызовах официанта в Telegram-канал ресторана. Утренний дайджест с продажами за вчера. Алерты по марже. Авто-установка webhook'а."
              tag="Интеграции"
              color="from-sky-500/20 to-sky-500/5"
            />
            <FeatureCard
              icon={<BarChart3 />}
              title="Аналитика и POS"
              desc="Интеграция с Caffesta POS: реальная маржа по чекам, контроль цен, время первого/последнего чека за смену. Отчёты в Telegram по расписанию."
              tag="Аналитика"
              color="from-emerald-500/20 to-emerald-500/5"
            />
            <FeatureCard
              icon={<Layers />}
              title="3 режима меню"
              desc="Карточки с фото, крупные плитки 2×2 для визуального меню (десерты), компактный список (вино, виски). Настраивается на каждую категорию отдельно."
              tag="UI"
              color="from-pink-500/20 to-pink-500/5"
            />
            <FeatureCard
              icon={<Bell />}
              title="Бейджи и ярлыки"
              desc="Системные бейджи — Хит, Новинка, Острое, На вынос. Плюс полностью кастомные ярлыки (название + цвет) — Безглютеновое, Сезонное, Халяль, что угодно."
              tag="Меню"
              color="from-rose-500/20 to-rose-500/5"
            />
            <FeatureCard
              icon={<Shield />}
              title="3 уровня доступа"
              desc="Суперадмин управляет всеми ресторанами и модулями. Администратор видит все, но не трогает системные настройки. Менеджер — только свой ресторан."
              tag="Безопасность"
              color="from-indigo-500/20 to-indigo-500/5"
            />
          </div>
        </div>
      </section>

      {/* ===== Architecture diagram ===== */}
      <section className="py-28 border-y border-white/5 bg-gradient-to-b from-transparent via-white/[0.015] to-transparent">
        <div className="max-w-6xl mx-auto px-5">
          <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Архитектура</div>
          <h2 className="text-4xl sm:text-5xl font-bold mb-12 leading-tight">
            Production-ready инфраструктура
          </h2>

          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-5">
              <ArchPoint
                icon={<Server />}
                title="Docker + Nginx + Let's Encrypt"
                desc="Контейнеризованная развёртка одной командой. Nginx с динамическим resolver — никогда не падает при пересборке backend'а. Сертификаты на каждый домен автоматически."
              />
              <ArchPoint
                icon={<Database />}
                title="MongoDB с UUID-ключами"
                desc="Никаких ObjectId в API — UUID4 для всех сущностей. Pydantic-валидация на каждом эндпоинте. Чистая JSON-сериализация без хаков."
              />
              <ArchPoint
                icon={<Cloud />}
                title="Self-healing деплой"
                desc="Скрипт update.sh с git reset --hard защищает от ручных правок. Кастомные домены лежат вне git — не сбрасываются при деплое. Nginx -t валидация перед применением конфигов."
              />
              <ArchPoint
                icon={<Lock />}
                title="JWT + RBAC"
                desc="Стандартная аутентификация с ролевой моделью. Бэкенд проверяет доступ к каждому ресторану на каждом запросе — менеджер не увидит чужие заказы."
              />
            </div>

            {/* Stylized SVG diagram */}
            <div className="relative aspect-square rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-transparent p-6 overflow-hidden">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(93,169,164,0.15),transparent_70%)]" />
              <div className="relative h-full flex flex-col justify-between text-xs font-mono text-white/60">
                <div className="grid grid-cols-3 gap-2">
                  <ArchBox label="QR" sub="клиенты" tone="mint" />
                  <ArchBox label="ADMIN" sub="suite" tone="purple" />
                  <ArchBox label="BOT" sub="Telegram" tone="cyan" />
                </div>
                <div className="my-3 mx-auto h-12 w-px bg-gradient-to-b from-mint-400/50 to-transparent" />
                <ArchBox label="NGINX" sub="reverse proxy + SSL" tone="amber" wide />
                <div className="my-3 mx-auto h-12 w-px bg-gradient-to-b from-amber-400/50 to-transparent" />
                <ArchBox label="FastAPI" sub="multi-tenant backend" tone="emerald" wide />
                <div className="my-3 mx-auto h-12 w-px bg-gradient-to-b from-emerald-400/50 to-transparent" />
                <div className="grid grid-cols-2 gap-2">
                  <ArchBox label="MongoDB" sub="data" tone="rose" />
                  <ArchBox label="Caffesta" sub="POS API" tone="indigo" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Tech stack ===== */}
      <section id="stack" className="py-28">
        <div className="max-w-6xl mx-auto px-5">
          <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Стек</div>
          <h2 className="text-4xl sm:text-5xl font-bold mb-12 leading-tight">
            Современный, без зоопарка
          </h2>

          <div className="grid sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {[
              { name: 'React 18', cat: 'Frontend' },
              { name: 'Tailwind CSS', cat: 'Styling' },
              { name: 'Shadcn UI', cat: 'Components' },
              { name: 'FastAPI', cat: 'Backend' },
              { name: 'Pydantic v2', cat: 'Validation' },
              { name: 'MongoDB', cat: 'Database' },
              { name: 'APScheduler', cat: 'Cron jobs' },
              { name: 'Telegram Bot API', cat: 'Messaging' },
              { name: 'Caffesta POS', cat: 'POS API' },
              { name: 'reportlab', cat: 'PDF gen' },
              { name: 'Docker Compose', cat: 'Deploy' },
              { name: "Let's Encrypt", cat: 'SSL' },
            ].map((t, i) => (
              <div
                key={i}
                className="px-4 py-3 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-mint-500/30 transition-all"
              >
                <div className="text-white font-semibold">{t.name}</div>
                <div className="text-[11px] text-white/40 mt-0.5">{t.cat}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== Highlights ===== */}
      <section className="py-28 border-t border-white/5">
        <div className="max-w-4xl mx-auto px-5">
          <div className="text-mint-400 text-sm font-semibold tracking-wider uppercase mb-3">Ключевые решения</div>
          <h2 className="text-4xl sm:text-5xl font-bold mb-12 leading-tight">
            Технические находки
          </h2>
          <div className="space-y-3">
            <Highlight
              n="01"
              title="Динамический resolver в Nginx"
              desc="При пересборке backend контейнера Docker даёт ему новый IP. Стандартный Nginx кеширует upstream IP при старте — отсюда классические 502 после деплоя. Решение: resolver 127.0.0.11 (Docker DNS) + динамический proxy_pass через переменную. Nginx перерезолвит каждые 10 секунд без рестарта."
            />
            <Highlight
              n="02"
              title="Кастомные домены вне git"
              desc="update.sh делает git reset --hard для надёжного деплоя. Если хранить server-блоки тенант-доменов в nginx.conf — они слетают при каждом деплое. Решение: include /etc/nginx/custom-domains/*.conf и .gitignore внутри директории. Файлы — untracked, git их не трогает."
            />
            <Highlight
              n="03"
              title="ScrollSpy без библиотек"
              desc="Подсветка активной категории в шапке меню — на чистом scroll-listener с requestAnimationFrame. Логика: для каждой категории берём rect.top, выбираем ту, что только что ушла под шапку (top ≤ headerHeight, максимальный среди таких). Точное переключение в нужный момент, без дёрганий."
            />
            <Highlight
              n="04"
              title="Auto-retry для картинок"
              desc="При первой загрузке меню браузер запрашивает 30+ картинок параллельно. На HTTP/2 случаются stream resets. Свой <MenuImage /> делает до 2 ретраев с cache-busting query, decoding=async и lazy-loading. Гость даже не замечает временных сбоев."
            />
            <Highlight
              n="05"
              title="Webhook URL из request headers"
              desc="Telegram webhook endpoint автоматически вычисляет публичный URL из X-Forwarded-Host + X-Forwarded-Proto входящего запроса админа. Не нужно конфигурировать PUBLIC_BASE_URL — работает для любого тенант-домена сразу."
            />
          </div>
        </div>
      </section>

      {/* ===== Final CTA ===== */}
      <section className="py-32">
        <div className="max-w-4xl mx-auto px-5">
          <div className="relative rounded-3xl overflow-hidden border border-white/10 p-10 sm:p-16 text-center bg-gradient-to-br from-mint-500/10 via-purple-500/10 to-transparent">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(93,169,164,0.2),transparent_60%)]" />
            <div className="relative">
              <Rocket className="w-12 h-12 text-mint-300 mx-auto mb-5" />
              <h2 className="text-3xl sm:text-5xl font-bold leading-tight">Хотите посмотреть систему вживую?</h2>
              <p className="mt-4 text-white/60 max-w-xl mx-auto">
                Доступ к админке по запросу — есть демо-аккаунт с реальными данными по нескольким ресторанам.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  to="/login"
                  className="px-6 h-12 inline-flex items-center gap-2 rounded-full bg-white text-[#0a0e1a] font-semibold hover:bg-mint-300 transition-colors"
                  data-testid="demo-final-cta"
                >
                  Открыть админку <ArrowRight className="w-5 h-5" />
                </Link>
                <a
                  href="#top"
                  className="px-6 h-12 inline-flex items-center gap-2 rounded-full border border-white/15 hover:bg-white/5 transition-colors text-sm"
                >
                  Наверх
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="py-10 border-t border-white/5 text-center text-sm text-white/40">
        <div className="max-w-6xl mx-auto px-5 flex flex-wrap items-center justify-between gap-4">
          <div>© 2026 REST-MENU · Multi-tenant restaurant SaaS</div>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1"><Code2 className="w-3.5 h-3.5" /> 100% custom</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ============ Sub-components ============

function FakeMetric({ icon, label, value, trend }) {
  return (
    <div className="rounded-lg bg-white/[0.02] border border-white/5 p-3">
      <div className="flex items-center justify-between text-[10px] text-white/40">
        <span className="inline-flex items-center gap-1">
          <span className="w-3 h-3 [&>svg]:w-3 [&>svg]:h-3">{icon}</span>
          {label}
        </span>
        <span className="text-mint-400">{trend}</span>
      </div>
      <div className="text-base font-bold mt-1.5">{value}</div>
    </div>
  );
}

function FeatureCard({ icon, title, desc, tag, color }) {
  return (
    <div className={`group relative rounded-2xl border border-white/10 bg-gradient-to-br ${color} p-6 hover:border-white/20 transition-all hover:-translate-y-0.5 overflow-hidden`}>
      <div className="absolute top-0 right-0 text-[10px] font-medium text-white/40 px-2 py-0.5 m-3 rounded-full border border-white/10">
        {tag}
      </div>
      <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center mb-4 [&>svg]:w-5 [&>svg]:h-5 text-mint-300 group-hover:scale-110 transition-transform">
        {icon}
      </div>
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="text-sm text-white/55 leading-relaxed">{desc}</p>
    </div>
  );
}

function ArchPoint({ icon, title, desc }) {
  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-lg bg-mint-500/10 border border-mint-500/30 flex items-center justify-center flex-shrink-0 [&>svg]:w-5 [&>svg]:h-5 text-mint-300">
        {icon}
      </div>
      <div>
        <h3 className="font-semibold text-white">{title}</h3>
        <p className="text-sm text-white/50 mt-1 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function ArchBox({ label, sub, tone, wide }) {
  const tones = {
    mint: 'from-mint-500/30 to-mint-500/10 border-mint-500/30 text-mint-200',
    purple: 'from-purple-500/30 to-purple-500/10 border-purple-500/30 text-purple-200',
    cyan: 'from-cyan-500/30 to-cyan-500/10 border-cyan-500/30 text-cyan-200',
    amber: 'from-amber-500/30 to-amber-500/10 border-amber-500/30 text-amber-200',
    emerald: 'from-emerald-500/30 to-emerald-500/10 border-emerald-500/30 text-emerald-200',
    rose: 'from-rose-500/30 to-rose-500/10 border-rose-500/30 text-rose-200',
    indigo: 'from-indigo-500/30 to-indigo-500/10 border-indigo-500/30 text-indigo-200',
  };
  return (
    <div className={`rounded-lg border bg-gradient-to-br ${tones[tone]} px-3 py-2 ${wide ? '' : ''} text-center`}>
      <div className="font-semibold text-white text-sm">{label}</div>
      <div className="text-[10px] opacity-70">{sub}</div>
    </div>
  );
}

function Highlight({ n, title, desc }) {
  return (
    <div className="group flex gap-5 p-6 rounded-2xl border border-white/5 hover:border-mint-500/30 hover:bg-white/[0.02] transition-all">
      <div className="text-3xl font-bold text-white/15 group-hover:text-mint-400 transition-colors w-12 flex-shrink-0">{n}</div>
      <div>
        <h3 className="text-xl font-bold mb-2">{title}</h3>
        <p className="text-white/60 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

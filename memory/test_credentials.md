# Test Credentials

## Web Application

**Superadmin (полный доступ, видит всё):**
- Username: `admin`
- Password: `220066`

**Administrator (read-only для системных модулей):**
- Username: `admin_test`
- Password: `test123456`

**Demo (публичный аккаунт, показывается на /demo лендинге):**
- Username: `demo`
- Password: `demo2026`
- Role: `administrator`
- Привязан **только** к изолированному демо-ресторану (slug=`demo`, имя `Demo Restaurant`).
- Доступ к реальным ресторанам («Мята Спортивная»/«Мята Центральная») закрыт.
- Создаётся автоматически в `/api/seed` через `helpers.create_demo_user(demo_restaurant_id)` после `services.demo_seed.seed_demo_restaurant()`.

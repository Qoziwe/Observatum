# 🏛 Архитектурная документация: Observatum Server (Termux Edition)

**Observatum** — это высокоэффективная исследовательская система сбора телеметрии и визуализации данных в реальном времени (UN SDG 9 Kuala Lumpur Connectivity Research). Построена на архитектуре **Flask + Flask-SocketIO + Gunicorn (gthread) + SQLite (WAL) + Apache ECharts**.

Данная документация описывает устройство сервера в Termux, особенности демонизации через Runit, схему туннелирования трафика через Cloudflare (`observatum.andatra.space`) и регламент администрирования.

---

## 1. Схема движения трафика

Приложение совмещает публичную анкету респондента (чистый HTTP без фоновых сокетов), защищённый паролем аналитический терминал `/admin` (WebSocket real-time) и локальное хранилище SQLite. Весь входящий трафик поступает из туннеля Cloudflare Zero Trust (`termux-android`) на локальный IPv4-сокет `127.0.0.1:5005`.

```text
[ Респонденты APU / KL ]          [ Исследователь / Дашборд ]
           │                                   │
           ▼  (GET / , POST /api/submit)       ▼  (GET /admin , WSS Socket.IO)
[ HTTPS / WSS: observatum.andatra.space ]
                       │
                       ▼  (Cloudflare Edge: SSL/TLS, Zero Trust Tunnel)
[ Смартфон (Android + Termux) ]
        │
        ├─► [ cloudflared (демон: termux-android) ]
        │         │
        │         ▼  (Локальный HTTP/WS прокси на http://127.0.0.1:5005)
        └─► [ Gunicorn (демон Runit, worker: gthread, порт 5005) ]
                  │
                  ├──► [ Flask App (Jinja2 SSR + REST API + CSV/JSON Export) ]
                  ├──► [ Flask-SocketIO (On-Demand WS только для комнаты admins) ]
                  ├──► [ Analytics Engine (O(N) расчёт 15 графиков и матриц) ]
                  └──► [ SQLite: database.db (WAL / synchronous=NORMAL / timeout=15) ]
```

---

## 2. Разбор компонентов сервера

### A. База данных (SQLite WAL)
* **Файл базы:** `/data/data/com.termux/files/home/Observatum/database.db`
* **Обоснование:** Нативный `sqlite3` без ORM-прослоек обеспечивает минимальное потребление RAM (~25–35 МБ) и мгновенную запись анкет.
* **Отказоустойчивость и конкурентность:**
  - Включён журнал предзаписи `PRAGMA journal_mode=WAL;` и `timeout=15.0`, что позволяет десяткам студентов отправлять анкеты одновременно с чтением аналитики на дашборде без блокировок `database is locked`.
  - Поле `is_demo` изолирует демонстрационные записи (`+25 DEMO`) от реальных ответов респондентов: демо-выборку можно удалить одной кнопкой (`CLEAR DEMO`) без потери настоящих данных.

### B. WSGI-сервер (Gunicorn + gthread)
* **Запуск:** Многопоточный режим `gthread` (`-w 1 --threads 100`) с поддержкой `simple-websocket`.
* **Порт:** `127.0.0.1:5005` (изолирован от Eventum на `5001`, AmadeusX на `5002`, Chan на `5003` и Presentum на `5004`).

### C. Демонизация (Runit / termux-services)
* **Файл службы:** `$PREFIX/var/service/observatum-backend/run`
* **Содержимое:**
  ```bash
  #!/data/data/com.termux/files/usr/bin/sh
  exec 2>&1
  cd /data/data/com.termux/files/home/Observatum
  exec /data/data/com.termux/files/home/Observatum/venv/bin/gunicorn -w 1 --threads 100 -b 127.0.0.1:5005 app:app
  ```

### D. Сеть и Cloudflare Tunnel
* **Туннель:** `termux-android`.
* **Маршрут:** `observatum.andatra.space` ➔ `http://127.0.0.1:5005`.
* ⚠️ **Критический нюанс (IPv6 таймаут на Android):** В Cloudflare Zero Trust Dashboard (Tunnels ➔ `termux-android` ➔ Routes) адрес сервиса **обязан** быть указан как `http://127.0.0.1:5005`, а **не** `http://localhost:5005`, чтобы избежать 5-секундных задержек резолвинга `::1` в Bionic libc.

### E. Профиль энергопотребления (Zero-Drain / On-Demand WebSocket)
Специально для сохранения заряда батареи смартфона в Termux реализована трёхуровневая защита от лишних пробуждений CPU:
1. **Zero-Socket на странице анкеты (`/`):** Респонденты не открывают WebSocket-соединений вообще. Отправка анкеты — это одиночный короткий HTTP `POST /api/submit`.
2. **Серверный гейтинг (`_active_admin_sids`):** На бэкенде ведётся потокобезопасный учёт активных подключений к комнате `admins`. Если дашборд `/admin` ни у кого не открыт (`listeners == 0`), сервер при сохранении новой анкеты **не запускает аналитический пересчёт `compute_dashboard_payload()` и не вызывает `socketio.emit()`**.
3. **Клиентский спящий режим (Page Visibility API):** Если администратор свернул браузер или переключился на другую вкладку (`document.hidden === true`), страница `/admin` автоматически разрывает WebSocket (`socket.disconnect()`), переводя индикатор в `WS: SLEEPING (TAB HIDDEN)`. При возврате на вкладку соединение восстанавливается и мгновенно синхронизирует графики.
4. **Редкий heartbeat (`ping_interval=60`):** Даже при открытом экране `/admin` пинг-пакеты ходят раз в 60 секунд вместо стандартных 25 секунд.

---

## 3. Структура проекта

```text
~/Observatum/
├── .env                    # Секретный ключ сессий, пароль админа (ADMIN_PASSWORD) и порт 5005
├── .env.example            # Шаблон переменных окружения
├── database.db             # База данных SQLite в режиме WAL (создаётся автоматически)
├── app.py                  # Ядро: Flask, Socket.IO, гейтинг слушателей, авторизация и экспорт
├── database.py             # Схема SQLite, CRUD, эталонные опции ТЗ и генератор демо-выборки
├── analytics.py            # Расчёт KPI, Sankey-графа, 2D-матриц, Парето и распределений
├── requirements.txt        # Python-зависимости
├── README.md               # Техническое описание проекта
├── SERVER.md               # Документация сервера для Termux
├── venv/                   # Виртуальное окружение Python
│
├── templates/              # HTML-шаблоны (Jinja2 SSR)
│   ├── survey.html         # Анкета из 17 вопросов в стиле Architectural Concrete Brutalism
│   ├── login.html          # Закрытый экран входа в панель администратора
│   └── admin.html          # Аналитический центр реального времени (15 графиков + таблица)
│
└── static/
    ├── css/
    │   └── brutalist.css   # Дизайн-система (Raw Concrete / Obsidian Bunker)
    └── js/
        ├── socket.io.min.js    # Локальный клиент Socket.IO (Zero-CDN)
        ├── echarts.min.js      # Локальный движок инфографики Apache ECharts 5.6 (Zero-CDN)
        └── admin_dashboard.js  # Рендер 15 графиков и энергосберегающий контроллер сокетов
```

---

## 4. Пошаговое развёртывание в Termux с нуля

```bash
# 1. Клонирование репозитория
cd ~
git clone https://github.com/Qoziwe/Observatum.git
cd ~/Observatum

# 2. Создание виртуального окружения и установка пакетов
python -m venv venv
./venv/bin/pip install -r requirements.txt

# 3. Настройка .env (установить свой ADMIN_PASSWORD)
cp .env.example .env
nano .env

# 4. Создание службы Runit (termux-services)
mkdir -p $PREFIX/var/service/observatum-backend/log
ln -sf $PREFIX/share/termux-services/svlogger $PREFIX/var/service/observatum-backend/log/run

cat << 'EOF' > $PREFIX/var/service/observatum-backend/run
#!/data/data/com.termux/files/usr/bin/sh
exec 2>&1
cd /data/data/com.termux/files/home/Observatum
exec /data/data/com.termux/files/home/Observatum/venv/bin/gunicorn -w 1 --threads 100 -b 127.0.0.1:5005 app:app
EOF

chmod +x $PREFIX/var/service/observatum-backend/run
sv-enable observatum-backend
sv up observatum-backend
```

После этого в панели **Cloudflare Zero Trust ➔ Networking ➔ Tunnels ➔ `termux-android` ➔ Routes** нажать **+ Add route**:
* **Subdomain:** `observatum` (Domain: `andatra.space` ➔ `observatum.andatra.space`)
* **Service Type:** `HTTP`
* **URL:** `127.0.0.1:5005`

---

## 5. Шпаргалка администратора

### Управление службой в Termux:
* **Статус службы:**
  ```bash
  sv status observatum-backend
  ```
* **Перезапустить бэкенд (после `git pull` или смены `.env`):**
  ```bash
  sv restart observatum-backend
  ```
* **Остановить / Запустить:**
  ```bash
  sv down observatum-backend
  sv up observatum-backend
  ```
* **Просмотр логов в реальном времени:**
  ```bash
  tail -f $PREFIX/var/log/sv/observatum-backend/current
  ```

### Обновление кодовой базы из Git:
```bash
cd ~/Observatum
git pull
sv restart observatum-backend
```

### Резервное копирование и сброс базы:
* **Бэкап базы ответов:**
  ```bash
  cp ~/Observatum/database.db ~/observatum_backup_$(date +%F).db
  ```
* **Полный сброс базы (чистый старт):**
  ```bash
  rm -f ~/Observatum/database.db ~/Observatum/database.db-wal ~/Observatum/database.db-shm
  sv restart observatum-backend
  ```

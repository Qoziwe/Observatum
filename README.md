# 🏛 Observatum — Urban Digital Infrastructure & Connectivity Telemetry (UN SDG 9)

**Observatum** — специализированная исследовательская веб-платформа и аналитический терминал реального времени, разработанный для исследования городской цифровой инфраструктуры и качества интернет-соединения в Куала-Лумпуре (Asia Pacific University — **UN Sustainable Development Goal 9: Industry, Innovation, and Infrastructure**).

Выполнен в эстетике **Architectural Concrete Brutalism** (монолитный бетон, швейцарская инженерная сетка, сигнальный акцент SDG 9 `#FF4F00`) и оптимизирован для работы на персональном сервере **Android Termux** с минимальным расходом заряда батареи (**Zero-Drain On-Demand WebSocket**).

---

## 1. Ключевые особенности

* **5 секций / 17 верифицированных вопросов** согласно спецификации исследования APU SDG 9:
  - Автоматический фильтр допуска (**Q2 DGCC Eligibility Gate**): блокирует отправку анкеты студентами модуля DGCC на клиенте и сервере.
  - Строгий контроль выбора приоритетов (**Q16 Select Top 2**): интерактивное ограничение до 2 вариантов.
  - Генерация уникального академического кода квитанции (`SDG9-KL-XXXXXX`) после отправки.
* **15 интерактивных аналитических графиков (Apache ECharts 5.6)** в закрытой панели `/admin`:
  1. **Multi-Layer Sankey Diagram:** сквозной поток `KL Zone (Q4) ➔ Mobile SIM (Q5) ➔ Disconnection Frequency (Q7)`.
  2. **KL Infrastructure Composite Pain Index (0–100 Gauge):** сводный индекс стресса инфраструктуры.
  3. **2D Cross-Tab Heatmap (`Q5 × Q7`):** матрица частоты обрывов по мобильным операторам.
  4. **Mobile Operator Share vs Mean Frustration (`Q5 × Q10`):** двухшкальный бенчмарк операторов.
  5. **Fixed Broadband vs Price-Value Match (`Q6 × Q14`):** стековая матрица домашнего и кампусного интернета.
  6. **Klang Valley Geo-Vulnerability (`Q4`):** сравнение районов KL по ежедневным обрывам, фантомной сети и индексу боли.
  7. **Pareto 80/20 Bottlenecks (`Q9`):** кривая Парето по погодным, пиковым и внутридомовым триггерам сбоев.
  8. **"Full Signal, No Internet" Nightingale Rose (`Q8`):** диаграмма феномена фантомных полосок сети.
  9. **Emotional Frustration Distribution (`Q10`):** гистограмма шкалы стресса 1–5 + медиана и стандартное отклонение.
  10. **Daily Activities Impact Radar (`Q11`):** 6-осевой радар ущерба (Moodle/Teams, QR/Touch ’n Go, Grab/Waze, звонки, гейминг, облачная работа).
  11. **Coping Mechanisms Breakdown (`Q12`):** рейтинг пользовательских способов борьбы со сбоями.
  12. **Step 9 Pitch Validation Donut (`Q15`):** уровень поддержки автоматического резервного 5G/4G-трафика и скидок.
  13. **Step 9 Pitch Top-2 Priorities (`Q16`):** ранжирование главных ожидаемых улучшений от телекомов.
  14. **Support & AI Chatbot Loop vs Price Fairness Heatmap (`Q13 × Q14`):** матрица корреляции качества саппорта и восприятия цены.
  15. **Respondent Occupation Profile (`Q3`):** демографический срез участников.
* **Qualitative Field Incident Wall (`Q17`) & Verification Ledger:** живая стена историй респондентов и таблица верификации с экспортом в **CSV (UTF-8 BOM для Excel)** и **JSON**.

---

## 2. Технологический стек

* **Backend:** Python 3, Flask, Flask-SocketIO (`threading` mode + `simple-websocket`), Gunicorn (`gthread`).
* **Database:** Нативный SQLite3 в режиме `WAL` (`PRAGMA journal_mode=WAL; timeout=15.0`).
* **Frontend:** Jinja2 SSR, Vanilla JS, локальные бандлы `echarts.min.js` и `socket.io.min.js` (**Zero-CDN**), кастомная дизайн-система `brutalist.css` (темы `CONCRETE` и `BUNKER`).

---

## 3. Быстрый локальный запуск

```bash
git clone https://github.com/Qoziwe/Observatum.git
cd Observatum
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
./venv/bin/gunicorn -w 1 --threads 100 -b 127.0.0.1:5005 app:app
```

* Анкета участника: `http://127.0.0.1:5005/`
* Панель администратора: `http://127.0.0.1:5005/admin` (пароль задаётся в `.env` через `ADMIN_PASSWORD`)

# Решение тестовых заданий: LLM API-шлюз и Content Studio

Четыре независимых проекта по техническому заданию. Каждый проект запускается через `docker compose up --build` и проверяется одной командой тестов. Подробности в README внутри каждой папки.

| Папка | Задание | Стек | Тесты |
|---|---|---|---|
| [01-rate-limiter](01-rate-limiter) | Rate limiter со скользящим окном для API | FastAPI, Redis, Lua | `uv run pytest` |
| [02-django-reminders](02-django-reminders) | Напоминания о регламентных задачах, страница «Ближайшие сроки» на HTMX | Django, Celery, PostgreSQL, Redis, HTMX | `uv run pytest` |
| [03-job-queue](03-job-queue) | Очередь заданий генерации с воркерами, авторизация воркеров по токену | FastAPI, PostgreSQL, Alembic | `uv run pytest` |
| [04-dashboard](04-dashboard) | Журнал запросов к LLM, тёмная тема | React, TypeScript, Vite, TanStack Query, Recharts, Tailwind | `npm test` |

Демо дашборда публикуется на GitHub Pages workflow-файлом `.github/workflows/deploy-dashboard.yml`.

Автор: Jet Technologies.

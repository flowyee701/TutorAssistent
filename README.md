# Tutor AI

AI-ассистент для репетиторов: генерация ДЗ, ведение учеников, расписание и платежи.

## Стек

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS + shadcn/ui
- Prisma 5 + PostgreSQL 16 + pgvector
- Clerk (авторизация + webhooks)
- pnpm

## Требования

- Node.js 20+
- pnpm 9+
- Docker Desktop

## Быстрый старт

1. Установите зависимости:

   ```bash
   pnpm install
   ```

2. Скопируйте переменные окружения:

   ```bash
   cp .env.example .env.local
   ```

   Заполните Clerk-ключи из [dashboard.clerk.com](https://dashboard.clerk.com).
   `DATABASE_URL` уже настроен на локальный Docker-Postgres.

3. Поднимите Postgres:

   ```bash
   docker compose up -d
   ```

4. Примените миграции и засейте теги:

   ```bash
   pnpm db:migrate   # создаст схему в БД
   pnpm db:seed      # наполнит TaskTag деревом тегов
   ```

5. Запустите дев-сервер:

   ```bash
   pnpm dev
   ```

   Откройте [http://localhost:3000](http://localhost:3000).

## Структура каталогов

```
.
├── docker-compose.yml         # Postgres 16 + pgvector
├── prisma/
│   ├── schema.prisma          # схема БД
│   ├── seed.ts                # сидинг тегов
│   ├── tags_math_ege.json     # кодификатор ФИПИ (математика, профиль)
│   └── migrations/
└── src/
    ├── app/
    │   ├── page.tsx           # лендинг
    │   ├── sign-in/           # Clerk
    │   ├── sign-up/
    │   ├── dashboard/         # защищённая зона
    │   │   ├── homeworks/
    │   │   ├── students/
    │   │   ├── schedule/
    │   │   ├── payments/
    │   │   └── settings/
    │   └── api/webhooks/clerk/ # синхронизация User
    ├── components/
    │   ├── ui/                # shadcn/ui
    │   ├── sidebar.tsx
    │   ├── mobile-sidebar.tsx
    │   ├── theme-toggle.tsx
    │   └── providers/
    ├── lib/
    │   ├── db.ts              # Prisma singleton
    │   └── utils.ts
    ├── hooks/
    └── middleware.ts          # защита /dashboard/*
```

## Полезные команды

| Команда             | Что делает                              |
| ------------------- | --------------------------------------- |
| `pnpm dev`          | dev-сервер Next.js                      |
| `pnpm build`        | production-сборка                       |
| `pnpm lint`         | ESLint                                  |
| `pnpm format`       | Prettier (write)                        |
| `pnpm db:migrate`   | `prisma migrate dev`                    |
| `pnpm db:seed`      | сидинг тегов                            |
| `pnpm db:studio`    | Prisma Studio                           |
| `pnpm db:generate`  | сгенерировать Prisma Client             |

## Clerk webhook (синхронизация User)

В Clerk Dashboard → Webhooks → создать endpoint:

```
https://<ваш-домен>/api/webhooks/clerk
```

Подписки: `user.created`, `user.updated`, `user.deleted`.
Полученный `Signing Secret` положите в `.env.local` как `CLERK_WEBHOOK_SECRET`.

Локально вебхук можно проксировать через `ngrok` или Clerk-локальный туннель.

## Темы

Светлая/тёмная/системная — переключение через кнопку в шапке (next-themes + shadcn/ui).

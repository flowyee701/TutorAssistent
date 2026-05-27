import { currentUser } from '@clerk/nextjs/server';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const user = await currentUser();
  const email = user?.emailAddresses?.[0]?.emailAddress ?? '—';
  const name = [user?.firstName, user?.lastName].filter(Boolean).join(' ') || '—';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Настройки</h1>
        <p className="text-muted-foreground">Профиль и подписка.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Профиль</CardTitle>
            <CardDescription>Данные аккаунта из Clerk.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Имя</span>
              <span>{name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Email</span>
              <span>{email}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Подписка</CardTitle>
            <CardDescription>Текущий тариф и срок действия.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Тариф</span>
              <span>FREE</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Статус</span>
              <span>—</span>
            </div>
            <p className="pt-2 text-xs text-muted-foreground">
              Управление тарифом появится после интеграции с ЮKassa.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

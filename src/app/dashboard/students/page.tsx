import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function StudentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Ученики</h1>
          <p className="text-muted-foreground">Карточки учеников, их цели и слабые места.</p>
        </div>
        <Button disabled>Добавить ученика</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Список пуст</CardTitle>
          <CardDescription>
            Добавьте первого ученика, чтобы начать вести занятия и формировать ДЗ.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Эта страница — заглушка. Список и формы появятся позже.
        </CardContent>
      </Card>
    </div>
  );
}

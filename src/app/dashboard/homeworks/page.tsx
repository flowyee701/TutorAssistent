import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function HomeworksPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Учебники</h1>
          <p className="text-muted-foreground">Сгенерированные и черновые домашние задания.</p>
        </div>
        <Button disabled>Создать ДЗ</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Пока ничего нет</CardTitle>
          <CardDescription>
            Когда вы сгенерируете первое домашнее задание, оно появится здесь.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Эта страница — заглушка. Функциональность появится на следующих итерациях.
        </CardContent>
      </Card>
    </div>
  );
}

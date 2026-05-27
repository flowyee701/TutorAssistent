import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function SchedulePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Расписание</h1>
        <p className="text-muted-foreground">Календарь занятий и тем уроков.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Календарь пуст</CardTitle>
          <CardDescription>
            Здесь появится календарь с занятиями, когда вы добавите учеников и расписание.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Страница-заглушка.</CardContent>
      </Card>
    </div>
  );
}

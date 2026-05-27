import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function PaymentsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Платежи</h1>
        <p className="text-muted-foreground">Учёт оплат учеников и история транзакций.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Платежей пока нет</CardTitle>
          <CardDescription>Здесь будет список платежей по ученикам.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">Страница-заглушка.</CardContent>
      </Card>
    </div>
  );
}

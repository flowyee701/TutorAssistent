import Link from 'next/link';
import { SignedIn, SignedOut } from '@clerk/nextjs';

import { Button } from '@/components/ui/button';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background p-6 text-center">
      <div className="max-w-xl space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">Tutor AI</h1>
        <p className="text-muted-foreground">
          AI-ассистент для репетиторов: генерация домашних заданий, ведение учеников,
          расписание и платежи в одном месте.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <SignedOut>
          <Button asChild>
            <Link href="/sign-in">Войти</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/sign-up">Регистрация</Link>
          </Button>
        </SignedOut>
        <SignedIn>
          <Button asChild>
            <Link href="/dashboard">Перейти в кабинет</Link>
          </Button>
        </SignedIn>
      </div>
    </main>
  );
}

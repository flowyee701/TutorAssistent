'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Users, Calendar, CreditCard, Settings, GraduationCap } from 'lucide-react';

import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard/homeworks', label: 'Учебники', icon: BookOpen },
  { href: '/dashboard/students', label: 'Ученики', icon: Users },
  { href: '/dashboard/schedule', label: 'Расписание', icon: Calendar },
  { href: '/dashboard/payments', label: 'Платежи', icon: CreditCard },
  { href: '/dashboard/settings', label: 'Настройки', icon: Settings },
] as const;

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <aside className={cn('flex h-full w-60 flex-col border-r bg-card', className)}>
      <Link
        href="/dashboard"
        className="flex items-center gap-2 border-b px-5 py-4 text-lg font-semibold"
      >
        <GraduationCap className="h-6 w-6 text-primary" />
        <span>Tutor AI</span>
      </Link>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-primary/10 font-medium text-primary'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

import { UserButton } from '@clerk/nextjs';

import { Sidebar } from '@/components/sidebar';
import { MobileSidebar } from '@/components/mobile-sidebar';
import { ThemeToggle } from '@/components/theme-toggle';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar className="hidden md:flex" />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center justify-between border-b px-4 md:px-6">
          <MobileSidebar />
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <UserButton afterSignOutUrl="/" />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}

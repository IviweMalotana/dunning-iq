import { Sidebar } from "@/components/shell/sidebar";
import { Pill } from "@/components/ui/pill";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-canvas">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-surface/80 px-6 backdrop-blur">
          <div className="lg:hidden flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-[6px] bg-accent text-[11px] font-bold text-ink-invert">
              D
            </div>
            <span className="text-sm font-semibold text-ink">Dunning IQ</span>
          </div>
          <div className="hidden text-xs text-ink-subtle lg:block">
            Recovery operations
          </div>
          <div className="flex items-center gap-3">
            <Pill tone="accent" dot>
              Demo mode
            </Pill>
            <div className="flex items-center gap-2 text-xs text-ink-subtle">
              <div className="h-6 w-6 rounded-full bg-neutral-soft" />
              operator
            </div>
          </div>
        </header>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}

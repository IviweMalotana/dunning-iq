import { PageHeader } from "@/components/shell/page-header";
import { EmptyState } from "@/components/ui/states";

export const metadata = { title: "Policy & tone" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Policy & tone" subtitle="Tune the retry rules and message tone." />
      <div className="p-6">
        <div className="rounded-[var(--radius-card)] border border-border bg-surface shadow-[var(--shadow-card)]">
          <EmptyState
            title="Editor arriving in the next milestone"
            hint="You'll be able to change retry counts, backoff, and message tone here — and watch the agent adapt."
          />
        </div>
      </div>
    </>
  );
}

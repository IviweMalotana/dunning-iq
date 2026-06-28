"use client";

import { PageHeader } from "@/components/shell/page-header";
import { ErrorState } from "@/components/ui/states";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <>
      <PageHeader title="Recovery" />
      <div className="p-6">
        <ErrorState onRetry={reset} />
      </div>
    </>
  );
}

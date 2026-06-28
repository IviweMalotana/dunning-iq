import { PageHeader } from "@/components/shell/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton, StatCardSkeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <>
      <PageHeader title="Recovery" subtitle="Loading live recovery metrics…" />
      <div className="space-y-5 p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="mt-5 h-[180px] w-full" />
            </Card>
          ))}
        </div>
      </div>
    </>
  );
}

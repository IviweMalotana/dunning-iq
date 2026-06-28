import { PageHeader } from "@/components/shell/page-header";
import { QueueView } from "@/components/queue/queue-view";

export const metadata = { title: "Dunning queue" };

export default function QueuePage() {
  return (
    <>
      <PageHeader
        title="Dunning queue"
        subtitle="Every account in dunning, with its current step and the agent's next action."
      />
      <QueueView />
    </>
  );
}

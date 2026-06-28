import { PageHeader } from "@/components/shell/page-header";
import { SettingsEditor } from "@/components/settings/settings-editor";

export const metadata = { title: "Policy & tone" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="Policy & tone"
        subtitle="Tune the retry rules and message tone — watch the agent adapt on the right."
      />
      <SettingsEditor />
    </>
  );
}

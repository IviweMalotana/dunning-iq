import { CaseView } from "@/components/case/case-view";

export const metadata = { title: "Case detail" };

export default async function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CaseView id={id} />;
}

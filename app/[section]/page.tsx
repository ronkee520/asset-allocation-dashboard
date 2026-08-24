import { TerminalDashboard } from "../components/TerminalDashboard";

export default async function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  return <TerminalDashboard section={section} />;
}


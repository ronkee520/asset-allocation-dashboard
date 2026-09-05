import { TerminalDashboard } from "../../components/TerminalDashboard";

export default async function AllocationDetailPage({ params }: { params: Promise<{ detail: string }> }) {
  const { detail } = await params;
  return <TerminalDashboard section="allocation" detail={detail} />;
}

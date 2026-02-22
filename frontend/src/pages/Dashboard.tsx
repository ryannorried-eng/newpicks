import { EmptyState } from "../components/common/EmptyState";
import { LoadingSpinner } from "../components/common/LoadingSpinner";
import { ParlayCard } from "../components/parlays/ParlayCard";
import { PickCard } from "../components/picks/PickCard";
import { useParlaysToday } from "../hooks/useParlays";
import { usePicksToday } from "../hooks/usePicks";
import { useLiveOdds, usePollStatus } from "../hooks/useOdds";

export default function Dashboard() {
  const picks = usePicksToday();
  const parlays = useParlaysToday();
  const poll = usePollStatus();
  const odds = useLiveOdds();

  if (picks.isLoading || parlays.isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="space-y-3 lg:col-span-2">
          <h2 className="text-lg">Today's Picks <span className="rounded bg-gray-800 px-2 py-1 text-xs">{picks.data?.length ?? 0}</span></h2>
          {picks.data?.length ? picks.data.map((pick) => <PickCard key={pick.id} pick={pick} />) : <EmptyState title="No picks generated yet today." description="Check back closer to game time." />}
        </section>
        <section className="space-y-3">
          <h2 className="text-lg">Suggested Parlays</h2>
          {parlays.data?.length ? parlays.data.map((parlay) => <ParlayCard key={parlay.id} parlay={parlay} />) : <EmptyState title="No parlays available" description="Not enough picks for parlays today" />}
        </section>
      </div>
      <section className="rounded-xl border border-gray-800 bg-gray-900 p-4 text-sm text-gray-300">
        <h3 className="mb-3 text-gray-100">System Status</h3>
        <div className="grid gap-2 md:grid-cols-4"><div>Mode: {poll.data?.mode ?? "--"}</div><div>Quota: {poll.data?.quota_remaining ?? "--"}</div><div>Next Poll: {poll.data?.next_poll_time ? new Date(poll.data.next_poll_time).toLocaleString() : "--"}</div><div>Snapshots: {odds.data?.length ?? 0}</div></div>
      </section>
    </div>
  );
}

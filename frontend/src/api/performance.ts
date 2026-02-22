import type { PerformanceSummary } from "../types";

export const fetchPerformanceSummary = async (): Promise<PerformanceSummary> => ({
  totalPicks: 0,
  winRate: 0,
  roi: 0,
  avgClv: 0,
});

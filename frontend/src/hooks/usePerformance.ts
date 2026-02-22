import { useQuery } from "@tanstack/react-query";
import { fetchBankroll } from "../api/bankroll";
import { fetchPerformanceSummary } from "../api/performance";

export const usePerformanceSummary = () =>
  useQuery({ queryKey: ["performance", "summary"], queryFn: fetchPerformanceSummary, refetchInterval: 60_000 });

export const useBankroll = () =>
  useQuery({ queryKey: ["bankroll", "summary"], queryFn: fetchBankroll, refetchInterval: 60_000 });

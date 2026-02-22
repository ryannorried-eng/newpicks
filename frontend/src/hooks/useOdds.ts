import { useQuery } from "@tanstack/react-query";
import client from "../api/client";
import { fetchLiveOdds } from "../api/odds";
import type { PollStatus } from "../types";

export const useLiveOdds = () =>
  useQuery({ queryKey: ["odds", "live"], queryFn: fetchLiveOdds, refetchInterval: 60_000 });

export const usePollStatus = () =>
  useQuery({
    queryKey: ["system", "polling-status"],
    queryFn: () => client.get<PollStatus>("/system/polling-status").then((r) => r.data),
    refetchInterval: 60_000,
  });

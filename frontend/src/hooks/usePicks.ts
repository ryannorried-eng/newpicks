import { useQuery } from "@tanstack/react-query";
import { fetchPicksHistory, fetchPicksToday } from "../api/picks";

export const usePicksToday = () =>
  useQuery({ queryKey: ["picks", "today"], queryFn: fetchPicksToday, refetchInterval: 60_000 });

export const usePicksHistory = () =>
  useQuery({ queryKey: ["picks", "history"], queryFn: fetchPicksHistory, refetchInterval: 60_000 });

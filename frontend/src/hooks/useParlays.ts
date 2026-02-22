import { useMutation, useQuery } from "@tanstack/react-query";
import { buildParlay, fetchParlaysToday, generateParlays } from "../api/parlays";

export const useParlaysToday = () =>
  useQuery({ queryKey: ["parlays", "today"], queryFn: fetchParlaysToday, refetchInterval: 60_000 });

export const useGenerateParlays = () => useMutation({ mutationFn: generateParlays });

export const useBuildParlay = () => useMutation({ mutationFn: buildParlay });

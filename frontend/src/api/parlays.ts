import client from "./client";
import type { Parlay, ParlayBuildResponse } from "../types";

export const fetchParlaysToday = async (): Promise<Parlay[]> => {
  const response = await client.get<Parlay[]>("/parlays/today");
  return response.data;
};

export const generateParlays = async (): Promise<Parlay[]> => {
  const response = await client.post<Parlay[]>("/parlays/generate");
  return response.data;
};

export const buildParlay = async (pickIds: number[]): Promise<ParlayBuildResponse> => {
  const response = await client.post<ParlayBuildResponse>("/parlays/build", { pick_ids: pickIds });
  return response.data;
};

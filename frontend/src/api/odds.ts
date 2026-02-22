import client from "./client";
import type { OddsSnapshot } from "../types";

export const fetchLiveOdds = async (): Promise<OddsSnapshot[]> => {
  const response = await client.get<OddsSnapshot[]>("/odds/live");
  return response.data;
};

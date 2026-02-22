import client from "./client";
import type { Pick } from "../types";

export const fetchPicksToday = async (): Promise<Pick[]> => {
  const response = await client.get<Pick[]>("/picks/today");
  return response.data;
};

export const fetchPicksHistory = async (): Promise<Pick[]> => {
  const response = await client.get<Pick[]>("/picks/history");
  return response.data;
};

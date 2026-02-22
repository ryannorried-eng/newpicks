import client from "./client";

export const fetchSports = async (): Promise<string[]> => {
  const response = await client.get<string[]>("/sports");
  return response.data;
};

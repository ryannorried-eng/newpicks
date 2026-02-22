import type { BankrollSummary } from "../types";

export const fetchBankroll = async (): Promise<BankrollSummary> => ({
  balance: 1000,
  history: [],
});

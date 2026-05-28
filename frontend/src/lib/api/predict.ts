import { apiFetch } from "./client";

export type Prediction = Record<string, number | string>;

export const predictApi = {
  get: () => apiFetch<Prediction>("/predict"),
};

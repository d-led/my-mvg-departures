export interface OnTheRunConfiguration {
  radiusMeters: number;
  maxDeparturesPerStop?: number;
  maxDeparturesPerRoute?: number;
  updateLocationIntervalSeconds?: number;
  updateLocationOnEveryPoll?: boolean;
  useAdapters?: string[];
  usePreciseLocation?: boolean;
  smartSubStops?: boolean;
  randomHeaderColors?: boolean;
}

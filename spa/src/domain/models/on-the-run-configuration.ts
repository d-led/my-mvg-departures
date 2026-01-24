export interface OnTheRunConfiguration {
  radiusMeters: number;
  maxDeparturesPerStop?: number;
  maxDeparturesPerRoute?: number;
  updateLocationIntervalSeconds?: number;
  useAdapters?: string[];
  usePreciseLocation?: boolean;
  smartSubStops?: boolean;
}

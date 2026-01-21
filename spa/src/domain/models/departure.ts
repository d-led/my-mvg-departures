export interface Departure {
  time: Date;
  plannedTime: Date;
  delaySeconds: number | null; // Match Python: delay_seconds: int | None
  platform: string | null;
  isRealtime: boolean;
  line: string;
  destination: string;
  transportType: string;
  icon: string;
  isCancelled: boolean;
  messages: string[];
  stopPointGlobalId: string | null;
}

export function createDeparture(data: {
  time: Date | number;
  plannedTime: Date | number;
  delaySeconds?: number | null;
  platform?: string | null;
  isRealtime?: boolean;
  line: string;
  destination: string;
  transportType: string;
  icon?: string;
  isCancelled?: boolean;
  messages?: string[];
  stopPointGlobalId?: string | null;
}): Departure {
  return {
    time: data.time instanceof Date ? data.time : new Date(data.time),
    plannedTime:
      data.plannedTime instanceof Date
        ? data.plannedTime
        : new Date(data.plannedTime),
    delaySeconds: data.delaySeconds ?? null, // Match Python: defaults to None, not 0
    platform: data.platform ?? null,
    isRealtime: data.isRealtime ?? false,
    line: data.line,
    destination: data.destination,
    transportType: data.transportType,
    icon: data.icon ?? "",
    isCancelled: data.isCancelled ?? false,
    messages: data.messages ?? [],
    stopPointGlobalId: data.stopPointGlobalId ?? null,
  };
}

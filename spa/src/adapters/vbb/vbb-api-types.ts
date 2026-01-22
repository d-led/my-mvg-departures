// Types for VBB API responses (v6.bvg.transport.rest)

export interface VbbApiLine {
  name?: string;
  id?: string;
  product?: string;
}

export interface VbbApiDestination {
  name?: string;
}

export interface VbbApiRemark {
  text?: string;
}

export interface VbbApiDeparture {
  when?: string; // ISO 8601 datetime string
  plannedWhen?: string; // ISO 8601 datetime string
  line?: VbbApiLine;
  direction?: string;
  destination?: VbbApiDestination;
  platform?: string | number;
  cancelled?: boolean;
  realtime?: boolean;
  remarks?: (VbbApiRemark | string)[];
}

export interface VbbApiResponse {
  departures?: VbbApiDeparture[];
}

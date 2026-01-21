import type { AppConfig } from "../models/app-config.js";

export interface ConfigStorage {
  getConfig(): Promise<AppConfig | null>;
  saveConfig(config: AppConfig): Promise<void>;
  getCurrentRoutePath(): Promise<string | null>;
  setCurrentRoutePath(path: string): Promise<void>;
}

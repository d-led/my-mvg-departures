import type { ConfigStorage } from "../../domain/ports/config-storage.js";
import type { AppConfig } from "../../domain/models/app-config.js";

const CONFIG_KEY = "mvg_departures_config";
const CONFIG_TOML_KEY = "mvg_departures_config_toml"; // Store raw TOML verbatim
const CURRENT_ROUTE_KEY = "mvg_departures_current_route";

export class LocalStorageConfigStorage implements ConfigStorage {
  async getConfig(): Promise<AppConfig | null> {
    try {
      const stored = localStorage.getItem(CONFIG_KEY);
      if (!stored) {
        return null;
      }
      return JSON.parse(stored);
    } catch (error) {
      console.error("Failed to get config:", error);
      return null;
    }
  }

  async saveConfig(config: AppConfig): Promise<void> {
    try {
      localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
    } catch (error) {
      console.error("Failed to save config:", error);
      throw error;
    }
  }

  // Store raw TOML string verbatim
  async saveConfigToml(tomlString: string): Promise<void> {
    try {
      localStorage.setItem(CONFIG_TOML_KEY, tomlString);
    } catch (error) {
      console.error("Failed to save config TOML:", error);
      throw error;
    }
  }

  // Get raw TOML string verbatim
  async getConfigToml(): Promise<string | null> {
    try {
      return localStorage.getItem(CONFIG_TOML_KEY);
    } catch (error) {
      console.error("Failed to get config TOML:", error);
      return null;
    }
  }

  async getCurrentRoutePath(): Promise<string | null> {
    try {
      return localStorage.getItem(CURRENT_ROUTE_KEY);
    } catch (error) {
      console.error("Failed to get current route:", error);
      return null;
    }
  }

  async setCurrentRoutePath(path: string): Promise<void> {
    try {
      localStorage.setItem(CURRENT_ROUTE_KEY, path);
    } catch (error) {
      console.error("Failed to set current route:", error);
    }
  }
}

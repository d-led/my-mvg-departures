import App from "./components/App.svelte";
import { mount } from "svelte";

function init() {
  // Find the container element
  const target = document.querySelector(".container[data-phx-main]");

  if (!target) {
    console.error("Container element not found");
    return;
  }

  // Clear existing content but keep the element
  target.innerHTML = "";

  // Svelte 5 uses mount() function from svelte package
  try {
    const app = mount(App, {
      target: target as HTMLElement,
    });
    return app;
  } catch (error) {
    console.error("Failed to mount Svelte app:", error);
  }
}

// Wait for DOM to be ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  // DOM already ready
  init();
}

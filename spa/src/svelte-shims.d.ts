declare module "*.svelte" {
  import type { Component } from "svelte";
  const component: Component<HTMLElement>;
  export default component;
}

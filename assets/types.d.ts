import type { Alpine as AlpineType } from "alpinejs";

declare global {
  interface Window {
    // main.ts assigns Alpine to the window so templates can reach it from
    // x-data expressions.
    Alpine: AlpineType;
  }
}

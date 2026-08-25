// Runs before body renders to prevent flash of wrong theme
const saved = localStorage.getItem("theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
if (saved === "dark" || (!saved && prefersDark)) {
  document.documentElement.classList.add("dark");
} else {
  document.documentElement.classList.remove("dark");
}

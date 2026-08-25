function initThemeSwitcher(): void {
  document
    .querySelectorAll<HTMLButtonElement>("[data-theme-toggle]")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const isDark = document.documentElement.classList.toggle("dark");
        localStorage.setItem("theme", isDark ? "dark" : "light");
      });
    });
}

document.addEventListener("DOMContentLoaded", initThemeSwitcher);

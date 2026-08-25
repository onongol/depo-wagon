import htmx from "htmx.org";
(window as any).htmx = htmx;
import Alpine from "alpinejs";
window.Alpine = Alpine;
Alpine.start();

import "./theme/theme_switcher";

import htmx from "htmx.org";
(window as any).htmx = htmx;
import Alpine from "alpinejs";
window.Alpine = Alpine;
Alpine.start();

import "./theme/theme_switcher";

// Replaced by Alpine.js:
// import "./sidebar/sidebar_toggle";
// import "./alert/alert_close";
// import "./alert/auto_hide_alert";
// import "./filters/filter_toggle";
// import "./modals/modals";

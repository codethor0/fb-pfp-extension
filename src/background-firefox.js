// Firefox entry point. Firefox MV3 has no service workers and requires
// background.scripts with an event page; Chrome requires background
// .service_worker. Both point at the same module tree so the logic stays
// single-sourced. Manifest V3 with type "module" background scripts needs
// Firefox 141+, which is what browser_specific_settings.gecko declares.
import './background.mjs';

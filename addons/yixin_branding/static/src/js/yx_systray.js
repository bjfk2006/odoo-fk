/** @odoo-module **/
import { registry } from "@web/core/registry";
import { session } from "@web/session";

// Hide the top notification (messaging) systray icon unless enabled in
// Settings -> 易新界面 -> 显示顶部通知. Loaded after `mail`, so the item is
// already registered by the time we remove it.
const systray = registry.category("systray");
if (!session.yx_show_notification && systray.contains("mail.messaging_menu")) {
    systray.remove("mail.messaging_menu");
}

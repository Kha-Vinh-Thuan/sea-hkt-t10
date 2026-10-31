/** @odoo-module **/

import { useListener } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

// Keep the sidebar selection in sync with navigation within Recruitment.
patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.state.ahoLocation = window.location.pathname;
        useListener(window, "popstate", () => {
            this.state.ahoLocation = window.location.pathname;
        });
    },

    async _onMenuClicked(menu) {
        await super._onMenuClicked(menu);
        this.state.ahoLocation = window.location.pathname;
    },

    isSidebarMenuActive(menu) {
        const path = this.getMenuItemHref(menu).split("?")[0];
        return this.state.ahoLocation === path || this.state.ahoLocation.startsWith(`${path}/`);
    },
});

/** @odoo-module **/
import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class SearchShortcut extends Component {
    static template = "oh_quick_search.SearchShortcut";

    setup() {
        this.commandService = useService("command");
    }

    onClickSearch() {
        this.commandService.openMainPalette();
    }
}

registry.category("systray").add("oh_quick_search.SearchShortcut", {Component: SearchShortcut,}, {sequence: 16});
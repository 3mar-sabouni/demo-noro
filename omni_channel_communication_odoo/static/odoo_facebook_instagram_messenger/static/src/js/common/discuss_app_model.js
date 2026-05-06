/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DiscussApp } from "@mail/core/public_web/discuss_app_model";
//import { OutOfFocusService } from "@mail/core/common/out_of_focus_service";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { DiscussAppCategory } from "@mail/core/public_web/discuss_app_category_model";
import { compareDatetime } from "@mail/utils/common/misc";

const PREVIEW_MSG_MAX_SIZE = 350; // optimal for native English speakers


//patch(OutOfFocusService.prototype, {
//   async notify(message, channel) {
//        const modelsHandleByPush = ["mail.thread", "discuss.channel"];
//        if (
//            modelsHandleByPush.includes(message.model) &&
//            (await this.hasServiceWorkInstalledAndPushSubscriptionActive())
//        ) {
//            return;
//        }
//        const author = message.author;
//        let notificationTitle;
//        if (!author) {
//            notificationTitle = _t("New message");
//        } else {
//            if (channel.channel_type === "channel") {
//                notificationTitle = _t("%(author name)s from %(channel name)s", {
//                    "author name": author.name,
//                    "channel name": channel.displayName,
//                });
//            } else {
//                notificationTitle = author.name;
//            }
//        }
//        var message = message.body || '';
//        const notificationContent = htmlToTextContentInline(message).substring(
//            0,
//            PREVIEW_MSG_MAX_SIZE
//        );
//        this.sendNotification({
//            message: notificationContent,
//            title: notificationTitle,
//            type: "info",
//        });
//    }
//});

patch(DiscussApp, {
    new(data) {
        const res = super.new(data);
        res.FbChannels = {
            extraClass: "o-mail-DiscussSidebarCategory-tus-FbChannels",
            id: "FbChannels",
            name: _t("Facebook Messenger Messages"),
            isOpen: false,
            canView: false,
            canAdd: true,
            addTitle: _t("Start a Messenger Conversion"),
            serverStateKey: "is_discuss_sidebar_category_facebook_open",
            addHotkey: "f",
        };
        res.InstaChannels = {
            extraClass: "o-mail-DiscussSidebarCategory-tus-InstaChannels",
            id: "InstaChannels",
            name: _t("Instagram Messenger Messages"),
            isOpen: false,
            canView: false,
            canAdd: true,
            addTitle: _t("Start a Instagram Messenger Conversion"),
            serverStateKey: "is_discuss_sidebar_category_instagram_open",
            addHotkey: "i",
        };
        return res;
    },

});

patch(DiscussApp.prototype, {
     setup(env) {
        super.setup(env);
        this.FbChannels = Record.one("DiscussAppCategory");
        this.InstaChannels = Record.one("DiscussAppCategory");
    },
});

patch(DiscussAppCategory.prototype, {
    sortThreads(t1, t2) {
        if (this.id === "FbChannels" || this.id === 'InstaChannels') {
            return compareDatetime(t2.lastInterestDt, t1.lastInterestDt) || t2.id - t1.id;
        }
        return super.sortThreads(t1, t2);
    },
});

//MOBILE VIEW WHATSAPP IN DISCUSS
patch(MessagingMenu.prototype, {
    /**
     * @override
     */
    get tabs() {
        const items = super.tabs;
        items.push({
            icon: "fa fa-facebook",
            id: "FbChannels",
            label: _t("Messenger"),
        });
        items.push({
            icon: "fa fa-instagram",
            id: "InstaChannels",
            label: _t("Instagram"),
        });
        return items;
    },

});

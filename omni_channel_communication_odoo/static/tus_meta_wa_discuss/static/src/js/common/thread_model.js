///* @odoo-module */

import { url } from "@web/core/utils/urls";
import { patch } from "@web/core/utils/patch";
import { AND, Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { assignDefined, assignIn } from "@mail/utils/common/misc";


patch(Thread.prototype, {
    update(data) {
        const { id, name, attachments, description, ...serverData } = data;
        assignDefined(this, { id, name, description });
        if (attachments) {
            this.attachments = attachments;
        }
        if (serverData) {
            assignDefined(this, serverData, [
                "uuid",
                "authorizedGroupFullName",
                "avatarCacheKey",
                "description",
                "hasWriteAccess",
                "is_pinned",
                "isLoaded",
                "isLoadingAttachments",
                "mainAttachment",
                "message_unread_counter",
                "message_needaction_counter",
                "name",
                "seen_message_id",
                "state",
                "type",
                "status",
                "group_based_subscription",
                "last_interest_dt",
                "custom_notifications",
                "mute_until_dt",
                "is_editable",
                "defaultDisplayMode",
            ]);
            assignIn(this, data, [
                "custom_channel_name",
                "memberCount",
                "channelMembers",
                "invitedMembers",
            ]);
            if ("channelMembers" in data) {
                if  (this.channel_type === "whatsapp" || this.channel_type === "FbChannels" || this.channel_type === "InstaChannels" || this.channel_type === "WpChannels") {
//                    CODE FOR GETTING FIRST PARTNER
                    let channelMember = this.channelMembers && this.channelMembers.length && this.channelMembers.find((member) => !member.persona?.isInternalUser);
                    if (channelMember) {
                        if (channelMember.persona.notEq(this._raw.user) || channelMember.persona?.eq(this._raw.user)){
                            this.chatPartner = channelMember.persona;
                        }
                    }
                }
           }
           if ("seen_partners_info" in serverData) {
                this._store.ChannelMember.insert(
                    serverData.seen_partners_info.map(
                        ({ id, fetched_message_id, partner_id, guest_id, seen_message_id }) => ({
                            id,
                            persona: {
                                id: partner_id ?? guest_id,
                                type: partner_id ? "partner" : "guest",
                            },
                            lastFetchedMessage: fetched_message_id
                                ? { id: fetched_message_id }
                                : undefined,
                            lastSeenMessage: seen_message_id ? { id: seen_message_id } : undefined,
                        })
                    )
                );
            }
        if (this.type === "channel") {
            this._store.discuss.channels.threads.add(this);
        } else if (this.type === "chat" || this.type === "group") {
            this._store.discuss.chats.threads.add(this);
        }
        if (!this.type && !["mail.box", "discuss.channel"].includes(this.model)) {
            this.type = "chatter";
        }
        if (this.type === "WpChannels") {
            this._store.discuss.WpChannels.threads.add(this);
        }
        if (this.type === "FbChannels") {
            this._store.discuss.FbChannels.threads.add(this);
        }
        if (this.type === "InstaChannels") {
            this._store.discuss.InstaChannels.threads.add(this);
        }
     }

      return super.update(data);
     },

     get avatarUrl() {
        if ((this.channel_type === "WpChannels" ||  this.channel_type === "FbChannels" ||  this.channel_type === "InstaChannels") && this.chatPartner) {
            return this.chatPartner.avatarUrl;
        }
        return super.avatarUrl;
    },
    _computeDiscussAppCategory() {
        return this.channel_type === "WpChannels"
            ? this.store.discuss.WpChannels
            : super._computeDiscussAppCategory();
    },
    get canUnpin() {
        if (this.channel_type === "WpChannels" ||  this.channel_type === "FbChannels" ||  this.channel_type === "InstaChannels") {
            return this.importantCounter === 0;
        }
        return super.canUnpin;
    },
});


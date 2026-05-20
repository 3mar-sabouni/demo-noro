# -*- coding: utf-8 -*-

import json
import time
import re

from markupsafe import Markup
from odoo import models
from google import genai


class Channel(models.Model):
    _inherit = 'discuss.channel'

    # =====================================================
    # RATE LIMIT
    # =====================================================
    _last_request = {}

    def _rate_limit(self, uid, cooldown=5):
        now = time.time()
        last = self._last_request.get(uid)

        if last and (now - last) < cooldown:
            return False

        self._last_request[uid] = now
        return True

    # =====================================================
    # GEMINI CALL
    # =====================================================
    def _call_gemini(self, client, model, prompt, retries=3, wait=30):

        for i in range(retries):
            try:
                return client.models.generate_content(
                    model=model,
                    contents=prompt
                )
            except Exception as ex:
                msg = str(ex).lower()

                if "429" in msg or "quota" in msg:
                    if i < retries - 1:
                        time.sleep(wait)
                        continue

                raise ex

    # =====================================================
    # SAFE JSON
    # =====================================================
    def _json(self, text):
        try:
            text = re.sub(r"```json|```", "", text.strip())
            return json.loads(text)
        except Exception:
            return {}

    # =====================================================
    # POST MESSAGE
    # =====================================================
    def _post(self, user, msg):
        self.with_user(user).message_post(
            body=Markup(msg),
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

    # =====================================================
    # INTENT ROUTER (CORE BRAIN)
    # =====================================================
    def _route_intent(self, client, model, message):

        prompt = f"""
You are an Odoo 18 AI router.

Return ONLY JSON:

{{
  "type": "count | list | report | explain | none",
  "model": "res.partner | sale.order | account.move | product.product | stock.quant | crm.lead | purchase.order | hr.employee | project.project | helpdesk.ticket | none"
}}

RULES:
- customers → res.partner
- sales orders → sale.order
- invoices → account.move
- products → product.product
- stock → stock.quant
- crm → crm.lead
- purchase → purchase.order
- employees → hr.employee
- projects → project.project
- tickets → helpdesk.ticket

QUESTION:
{message.body}
"""

        res = self._call_gemini(client, model, prompt)
        return self._json(res.text)

    # =====================================================
    # ODOO ORM ENGINE (REAL DATA ONLY)
    # =====================================================
    def _execute_odoo(self, intent):

        model = intent.get("model")
        action = intent.get("type")

        if model == "none":
            return None

        env = self.env

        # -------------------------
        # CONTACTS
        # -------------------------
        if model == "res.partner":
            if action == "count":
                return {
                    "count": env["res.partner"].search_count([])
                }

            if action == "list":
                recs = env["res.partner"].search([], limit=10)
                return {
                    "records": recs.read(["name", "email", "create_date"])
                }

        # -------------------------
        # SALES
        # -------------------------
        if model == "sale.order":
            if action == "count":
                return {
                    "count": env["sale.order"].search_count([])
                }

            if action == "list":
                recs = env["sale.order"].search([], limit=10)
                return {
                    "records": recs.read(["name", "amount_total", "state"])
                }

        # -------------------------
        # INVOICES
        # -------------------------
        if model == "account.move":
            if action == "count":
                return {
                    "count": env["account.move"].search_count([
                        ("move_type", "=", "out_invoice")
                    ])
                }

        # -------------------------
        # PRODUCTS
        # -------------------------
        if model == "product.product":
            if action == "count":
                return {
                    "count": env["product.product"].search_count([])
                }

        # -------------------------
        # STOCK
        # -------------------------
        if model == "stock.quant":
            if action == "count":
                return {
                    "count": env["stock.quant"].search_count([])
                }

        # -------------------------
        # CRM
        # -------------------------
        if model == "crm.lead":
            if action == "count":
                return {
                    "count": env["crm.lead"].search_count([])
                }

        # -------------------------
        # PURCHASE
        # -------------------------
        if model == "purchase.order":
            if action == "count":
                return {
                    "count": env["purchase.order"].search_count([])
                }

        # -------------------------
        # EMPLOYEES
        # -------------------------
        if model == "hr.employee":
            if action == "count":
                return {
                    "count": env["hr.employee"].search_count([])
                }

        # -------------------------
        # PROJECTS
        # -------------------------
        if model == "project.project":
            if action == "count":
                return {
                    "count": env["project.project"].search_count([])
                }

        # -------------------------
        # HELP DESK
        # -------------------------
        if model == "helpdesk.ticket":
            if "helpdesk.ticket" in env:
                if action == "count":
                    return {
                        "count": env["helpdesk.ticket"].search_count([])
                    }

        return None

    # =====================================================
    # FINAL RESPONSE GENERATOR
    # =====================================================
    def _final_answer(self, client, model, message, data):

        prompt = f"""
You are an Odoo 18 AI assistant.

RULES:
- Use ONLY provided Odoo data
- NEVER guess numbers
- NEVER mention other systems
- Be precise and short

QUESTION:
{message.body}

ODOO DATA:
{data}

Return ONLY JSON:
{{
  "html_code": ""
}}
"""

        res = self._call_gemini(client, model, prompt)
        data = self._json(res.text)

        html = data.get("html_code", "<p>No data</p>")

        return html

    # =====================================================
    # MAIN HOOK
    # =====================================================
    def _notify_thread(self, message, msg_vals=None, **kwargs):

        res = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

        try:
            partner = self.env.ref(
                "googel_gemini_odoo_connector.partner_gemini"
            )

            user = self.env.ref(
                "googel_gemini_odoo_connector.user_gemini"
            )

            author_id = msg_vals.get("author_id")

            if author_id == partner.id:
                return res

            channel = self.env["discuss.channel"].browse(
                msg_vals.get("res_id")
            )

            if (
                channel.channel_type != "chat"
                or partner.id not in channel.channel_partner_ids.ids
            ):
                return res

            if not self._rate_limit(author_id):
                self._post(user, "Please wait a few seconds...")
                return res

            config = self.env["ir.config_parameter"].sudo()

            model = config.get_param(
                "googel_gemini_odoo_connector.gemini_model"
            )

            api_key = config.get_param(
                "googel_gemini_odoo_connector.gemini_api_key"
            )

            if not model or not api_key:
                self._post(user, "Gemini not configured.")
                return res

            client = genai.Client(api_key=api_key)

            # STEP 1: INTENT
            intent = self._route_intent(client, model, message)

            # STEP 2: ODOO DATA
            odoo_data = self._execute_odoo(intent)

            # STEP 3: FINAL ANSWER
            html = self._final_answer(
                client,
                model,
                message,
                odoo_data
            )

            self._post(user, html)

        except Exception as ex:
            msg = str(ex)
            print("AI ERROR:", msg)

            if "429" in msg or "quota" in msg:
                self._post(user, "Gemini quota exceeded. Try later.")

        return res
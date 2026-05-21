from odoo import models
from google import genai 
from google.genai import types
import json
from markupsafe import Markup
import threading

class Channel(models.Model):
    _inherit = 'discuss.channel'

    def _get_question_related_to_odoo(self, client, gemini_model, message_body):
        response_format = {
            "related_to_odoo": "yes/no",
            "used_model_for_postgresql_query": "List of models"
        }
        response = client.models.generate_content(
            model=gemini_model,
            contents=f'Give me response in this format {json.dumps(response_format)} for question "{message_body}"',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)

    def _generate_query(self, client, gemini_model, message_body, model_fields_mapping):
        format_query = '{"query" : "postgresql_odoo_query","fields" : {"model_1" : "used_field_list_for_query_model_1","model_2": "used_field_list_for_query_model_2"}}'
        instruction = [
            "if field name is name use operator ilike",
            "if field translate is true search like this : pt.name::text ilike '%abc%'",
            "if field translate is true and field name is name search like this : name::text ilike '%xyz%'",
            "Must be give alias for field in generated query",
            "for field type char and translate is true search like this where name::text ilike '%abc%'",
            "Not take that type of word in response like [Based on the data, using the data,Based on the provided data]"
        ]
        response = client.models.generate_content(
            model=gemini_model,
            contents=f'My database structure is {model_fields_mapping}. instruction: {instruction}. Give me response in this format {format_query} for question "{message_body}"',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(response.text)

    def _generate_python_code_snippet(self, client, gemini_model, message_body, used_model_for_postgresql_query):
        model_fields_mapping = dict()
        for model_name in used_model_for_postgresql_query:
            model_name = model_name.replace('_', '.')
            model_id = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
            if not model_id:
                continue
            field_list = [{
                "name": field.name, 
                "field_description": field.field_description,
                "type": field.ttype, 
                "translate": field.translate
            } for field in model_id.field_id]
            model_fields_mapping[model_name] = field_list
            
        if not model_fields_mapping:
            return False
            
        format_query = "{'python_code_snippet': [python_code_1,python_code_2,python_code_3,python_code_4,python_code_5]}"
        prompt_content = f'''Key Principle:
            self Usage: You can freely use self within the code snippets, assuming the context is an Odoo model method.
            final_result Dictionary: A dictionary named final_result is always available in the environment. Store your final output in final_result['response']. Never overwrite or reassign the final_result dictionary itself. Only modify the final_result['response'] value..
            Snippet Only: Do not create classes or functions. Generate concise, directly runnable code snippets.
            ORM Methods: Use Odoo ORM methods exclusively. Do not use direct PostgreSQL queries due to access restrictions.
            Read-Only Operations: You have no access to create, write, or unlink methods.
            No sudo(): Do not use sudo() anywhere in the code.
            Context and User: Always use the following context and user when interacting with the ORM: .with_context(from_gemini=True).with_user(self.env.user). For example: self.env['sale.order'].with_context(from_gemini=True).with_user(self.env.user).search([])
            Generate 5 distinct script for odoov18.
            database structure: {model_fields_mapping}.             
            Give me response in this format {format_query} for question "{message_body}"'''

        response = client.models.generate_content(
            model=gemini_model,
            contents=prompt_content,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        res = json.loads(response.text)
        final_result = {'response': ''}
        result_dict = {}
        for count, code in enumerate(res.get('python_code_snippet', [])):
            try:
                exec(code, {'self': self, 'final_result': final_result})
                result_dict[f"response_{count}"] = final_result.get('response')
            except Exception as ex:
                result_dict[f"error_{count}"] = ex
        return result_dict

    def _clean_and_post_html(self, response_text, user_gemini):
        try:
            res = json.loads(response_text)
            final_response = res.get('html_code', '')
        except Exception:
            final_response = response_text

        replace_list = [('<html>', ''), ('</html>', ''), ('html', ''), ("```", '')]
        for i, j in replace_list:
            final_response = final_response.replace(i, j)
        final_response = final_response.strip()

        self.with_user(user_gemini).message_post(
            body=Markup(final_response),
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

    def _response_gemini(self, client, gemini_model, message_body, user_gemini):
        response = client.models.generate_content(
            model=gemini_model,
            contents=message_body,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        self._clean_and_post_html(response.text, user_gemini)

    def _response_gemini_html(self, client, gemini_model, message_body, user_gemini):
        response = client.models.generate_content(
            model=gemini_model,
            contents=message_body,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        self._clean_and_post_html(response.text, user_gemini)

    def _process_gemini_async(self, channel_id, message_body, gemini_model, gemini_api_key, user_gemini_id):
        """ Runs inside a separate thread with a unique standalone database cursor """
        new_env = self.env(cr=self.pool.cursor())
        try:
            client = genai.Client(api_key=gemini_api_key)
            detached_channel = new_env['discuss.channel'].browse(channel_id)
            
            res = detached_channel._get_question_related_to_odoo(client, gemini_model, message_body)
            
            body = f'generated a text answer for question : {message_body}\nAlso give a response in html code.\nresponse format : {{"html_code" : html_code_response}}'
            
            if res.get('related_to_odoo') == 'yes':
                used_models = res.get('used_model_for_postgresql_query')
                if isinstance(used_models, str):
                    try:
                        used_models = eval(used_models)
                    except Exception:
                        pass
                
                odoo_response = detached_channel._generate_python_code_snippet(client, gemini_model, message_body, used_models)
                if odoo_response:
                    body += f'\nthis a different response from odoo run script : {odoo_response}, generate a answer from this response. This is a final data you don\'t need to filter out data. Don\'t show a response data in answer.'
                    detached_channel._response_gemini_html(client, gemini_model, body, user_gemini_id)
                else:
                    detached_channel._response_gemini(client, gemini_model, body, user_gemini_id)
            else:
                detached_channel._response_gemini(client, gemini_model, body, user_gemini_id)
                
            new_env.cr.commit()
            
        except Exception as ex:
            error_msg = str(ex)
            # Rebranded User Notifications
            friendly_message = f"⚠️ <b>Noro System Automation Notice:</b><br/>"
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                friendly_message += "The engine is currently processing high data volumes. Please allow a minute before resending your command."
            else:
                friendly_message += f"Engine tracking trace: {error_msg}"
                
            try:
                detached_channel = new_env['discuss.channel'].browse(channel_id)
                detached_channel.with_user(user_gemini_id).message_post(
                    body=Markup(friendly_message),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
                new_env.cr.commit()
            except Exception:
                new_env.cr.rollback()
        finally:
            new_env.cr.close()

    def _notify_thread(self, message, msg_vals=None, **kwargs):
        rdata = super(Channel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        if not msg_vals:
            return rdata

        partner_gemini = self.env.ref("googel_gemini_odoo_connector.partner_gemini", raise_if_not_found=False)
        user_gemini = self.env.ref("googel_gemini_odoo_connector.user_gemini", raise_if_not_found=False)
        
        if not partner_gemini or not user_gemini:
            return rdata

        author_id = msg_vals.get('author_id')
        discuss_channel_id = self.env['discuss.channel'].browse(msg_vals.get('res_id', 0))
        partner_ids = discuss_channel_id.channel_partner_ids

        if (author_id != partner_gemini.id) and (msg_vals.get('model', '') == 'discuss.channel' and partner_gemini.id in partner_ids.ids):
            if discuss_channel_id.channel_type != 'chat':
                return rdata
                
            gemini_model = self.env['ir.config_parameter'].sudo().get_param('googel_gemini_odoo_connector.gemini_model')
            gemini_api_key = self.env['ir.config_parameter'].sudo().get_param('googel_gemini_odoo_connector.gemini_api_key')
            
            if not gemini_model or not gemini_api_key:
                self.with_user(user_gemini.id).message_post(
                    body=Markup("Noro System connection parameters are unconfigured. Please check system parameters."),
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
                return rdata

            # Thread execution block for instant handling
            threading.Thread(
                target=self._process_gemini_async,
                args=(discuss_channel_id.id, message.body, gemini_model, gemini_api_key, user_gemini.id),
                daemon=True
            ).start()

        return rdata
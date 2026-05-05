from odoo import models, fields, api
import json

class PaymentTransactionLog(models.Model):
    _name = 'payment.transaction.log'
    _description = 'Payment Transaction Log History'
    _order = 'create_date desc'

    transaction_id = fields.Many2one(
        'payment.transaction',
        string='Payment Transaction',
        required=True,
        ondelete='cascade'
    )
    
    status = fields.Char(string='Status')
    raw_response = fields.Text(string='Raw Response')
    html_details = fields.Html(string='Transaction Details', compute='_compute_html_details', sanitize=False)
    
    def action_view_transaction_log_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transaction Log Details',
            'view_mode': 'form',
            'res_model': 'payment.transaction.log',
            'res_id': self.id,
            'target': 'new',
        }

    @api.depends('raw_response')
    def _compute_html_details(self):
        for record in self:
            if not record.raw_response:
                record.html_details = False
                continue
            
            try:
                # Handle both bytes and string responses
                if isinstance(record.raw_response, bytes):
                    response_str = record.raw_response.decode('utf-8')
                else:
                    response_str = record.raw_response
                
                # First try to parse as proper JSON
                try:
                    response_data = json.loads(response_str)
                except json.JSONDecodeError:
                    # If that fails, try to handle malformed JSON (single quotes)
                    try:
                        # Replace single quotes with double quotes carefully
                        fixed_json = response_str.replace("'", '"')
                        response_data = json.loads(fixed_json)
                    except json.JSONDecodeError:
                        # If still failing, try eval (with safety check)
                        if any(word in response_str.lower() for word in ['system', 'error', 'failed']):
                            # For error messages, just display as-is
                            record.html_details = f"""
                                <div class="alert alert-danger">
                                    <strong>Error Response:</strong><br/>
                                    <pre>{response_str}</pre>
                                </div>
                            """
                            return
                        else:
                            # Try eval as last resort (potentially unsafe)
                            response_data = eval(response_str)
                
                # Flatten nested dictionaries
                def flatten_dict(d, parent_key='', separator='.'):
                    items = []
                    for k, v in d.items():
                        new_key = f"{parent_key}{separator}{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten_dict(v, new_key, separator).items())
                        else:
                            items.append((new_key, v))
                    return dict(items)
                
                flat_data = flatten_dict(response_data)
                
                # Generate HTML table
                html = """
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Field</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for key, value in sorted(flat_data.items()):
                    html += f"""
                        <tr>
                            <td><strong>{key}</strong></td>
                            <td>{value}</td>
                        </tr>
                    """
                
                html += """
                        </tbody>
                    </table>
                """
                
                record.html_details = html
                
            except Exception as e:
                record.html_details = f"""
                    <div class="alert alert-warning">
                        <strong>Could not parse response:</strong> {str(e)}<br/>
                        <pre>{record.raw_response}</pre>
                    </div>
                """
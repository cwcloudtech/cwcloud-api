import os
import requests

from utils import common
from adapters.emails.EmailAdapter import EmailAdapter
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.logger import log_msg
from utils.mail import EMAIL_EXPEDITOR
from utils.observability.cid import get_current_cid

_brevo_api_key = os.getenv('BREVO_API_KEY')
_brevo_api_url = os.getenv('BREVO_API_URL', 'https://api.brevo.com/v3')

def _build_attachment(payload):
    if not any(common.is_not_empty_key(payload, k) for k in ['content', 'b64']) or common.is_empty_key(payload, 'file_name'):
        return None

    return {
        'content': payload['content'] if common.is_not_empty_key(payload, "content") else payload['b64'],
        'name': payload['file_name']
    }

class BrevoAdapter(EmailAdapter):
    def is_disabled(self):
        return common.is_disabled(_brevo_api_key)

    def send(self, email):
        email = self.dedupe_recipients(email)

        sender = {'email': email['from'] if common.is_not_empty_key(email, "from") else EMAIL_EXPEDITOR}
        if common.is_not_empty_key(email, "from_name"):
            sender['name'] = email['from_name']

        to_emails = email['to'] if common.is_not_empty_key(email, "to") else [EMAIL_EXPEDITOR]

        payload = {
            'sender': sender,
            'to': [{'email': to_email} for to_email in to_emails],
            'subject': email['subject'],
            'htmlContent': email['content']
        }

        if common.is_not_empty_key(email, "cc"):
            payload['cc'] = [{'email': cc_email} for cc_email in email['cc']]

        if common.is_not_empty_key(email, "bcc"):
            payload['bcc'] = [{'email': bcc_email} for bcc_email in email['bcc']]

        if common.is_not_empty_key(email, "replyto"):
            payload['replyTo'] = {'email': email['replyto']}

        attachment_payloads = []
        if common.is_not_empty_key(email, "attachment"):
            attachment_payloads.append(email['attachment'])
        if common.is_not_empty_key(email, "attachments"):
            attachment_payloads.extend(email['attachments'])

        attachments = [a for a in (_build_attachment(p) for p in attachment_payloads) if a is not None]
        if attachments:
            payload['attachment'] = attachments

        message = ""
        try:
            if not common.is_disabled(_brevo_api_key):
                response = requests.post(
                    "{}/smtp/email".format(_brevo_api_url),
                    headers = {
                        'api-key': _brevo_api_key,
                        'accept': 'application/json',
                        'content-type': 'application/json'
                    },
                    json = payload,
                    timeout = HTTP_REQUEST_TIMEOUT
                )
                message = "code = {}, body = {}".format(response.status_code, response.text)
                if response.status_code >= 300:
                    raise RuntimeError(message)
        except Exception as ex:
            message = "{}".format(ex)
            log_msg("ERROR", "[BrevoAdapter][send] unexpected error : type = {}, file = {}, lno = {}, msg = {}".format(type(ex).__name__, __file__, ex.__traceback__.tb_lineno, ex))
            return {
                'status': 'ko',
                'adapter': 'brevo',
                'i18n_code': 'third_part_email_error',
                'http_code': 500,
                'error': message,
                'cid': get_current_cid()
            }
        return {
            'status': 'ok',
            'adapter': 'brevo',
            'message': message
        }

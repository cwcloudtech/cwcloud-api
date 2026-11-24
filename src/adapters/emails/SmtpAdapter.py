import os
import base64
import smtplib

from email.message import EmailMessage
from email.utils import formataddr

from utils import common
from adapters.emails.EmailAdapter import EmailAdapter
from utils.http import HTTP_REQUEST_TIMEOUT
from utils.logger import log_msg
from utils.mail import EMAIL_EXPEDITOR
from utils.observability.cid import get_current_cid

_smtp_host = os.getenv('SMTP_HOST')
_smtp_port = int(os.getenv('SMTP_PORT', '587'))
_smtp_username = os.getenv('SMTP_USERNAME')
_smtp_password = os.getenv('SMTP_PASSWORD')
_smtp_security = os.getenv('SMTP_SECURITY', 'starttls').lower() # starttls, ssl or none

def _add_attachment(message, payload):
    if not any(common.is_not_empty_key(payload, k) for k in ['content', 'b64']) or any(common.is_empty_key(payload, k) for k in ['mime_type', 'file_name']):
        return

    content = payload['content'] if common.is_not_empty_key(payload, "content") else payload['b64']
    maintype, _, subtype = payload['mime_type'].partition('/')
    message.add_attachment(
        base64.b64decode(content),
        maintype = maintype,
        subtype = subtype or 'octet-stream',
        filename = payload['file_name']
    )

class SmtpAdapter(EmailAdapter):
    def is_disabled(self):
        return common.is_disabled(_smtp_host)

    def send(self, email):
        email = self.dedupe_recipients(email)

        from_email = email['from'] if common.is_not_empty_key(email, "from") else EMAIL_EXPEDITOR
        to_emails = email['to'] if common.is_not_empty_key(email, "to") else [EMAIL_EXPEDITOR]
        cc_emails = email['cc'] if common.is_not_empty_key(email, "cc") else []
        bcc_emails = email['bcc'] if common.is_not_empty_key(email, "bcc") else []

        message = EmailMessage()
        message['Subject'] = email['subject']
        message['From'] = formataddr((email['from_name'], from_email)) if common.is_not_empty_key(email, "from_name") else from_email
        message['To'] = ", ".join(to_emails)

        if cc_emails:
            message['Cc'] = ", ".join(cc_emails)

        if common.is_not_empty_key(email, "replyto"):
            message['Reply-To'] = email['replyto']

        message.set_content(email['content'], subtype = 'html')

        attachment_payloads = []
        if common.is_not_empty_key(email, "attachment"):
            attachment_payloads.append(email['attachment'])
        if common.is_not_empty_key(email, "attachments"):
            attachment_payloads.extend(email['attachments'])

        result = ""
        try:
            for attachment_payload in attachment_payloads:
                _add_attachment(message, attachment_payload)

            if not common.is_disabled(_smtp_host):
                smtp_class = smtplib.SMTP_SSL if _smtp_security == 'ssl' else smtplib.SMTP
                with smtp_class(_smtp_host, _smtp_port, timeout = HTTP_REQUEST_TIMEOUT) as server:
                    if _smtp_security == 'starttls':
                        server.starttls()
                    if common.is_enabled(_smtp_username) and common.is_enabled(_smtp_password):
                        server.login(_smtp_username, _smtp_password)
                    refused = server.send_message(message, from_addr = from_email, to_addrs = to_emails + cc_emails + bcc_emails)
                    result = "refused = {}".format(refused)
        except Exception as ex:
            result = "{}".format(ex)
            log_msg("ERROR", "[SmtpAdapter][send] unexpected error : type = {}, file = {}, lno = {}, msg = {}".format(type(ex).__name__, __file__, ex.__traceback__.tb_lineno, ex))
            return {
                'status': 'ko',
                'adapter': 'smtp',
                'i18n_code': 'third_part_email_error',
                'http_code': 500,
                'error': result,
                'cid': get_current_cid()
            }
        return {
            'status': 'ok',
            'adapter': 'smtp',
            'message': result
        }

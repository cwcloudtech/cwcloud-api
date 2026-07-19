import os
import sendgrid

from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition, ContentId, ReplyTo, Bcc, Cc

from utils import common
from adapters.emails.EmailAdapter import EmailAdapter
from utils.logger import log_msg
from utils.mail import EMAIL_EXPEDITOR
from utils.observability.cid import get_current_cid

_sendgrid_api_key = os.getenv('SENDGRID_API_KEY')

def _build_attachment(payload):
    if not any(common.is_not_empty_key(payload, k) for k in ['content', 'b64']) or any(common.is_empty_key(payload, k) for k in ['mime_type', 'file_name']):
        return None

    attachment = Attachment()
    if common.is_not_empty_key(payload, "content"):
        attachment.file_content = FileContent(payload['content'])
    elif common.is_not_empty_key(payload, "b64"):
        attachment.file_content = FileContent(payload['b64'])

    attachment.file_type = FileType(payload['mime_type'])
    attachment.file_name = FileName(payload['file_name'])
    attachment.disposition = Disposition('attachment')
    attachment.content_id = ContentId(payload['file_name'])
    return attachment

class SendgridAdapter(EmailAdapter):
    def is_disabled(self):
        return common.is_disabled(_sendgrid_api_key)

    def send(self, email):
        email = self.dedupe_recipients(email)

        from_email = Email(EMAIL_EXPEDITOR)
        if common.is_not_empty_key(email, "from"):
            from_email = Email(email['from'])

        to_emails = email['to'] if common.is_not_empty_key(email, "to") else [EMAIL_EXPEDITOR]

        content = Content("text/html", email['content'])
        mail = Mail(from_email, [To(to_email) for to_email in to_emails], email['subject'], content)

        if common.is_not_empty_key(email, "cc"):
            for cc_email in email['cc']:
                mail.add_cc(Cc(cc_email))

        if common.is_not_empty_key(email, "bcc"):
            for bcc_email in email['bcc']:
                mail.add_bcc(Bcc(bcc_email))

        if common.is_not_empty_key(email, "replyto"):
            mail.reply_to = ReplyTo(email['replyto'])

        if common.is_not_empty_key(email, "from_name"):
            mail.from_email.name = email['from_name']

        attachment_payloads = []
        if common.is_not_empty_key(email, "attachment"):
            attachment_payloads.append(email['attachment'])
        if common.is_not_empty_key(email, "attachments"):
            attachment_payloads.extend(email['attachments'])

        for attachment_payload in attachment_payloads:
            attachment = _build_attachment(attachment_payload)
            if attachment is not None:
                mail.add_attachment(attachment)

        try:
            if not common.is_disabled(_sendgrid_api_key):
                sg = sendgrid.SendGridAPIClient(api_key = _sendgrid_api_key)
                sg_response = sg.client.mail.send.post(request_body = mail.get())
                message = "code = {}, body = {}".format(sg_response.status_code, sg_response.body)
        except Exception as ex:
            message = "{}".format(ex)
            body = getattr(ex, 'body', None)
            log_msg("ERROR", "[SendgridAdapter][send] unexpected error : type = {}, file = {}, lno = {}, msg = {}, body = {}".format(type(ex).__name__, __file__, ex.__traceback__.tb_lineno, ex, body))
            return {
                'status': 'ko',
                'adapter': 'sendgrid',
                'i18n_code': 'third_part_email_error',
                'http_code': 500,
                'error': message,
                'cid': get_current_cid()
            }
        return {
            'status': 'ok',
            'adapter': 'sendgrid',
            'message': message
        }

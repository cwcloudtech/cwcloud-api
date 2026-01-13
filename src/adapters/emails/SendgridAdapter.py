import os
import sendgrid

from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition, ContentId, Attachment, FileContent, FileName, FileType, Disposition, ContentId, ReplyTo, Bcc, Cc

from utils import common
from adapters.emails.EmailAdapter import EmailAdapter
from utils.logger import log_msg
from utils.mail import EMAIL_EXPEDITOR
from utils.observability.cid import get_current_cid

_sendgrid_api_key = os.getenv('SENDGRID_API_KEY')

class SendgridAdapter(EmailAdapter):
    def is_disabled(self):
        return common.is_disabled(_sendgrid_api_key)

    def send(self, email):
        from_email = Email(EMAIL_EXPEDITOR)
        if common.is_not_empty_key(email, "from"):
            from_email = Email(email['from'])

        to_email = Email(EMAIL_EXPEDITOR)
        if common.is_not_empty_key(email, "to"):
            to_email = To(email['to'])

        content = Content("text/html", email['content'])
        mail = Mail(from_email, to_email, email['subject'], content)

        if common.is_not_empty_key(email, "cc"):
            mail.add_cc(Cc(email['cc']))

        if common.is_not_empty_key(email, "bcc"):
            mail.add_bcc(Bcc(email['bcc']))

        if common.is_not_empty_key(email, "replyto"):
            mail.reply_to = ReplyTo(email['replyto'])

        if common.is_not_empty_key(email, "from_name"):
            mail.from_email.name = email['from_name']

        if common.is_not_empty_key(email, "attachment") and any(common.is_not_empty_key(email['attachment'], k) for k in ['content', 'b64']) and not any (common.is_empty_key(email['attachment'], k) for k in ['mime_type', 'file_name']):
            attachment = Attachment()
            if common.is_not_empty_key(email['attachment'], "content"):
                attachment.file_content = FileContent(email['attachment']['content'])
            elif common.is_not_empty_key(email['attachment'], "b64"):
                attachment.file_content = FileContent(email['attachment']['b64'])

            attachment.file_type = FileType(email['attachment']['mime_type'])
            attachment.file_name = FileName(email['attachment']['file_name'])
            attachment.disposition = Disposition('attachment')
            attachment.content_id = ContentId(email['attachment']['file_name'])
            mail.attachment = attachment

        try:
            if not common.is_disabled(_sendgrid_api_key):
                sg = sendgrid.SendGridAPIClient(api_key = _sendgrid_api_key)
                sg_response = sg.client.mail.send.post(request_body = mail.get())
                message = "code = {}, body = {}".format(sg_response.status_code, sg_response.body)
        except Exception as ex:
            message = "{}".format(ex)
            log_msg("ERROR", "[SendgridAdapter][send] unexpected error : type = {}, file = {}, lno = {}, msg = {}".format(type(ex).__name__, __file__, ex.__traceback__.tb_lineno, ex))
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

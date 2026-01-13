from adapters.emails.EmailAdapter import EmailAdapter
from utils.common import is_not_empty_key
from utils.logger import log_msg
from utils.mail import EMAIL_EXPEDITOR

class LogAdapter(EmailAdapter):
    def is_disabled(self):
        is_disabled = False
        log_msg("INFO", "[Emails][LogAdapter][is_disabled] is_disabled = {}".format(is_disabled))
        return is_disabled

    def send(self, email):
        from_email = EMAIL_EXPEDITOR
        if is_not_empty_key(email, "from"):
            from_email = email['from']

        to_email = EMAIL_EXPEDITOR
        if is_not_empty_key(email, "to"):
            to_email = email['to']

        log_msg("INFO", "[Emails][LogAdapter][send] from = {}, to = {}, subject = {}, message = {}".format(from_email, to_email, email['subject'], email['content']))
        return {
            'status': 'ok',
            'adapter': 'log',
            'message': ''
        }

import os

from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from adapters.AdapterConfig import get_adapter, get_default_adapter

from utils.api_url import get_api_url
from utils.common import is_false, is_not_empty, is_not_empty_key, AUTOESCAPE_EXTENSIONS
from utils.spam import is_message_acceptable
from utils.logger import log_msg
from utils.observability.cid import get_current_cid

EMAIL_EXPEDITOR = os.getenv('EMAIL_EXPEDITOR', 'cloud@changeit.com')
EMAIL_ACCOUNTING = os.getenv('EMAIL_ACCOUNTING') if is_not_empty(os.getenv('EMAIL_ACCOUNTING')) else EMAIL_EXPEDITOR
EMAIL_ADAPTER = get_adapter("emails")
DEFAULT_EMAIL_ADAPTER = get_default_adapter("emails")

_CACHE_ADAPTER = get_adapter('cache')
_TTL_CONTACT_FORM = int(os.getenv('TTL_CONTACT_FORM', 30))
_CONTACT_COPYRIGHT_NAME_FOOTER = os.getenv('CONTACT_COPYRIGHT_NAME_FOOTER', 'CWCloud')
_CONTACT_FOOTER_LOGO = os.getenv('CONTACT_FOOTER_LOGO', 'https://assets.cwcloud.tech/assets/logos/cwcloud-gold.png')

current_year = datetime.now().year

def send_email_with_chosen_template(receiver_email, activateLink, subject, template):
    if EMAIL_ADAPTER().is_disabled():
        return {}

    content = template.render(
        activateLink = activateLink,
        currentYear = current_year,
        copyrigth_name_footer = _CONTACT_COPYRIGHT_NAME_FOOTER,
        contact_footer_logo = _CONTACT_FOOTER_LOGO
    )

    log_msg("INFO", "[send_email] Send from = {}, to = {}, content = {}".format(EMAIL_EXPEDITOR, receiver_email, activateLink))
    return EMAIL_ADAPTER().send({
        'from': EMAIL_EXPEDITOR,
        'to': receiver_email,
        'content': content,
        'subject': subject
    })

def send_confirmation_email(receiver_email, activateLink, subject):
    log_msg("INFO", "[send_confirmation_email] activateLink = {}".format(activateLink))
    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('confirmation_mail.j2')
    return send_email_with_chosen_template(receiver_email, activateLink, subject, template)

def send_device_confirmation_email(receiver_email, activateLink, subject):
    log_msg("INFO", "[send_device_confirmation_email] activateLink = {}".format(activateLink))
    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('/iot/device_confirmation_mail.j2')
    return send_email_with_chosen_template(receiver_email, activateLink, subject, template)

def send_user_and_device_confirmation_email(receiver_email, generated_password, activateLink, subject):
    log_msg("INFO", "[send_user_and_device_confirmation_email] activateLink = {}".format(activateLink))
    if EMAIL_ADAPTER().is_disabled():
        return {}

    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('/iot/user_and_device_confirmation_mail.j2')
    content = template.render(
        email = receiver_email,
        password = generated_password,
        activateLink = activateLink,
        currentYear = current_year
    )
    log_msg("INFO", "[send_email] Send from = {}, to = {}, content = {}".format(EMAIL_EXPEDITOR, receiver_email, activateLink))
    return EMAIL_ADAPTER().send({
        'from': EMAIL_EXPEDITOR,
        'to': receiver_email,
        'content': content,
        'subject': subject
    })

def send_user_confirmation_email_without_activation_link(receiver_email, generated_password, subject):
    log_msg("INFO", "[send_user_confirmation_email_without_activation_link] generated_password = {}".format(generated_password))
    if EMAIL_ADAPTER().is_disabled():
        return {}

    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('/confirmation_mail_without_activation_link.j2')
    content = template.render(
        password = generated_password,
        currentYear = current_year
    )
    log_msg("INFO", "[send_email] Send from = {}, to = {}, content = {}".format(EMAIL_EXPEDITOR, receiver_email, generated_password))
    return EMAIL_ADAPTER().send({
        'from': EMAIL_EXPEDITOR,
        'to': receiver_email,
        'content': content,
        'subject': subject
    })

def send_forget_password_email(receiver_email, activateLink, subject):
    log_msg("INFO", "[send_forget_password_email] activateLink = {}".format(activateLink))
    if EMAIL_ADAPTER().is_disabled():
        return {}

    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('forget_password_mail.j2')
    content = template.render(
        activateLink = activateLink,
        currentYear = current_year,
        copyrigth_name_footer = _CONTACT_COPYRIGHT_NAME_FOOTER,
        contact_footer_logo = _CONTACT_FOOTER_LOGO
    )

    log_msg("INFO", "[send_email] Send from = {}, to = {}, link = {}".format(EMAIL_EXPEDITOR, receiver_email, activateLink))
    return EMAIL_ADAPTER().send({
        'from': EMAIL_EXPEDITOR,
        'to': receiver_email,
        'content': content,
        'subject': subject
    })

def send_templated_email(email):
    if EMAIL_ADAPTER().is_disabled():
        return {}

    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('email.j2')
    content = template.render(
        body = email['content'],
        title = email['subject'],
        currentYear = current_year
    )
    email['content'] = content
    return EMAIL_ADAPTER().send(email)

def send_email(receiver_email, body, subject):
    return send_templated_email({
        'from': EMAIL_EXPEDITOR,
        'to': receiver_email,
        'content': body,
        'subject': subject
    })

def send_contact_email(email, receiver_email, body, subject):
    return send_contact_form_request(EMAIL_EXPEDITOR, email, receiver_email, body, subject, _CONTACT_COPYRIGHT_NAME_FOOTER, _CONTACT_FOOTER_LOGO)

def send_contact_form_request(mail_from, reply_to, mail_to, body, subject, copyright_name, logo_url):
    if EMAIL_ADAPTER().is_disabled():
        return {
            'status': 'ok',
            'response': 'Email third part is disabled'
        }

    key_cf_ttl = f"cf_{body['host']}"
    if is_not_empty(_CACHE_ADAPTER().get(key_cf_ttl)):
        log_msg("WARN", "[send_contact_form_request] Sender exceed rate limiting (max = {} seconds): from = {}, host = {}, to = {}, content = {}".format(_TTL_CONTACT_FORM, mail_from, body['host'], mail_to, body))
        _CACHE_ADAPTER().put(key_cf_ttl, body['host'], _TTL_CONTACT_FORM, "seconds")
        return {
            'status': 'ko',
            'i18n_code': 'cf_rate_limiting',
            'http_code': 429,
            'error': f"You exceed the rate limiting, retry in {_TTL_CONTACT_FORM} seconds",
            'cid': get_current_cid()
        }

    is_acceptable, i18n_code = is_message_acceptable(body['message'])
    if is_false(is_acceptable):
        log_msg("WARN", "[send_contact_form_request] Content looks like spam: from = {}, host = {}, to = {}, content = {}".format(mail_from, body['host'], mail_to, body))
        _CACHE_ADAPTER().put(key_cf_ttl, body['host'], _TTL_CONTACT_FORM, "seconds")
        return {
            'status': 'ko',
            'i18n_code': i18n_code,
            'http_code': 400,
            'error': 'Body is detected as spam',
            'cid': get_current_cid()
        }

    file_loader = FileSystemLoader(str(Path(__file__).resolve().parents[1]) + '/templates')
    env = Environment(loader=file_loader, autoescape=select_autoescape(AUTOESCAPE_EXTENSIONS))
    template = env.get_template('email.j2')

    opt_name = ""
    if is_not_empty_key(body, 'name'):
        opt_name = f"<li><b>Name:</b> {body['name']}</li>"

    opt_firstname = ""
    if is_not_empty_key(body, 'firstname'):
        opt_firstname = f"<li><b>First name:</b> {body['firstname']}</li>"

    opt_form = ""
    if is_not_empty_key(body, 'form_id') and is_not_empty_key(body, 'form_name'):
        opt_form = f"<li><b>Form:</b> {body['form_id']} / {body['form_name']}</li>"

    html = "This email is from the following expeditor:" \
        "<ul>" \
        f"<li><b>Email:</b> {mail_from}</li>" \
        f"{opt_firstname}" \
        f"{opt_name}" \
        f"<li><b>Host:</b> {body['host']}</li>" \
        f"<li><b>Api env:</b> {get_api_url()}</li>" \
        f"{opt_form}" \
        f"<li><b>Object:</b> {subject}</li>" \
        f"</ul><br /><hr />{body['message']}"

    content = template.render(
        body = html,
        title = subject,
        currentYear = current_year,
        copyrigth_name_footer = copyright_name,
        contact_footer_logo = logo_url
    )

    log_msg("INFO", "[send_contact_form_request] Send from = {}, to = {}, reply_to = {}, subject = {}, content = {}".format(mail_from, mail_to, reply_to, subject, body))
    _CACHE_ADAPTER().put(key_cf_ttl, body['host'], _TTL_CONTACT_FORM, "seconds")
    return EMAIL_ADAPTER().send({
        'from': mail_from,
        'replyto': reply_to,
        'to': mail_to,
        'content': content,
        'subject': f"CWCloud's contact form: {subject}"
    })

def send_create_instance_email(user_email, project_repo_url, instance_name, environment, access_password, root_dns_zone):
    if EMAIL_ADAPTER().is_disabled():
        return {}

    instance_url = "https://{}.{}.{}".format(instance_name, environment['path'], root_dns_zone)
    subject = "New Cloud instance access information"
    message_tpl = "Cloud instance information: <ul>" + \
        "<li>Environment: {}</li>" + \
        "<li>Instance name: {}</li>" + \
        "<li>Instance domain: {}</li>" + \
        "<li>Access password: {}</li>" + \
        "<li>GitLab repository URL: {}</li>" + \
        "</ul>"
    message = message_tpl.format(environment['name'], instance_name, instance_url, access_password, project_repo_url)

    return send_email(user_email, message, subject)

def send_reply_to_customer_email(customer_email, subject, reply_message):
    if EMAIL_ADAPTER().is_disabled():
        return {}

    subject = "Re: " + subject
    message_tpl = "You have a new reply to your support ticket: <ul>" + \
        "<li>Subject: {}</li>" + \
        "<li>Message: {}</li>" + \
        "</ul>"
    message = message_tpl.format(subject, reply_message)

    return send_email(customer_email, message, subject)

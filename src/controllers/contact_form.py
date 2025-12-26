from fastapi.responses import JSONResponse
from fastapi import HTTPException

from datetime import datetime
from entities.ContactForm import ContactForm
from utils.observability.cid import get_current_cid
from utils.dynamic_name import generate_hashed_name

def get_all_forms(current_user, db):
    return ContactForm.getUserContactForms(current_user.id, db)

def get_form_by_id(form_id, db):
    return ContactForm.findContactFormById(form_id, db)

def get_form_by_user_and_id(current_user, form_id, db):
    form = ContactForm.findUserContactFormById(current_user.id, form_id, db)
    if not form:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Contact form not found',
            'i18n_code': 'contact_form_not_found',
            'cid': get_current_cid()
        }, status_code = 404)
    
    return form

def add_form(current_user, payload, db):
    try:    
        new_form = ContactForm(**payload.dict())
        new_form.user_id = current_user.id
        hash, hashed_form_name = generate_hashed_name(new_form.name)
        new_form.name = hashed_form_name
        new_form.hash = hash
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        new_form.created_at = current_date
        new_form.updated_at = current_date
        new_form.save(db)

        return JSONResponse(content = {
            'status': 'ok',
            'message': 'Contact form successfully created',
            'id': str(new_form.id),
            'i18n_code': 'contact_form_created'
        }, status_code = 201)

    except HTTPException as e:
        return JSONResponse(content = {
            'status': 'ko',
            'message': e.detail,
            'cid': get_current_cid()
        }, status_code = e.status_code)
        
def update_form(current_user, form_id, payload, db):
    form = ContactForm.findUserContactFormById(current_user.id, form_id, db)
    if not form:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Contact form not found',
            'i18n_code': 'contact_form_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    payload.name = "{}-{}".format(payload.name, form.hash)
    ContactForm.updateInfo(form_id, payload.name, payload.mail_from, payload.mail_to, payload.copyright_name, payload.logo_url, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Contact form successfully updated',
        'id': form_id,
        'i18n_code': 'contact_form_updated'
    })

def remove_form(current_user, form_id, db):
    form = ContactForm.findUserContactFormById(current_user.id, form_id, db)
    if not form:
        return JSONResponse(content = {
            'status': 'ko',
            'error': 'Contact form not found',
            'i18n_code': 'contact_form_not_found',
            'cid': get_current_cid()
        }, status_code = 404)

    ContactForm.deleteUserContactForm(current_user.id, form_id, db)

    return JSONResponse(content = {
        'status': 'ok',
        'message': 'Contact form successfully deleted',
        'id': form_id,
        'i18n_code': 'contact_form_deleted'
    })

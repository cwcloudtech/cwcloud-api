from sqlalchemy import Column, Integer, String, ForeignKey
from fastapi_utils.guid_type import GUID_SERVER_DEFAULT_POSTGRESQL
from database.postgres_db import Base
from database.types import CachedGUID

class ContactForm(Base):
    __tablename__ = 'contact_form'
    id = Column(CachedGUID, primary_key=True, server_default=GUID_SERVER_DEFAULT_POSTGRESQL)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    mail_from = Column(String, nullable=False)
    mail_to = Column(String, nullable=False)
    name = Column(String, nullable=False)
    hash = Column(String(10))
    copyright_name = Column(String)
    logo_url = Column(String)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

    def save(self, db):
        db.add(self)
        db.commit()

    @staticmethod
    def getAllContactForms(db):
        forms = db.query(ContactForm).all()
        return forms
    
    @staticmethod
    def getUserContactForms(user_id, db):
        forms = db.query(ContactForm).filter(ContactForm.user_id == user_id).all()
        return forms

    @staticmethod
    def findContactFormById(contact_form_id, db):
        form = db.query(ContactForm).filter(ContactForm.id == contact_form_id).first()
        return form

    @staticmethod
    def findUserContactFormById(user_id, contact_form_id, db):
        form = db.query(ContactForm).filter(ContactForm.id == contact_form_id, ContactForm.user_id == user_id).first()
        return form

    @staticmethod
    def deleteUserContactForm(user_id, contact_form_id, db):
        form = db.query(ContactForm).filter(ContactForm.id == contact_form_id, ContactForm.user_id == user_id).first()
        db.delete(form)
        db.commit()

    @staticmethod
    def deleteContactForm(contact_form_id, db):
        form = db.query(ContactForm).filter(ContactForm.id == contact_form_id).first()
        db.delete(form)
        db.commit()

    @staticmethod
    def updateInfo(contact_form_id, mail_from, mail_to, copyright_name, logo_url, db):
        db.query(ContactForm).filter(ContactForm.id == contact_form_id).update({"mail_from": mail_from, "mail_to": mail_to, "copyright_name": copyright_name, "logo_url": logo_url})
        db.commit()

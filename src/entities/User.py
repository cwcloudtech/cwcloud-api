from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from database.postgres_db import Base
from entities.Project import Project
from entities.Instance import Instance
from entities.Bucket import Bucket
from entities.Registry import Registry
from entities.Apikeys import ApiKeys
from entities.SupportTicketLog import SupportTicketLog
from entities.SupportTicket import SupportTicket

from utils.common import generate_hash_password

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key = True)
    email = Column(String(200))
    enabled_features = Column(JSONB, nullable=False)
    registration_number = Column(String(300))
    address = Column(String(300))
    company_name = Column(String(200))
    contact_info = Column(String(300))
    password = Column(String(200))
    is_admin = Column(Boolean, default = False)
    confirmed = Column(Boolean, default = False)
    created_at = Column(String(100), default = datetime.now().isoformat())
    projects = relationship("Project", backref = "user", lazy = "select")
    instances = relationship("Instance", backref = "user", lazy = "select")
    buckets = relationship("Bucket", backref = "user", lazy = "select")
    registries = relationship("Registry", backref = "user", lazy = "select")
    api_keys = relationship("ApiKeys", backref = "user", lazy = "select")
    support_ticket_logs = relationship("SupportTicketLog", backref = "user", lazy = "select")
    support_ticket = relationship("SupportTicket", backref = "user", lazy = "select")

    def hashed_table(self):
        return {
            "id": self.id,
            "created_at": self.created_at,
            "email": self.email,
            "confirmed": self.confirmed,
            "is_admin": self.is_admin,
            "registration_number": self.registration_number,
            "company_name": self.company_name,
            "contact_info": self.contact_info,
            "address": self.address,
            "enabled_features": self.enabled_features
        }

    def save(self, db):
        db.add(self)
        db.commit()
        db.refresh(self)

    @staticmethod
    def getUserByEmail(email, db):
        user = db.query(User).filter(User.email == email).first()
        return user

    @staticmethod
    def getUserById(userId, db):
        user = db.query(User).filter(User.id == userId).first()
        return user

    @staticmethod
    def deleteUserById(userId, db):
        db.query(User).filter(User.id == userId).delete()
        db.commit()

    @staticmethod
    def updateConfirmation(userId, confirmedStatus, db):
        db.query(User).filter(User.id == userId).update({"confirmed": confirmedStatus})
        db.commit()

    @staticmethod
    def updateUserRole(userId, RoleStatus, db):
        db.query(User).filter(User.id == userId).update({"is_admin": RoleStatus})
        db.commit()

    @staticmethod
    def updateUser(id, payload, db):
        db.query(User).filter(User.id == id).update({"email": payload.email, "company_name": payload.company_name, "registration_number": payload.registration_number, "address": payload.address, "contact_info": payload.contact_info})
        db.commit()

    @staticmethod
    def adminUpdateUser(id, payload, db):
        db.query(User).filter(User.id == id).update({
            "email": payload.email,
            "is_admin": payload.is_admin,
            "company_name": payload.company_name,
            "registration_number": payload.registration_number,
            "address": payload.address,
            "contact_info": payload.contact_info,
            "enabled_features": {
                "billable": True,
                "without_vat": False,
                "auto_pay": False,
                "emailapi": payload.enabled_features.emailapi,
                "cwaiapi": payload.enabled_features.cwaiapi,
                "faasapi": payload.enabled_features.faasapi,
                "disable_emails": payload.enabled_features.disable_emails,
                "k8sapi": payload.enabled_features.k8sapi,
                "daasapi": payload.enabled_features.daasapi,
                "iotapi": payload.enabled_features.iotapi,
                "monitorapi": payload.enabled_features.monitorapi,
                "storageapi": payload.enabled_features.storageapi,
                "block": payload.enabled_features.block
            }
        })
        db.commit()

    @staticmethod
    def updateUserEmail(id, email, db):
        db.query(User).filter(User.id == id).update({"email": email})
        db.commit()

    @staticmethod
    def updateUserPassword(id, password, db):
        db.query(User).filter(User.id == id).update({"password": generate_hash_password(password)})
        db.commit()

    @staticmethod
    def updateUserPasswordAndConfirm(id, password, db):
        db.query(User).filter(User.id == id).update({"password": generate_hash_password(password), "confirmed": True})
        db.commit()

    @staticmethod
    def getAllUsers(db):
        users = []
        for user in db.query(User).all():
            del user.__dict__["_sa_instance_state"]
            del user.__dict__["password"]
            users.append(user.__dict__)
        return users

    @staticmethod
    def getFirstAdminUser(db):
        user = db.query(User).filter(User.is_admin).first()
        return user

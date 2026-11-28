from database.postgres_db import Base
from sqlalchemy import Column, ForeignKey, String, Integer
from datetime import datetime

class ApiKeys(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key = True)
    access_key = Column(String(100), unique = True)
    name = Column(String(200))
    secret_key = Column(String(100), unique = True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable = False)
    created_at = Column(String(100), default = datetime.now().isoformat())

    def save(self, db):
        db.add(self)
        db.commit()

    @staticmethod
    def getUserApiKeys(user_id, db):
        apiKeys = db.query(ApiKeys).filter(ApiKeys.user_id == user_id).all()
        return apiKeys

    @staticmethod
    def getAllApiKeys(db):
        return db.query(ApiKeys).order_by(ApiKeys.id.desc()).all()

    @staticmethod
    def getApiKeyById(key_id, db):
        return db.query(ApiKeys).filter(ApiKeys.id == key_id).first()

    @staticmethod
    def getApiKeysByAccessKey(access_key, db):
        apiKeys = db.query(ApiKeys).filter(ApiKeys.access_key == access_key).all()
        return apiKeys

    @staticmethod
    def getApiKeysBySecretKey(secret_key, db):
        apiKeys = db.query(ApiKeys).filter(ApiKeys.secret_key == secret_key).all()
        return apiKeys

    @staticmethod
    def getApiKeyBySecretKey(secret_key, db):
        apiKey = db.query(ApiKeys).filter(ApiKeys.secret_key == secret_key).first()
        return apiKey

    @staticmethod
    def getUserApiKey(user_id, key_id, db):
        apiKey = db.query(ApiKeys).filter(ApiKeys.user_id == user_id, ApiKeys.id == key_id).first()
        return apiKey

    @staticmethod
    def getApiKey(access_key, secret_key, db):
        apiKey = db.query(ApiKeys).filter(ApiKeys.access_key == access_key, ApiKeys.secret_key == secret_key).first()
        return apiKey

    @staticmethod
    def deleteUserAllApiKeys(user_id, db):
        db.query(ApiKeys).filter(ApiKeys.user_id == user_id).delete()
        db.commit()

    @staticmethod
    def deleteUserApiKey(user_id, key_id, db):
        db.query(ApiKeys).filter(ApiKeys.user_id == user_id, ApiKeys.id == key_id).delete()
        db.commit()

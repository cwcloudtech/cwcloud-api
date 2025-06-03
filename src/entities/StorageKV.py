from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from fastapi_utils.guid_type import GUID_SERVER_DEFAULT_POSTGRESQL
from database.postgres_db import Base
from database.types import CachedGUID

class StorageKV(Base):
    __tablename__ = 'storage_kv'
    id = Column(CachedGUID, primary_key=True, server_default=GUID_SERVER_DEFAULT_POSTGRESQL)
    storage_key = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    def save(self, db):
        db.add(self)
        db.commit()
        db.refresh(self)
        return self

    @staticmethod
    def getUserStorageKVs(user_id, db):
        storage_kvs = db.query(StorageKV).filter(StorageKV.user_id == user_id).all()
        return storage_kvs
    
    @staticmethod
    def searchUserStorageKVsByKey(user_id, search_term, db):
        search_pattern = f"%{search_term}%"
        storage_kvs = db.query(StorageKV).filter(
            StorageKV.user_id == user_id,
            func.lower(StorageKV.storage_key).like(func.lower(search_pattern))
        ).all()
        return storage_kvs

    @staticmethod
    def searchStorageKVsByKey(search_term, db):
        search_pattern = f"%{search_term}%"
        storage_kvs = db.query(StorageKV).filter(
            func.lower(StorageKV.storage_key).like(func.lower(search_pattern))
        ).all()
        return storage_kvs

    @staticmethod
    def findStorageKVById(storage_kv_id, db):
        storage_kv = db.query(StorageKV).filter(StorageKV.id == storage_kv_id).first()
        return storage_kv

    @staticmethod
    def findUserStorageKVByKey(user_id, storage_key, db):
        storage_kv = db.query(StorageKV).filter(
            StorageKV.user_id == user_id,
            StorageKV.storage_key == storage_key
        ).first()
        return storage_kv

    @staticmethod
    def updateStorageKV(user_id, storage_key, payload, db):
        storage_kv = StorageKV.findUserStorageKVByKey(user_id, storage_key, db)
        if storage_kv:
            update_data = {
                'payload': payload,
                'updated_at': datetime.now()
            }
            db.query(StorageKV).filter(
                StorageKV.user_id == user_id,
                StorageKV.storage_key == storage_key
            ).update(update_data)
            db.commit()
            db.refresh(storage_kv)
            return storage_kv
        return None

    @staticmethod
    def deleteUserStorageKV(user_id, storage_key, db):
        storage_kv = db.query(StorageKV).filter(
            StorageKV.user_id == user_id,
            StorageKV.storage_key == storage_key
        ).first()
        if storage_kv:
            db.delete(storage_kv)
            db.commit()
            return True
        return False

    @staticmethod
    def deleteStorageKVById(storage_kv_id, db):
        storage_kv = db.query(StorageKV).filter(StorageKV.id == storage_kv_id).first()
        if storage_kv:
            db.delete(storage_kv)
            db.commit()
            return True
        return False

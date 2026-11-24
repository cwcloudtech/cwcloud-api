from datetime import datetime

from sqlalchemy import Column, String, Integer
from sqlalchemy.dialects.postgresql import JSONB
from fastapi_utils.guid_type import GUID_SERVER_DEFAULT_POSTGRESQL

from database.postgres_db import Base
from database.types import CachedGUID

class InvocationEntity(Base):
    __tablename__ = 'faas_invocation'
    id = Column(CachedGUID, primary_key=True, server_default=GUID_SERVER_DEFAULT_POSTGRESQL)
    content = Column(JSONB, nullable=False)
    invoker_id = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False, default=datetime.now)
    updated_at = Column(String, nullable=False, default=datetime.now)

    @staticmethod
    def transferAllInvocationsOwnership(invoker_id, new_invoker_id, db):
        invocations = db.query(InvocationEntity).filter(InvocationEntity.invoker_id == invoker_id).all()
        for invocation in invocations:
            invocation.invoker_id = new_invoker_id
        db.commit()

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

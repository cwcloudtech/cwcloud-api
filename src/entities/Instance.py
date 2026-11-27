from sqlalchemy import Column, ForeignKey, String, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from database.postgres_db import Base

class Instance(Base):
    __tablename__ = "instance"
    id = Column(Integer, primary_key = True)
    hash = Column(String(10))
    name = Column(String(200))
    type = Column(String(50))
    created_at = Column(String(100), default = datetime.now().isoformat())
    user_id = Column(Integer, ForeignKey("user.id"))
    environment_id = Column(Integer, ForeignKey("environment.id"))
    project_id = Column(Integer, ForeignKey("project.id"))
    region = Column(String(100))
    zone = Column(String(100))
    provider = Column(String(100))
    status = Column(String(50), default = "starting")
    ip_address = Column(String(100), default = "Null")
    modification_date = Column(String(100), default = datetime.now().isoformat())
    root_dns_zone = Column(String(254))
    is_protected = Column(Boolean, default = False)

    def save(self, db):
        db.add(self)
        db.commit()

    @staticmethod
    def getUserInstances(userId, db):
        instances = db.query(Instance).filter(Instance.user_id == userId).all()
        return instances

    @staticmethod
    def findInstances(instancesIds, db):
        instances = db.query(Instance).filter(Instance.id.in_(instancesIds)).all()
        return instances

    @staticmethod
    def findInstancesByRegion(instancesIds, provider, region, db):
        instances = db.query(Instance).filter(Instance.id.in_(instancesIds), Instance.provider == provider, Instance.region == region, Instance.status != "deleted").all()
        return instances

    @staticmethod
    def getUserInstance(userId, instance_id, db):
        instance = db.query(Instance).filter(Instance.id == instance_id, Instance.user_id == userId).first()
        return instance

    @staticmethod
    def getActiveUserInstances(userId, db):
        instances = db.query(Instance).filter(Instance.user_id == userId, Instance.status  != "deleted").all()
        return instances

    @staticmethod
    def findUserInstance(userId, provider, region, instanceId, db):
        user_instance = db.query(Instance).filter(Instance.provider == provider, Instance.region == region, Instance.user_id == userId, Instance.id == instanceId, Instance.status != "deleted").first()
        return user_instance

    @staticmethod
    def findInstance(provider, region, instanceId, db):
        user_instance = db.query(Instance).filter(Instance.provider == provider, Instance.region == region, Instance.id == instanceId, Instance.status  != "deleted").first()
        return user_instance

    @staticmethod
    def findUserInstanceByName(userId, name, db):
        user_instance = db.query(Instance).filter(Instance.user_id == userId, Instance.name == name).order_by(Instance.id.desc()).first()
        return user_instance

    @staticmethod
    def findUserAvailableInstanceByName(userId, name, db):
        user_instance = db.query(Instance).filter(Instance.user_id == userId, Instance.name == name, Instance.status != "deleted").first()
        return user_instance

    @staticmethod
    def findInstanceById(id, db):
        user_instance = db.query(Instance).filter(Instance.id == id, Instance.status != "deleted").first()
        return user_instance

    @staticmethod
    def findInstanceByIpAddress(ip_address, db):
        user_instance = db.query(Instance).filter(Instance.ip_address == ip_address, Instance.status != "deleted").first()
        return user_instance

    @staticmethod
    def updateModificationDate(instance_id, newDate, db):
        db.query(Instance).filter(Instance.id == instance_id).update({"modification_date": newDate})
        db.commit()

    @staticmethod
    def updateStatus(instance_id, status, db):
        db.query(Instance).filter(Instance.id == instance_id).update({"status": status})
        db.commit()

    @staticmethod
    def updateInstanceIp(instance_id, ip_address, db):
        db.query(Instance).filter(Instance.id == instance_id).update({"ip_address": ip_address})
        db.commit()

    @staticmethod
    def getActiveUserInstancesPerRegion(userId, provider, region, db):
        instances = db.query(Instance).filter(Instance.user_id == userId, Instance.provider == provider, Instance.region == region, Instance.status  != "deleted").all()
        return instances

    @staticmethod
    def getAllActiveInstances(db):
        instances = db.query(Instance).filter(Instance.status != "deleted").all()
        return instances

    @staticmethod
    def getAllActiveInstancesByProject(projectId, db):
        instances = db.query(Instance).filter(Instance.project_id == projectId, Instance.status != "deleted").all()
        return instances

    @staticmethod
    def updateProjectInstancesOwner(projectId, owner_id, db):
        db.query(Instance).filter(Instance.project_id == projectId, Instance.status != "deleted").update({"user_id": owner_id})
        db.commit()

    @staticmethod
    def getAllInstances(db):
        instances = db.query(Instance).filter(Instance.status != "deleted").all()
        return instances

    @staticmethod
    def getAllInstancesByRegion(provider, region, db):
        instances = db.query(Instance).filter(Instance.provider == provider, Instance.region == region, Instance.status != "deleted").all()
        return instances

    @staticmethod
    def getAllUserInstancesByRegion(provider, region, user_id, db):
        instances = db.query(Instance).filter(Instance.provider == provider, Instance.region == region, Instance.user_id == user_id, Instance.status != "deleted").all()
        return instances

    @staticmethod
    def getAllUserInstances(user_id, db):
        instances = db.query(Instance).filter(Instance.user_id == user_id).all()
        return instances

    @staticmethod
    def updateInfo(id, provider, region, zone, instance_type, status, ip_address, root_dns_zone, db):
        current_date = datetime.now().isoformat()
        db.query(Instance).filter(Instance.id == id).update({"modification_date": current_date, "provider": provider, "region": region, "zone": zone, "type": instance_type, "status": status, "ip_address": ip_address, "root_dns_zone": root_dns_zone})
        db.commit()

    @staticmethod
    def updateType(id, type, db):
        current_date = datetime.now().isoformat()
        db.query(Instance).filter(Instance.id == id).update({"modification_date": current_date, "type": type})
        db.commit()

    @staticmethod
    def updateTypeAndIp(id, type, ip, db):
        current_date = datetime.now().isoformat()
        db.query(Instance).filter(Instance.id == id).update({"modification_date": current_date, "type": type, "ip_address": ip})
        db.commit()

    @staticmethod
    def recreateInstanceInfo(instanceId, provider, region, zone, instance_type, status, ip_address, root_dns_zone, project_id, db):
        current_date = datetime.now().isoformat()
        db.query(Instance).filter(Instance.id == instanceId).update({"modification_date": current_date, "provider": provider, "region": region, "zone": zone, "type": instance_type, "status": status, "ip_address": ip_address, "root_dns_zone": root_dns_zone, "project_id": project_id})
        db.commit()


    @staticmethod
    def updateProtection(instance_id, is_protected, db):
        db.query(Instance).filter(Instance.id == instance_id).update({"is_protected": is_protected})
        db.commit()

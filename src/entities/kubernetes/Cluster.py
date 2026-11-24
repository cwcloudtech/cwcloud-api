from sqlalchemy import Column, ForeignKey, String, Integer, UniqueConstraint, Table
from datetime import datetime
from entities.kubernetes.KubeconfigFile import KubeConfigFile
from database.postgres_db import Base

class Cluster(Base):
    __tablename__ = "k8s_cluster"
    id = Column(Integer, primary_key = True)
    name = Column(String(100))
    kubeconfig_file_id = Column(Integer, ForeignKey("k8s_kubeconfig_files.id"))
    version = Column(String(100))
    platform = Column(String(100))
    created_at = Column(String(100), default = datetime.isoformat(datetime.now()))

    def save(self, db):
        db.add(self)
        db.commit()

    def delete(self, db):
        db.delete(self)
        db.commit()

    @staticmethod
    def getById(id, db) -> "Cluster":
        cluster = db.query(Cluster).filter(Cluster.id == id).first()
        return cluster

    @staticmethod
    def findByKubeConfigFile(file_id, db):
        clusters = db.query(Cluster).filter(Cluster.kubeconfig_file_id == file_id).all()
        return clusters

    @staticmethod
    def getKuberConfigFileByClusterId(cluster_id, db) -> "KubeConfigFile":
        kubeconfigFile = db.query(KubeConfigFile).join(Cluster).filter(Cluster.id == cluster_id).first()
        return kubeconfigFile

    @staticmethod
    def getAll(db):
        clusters = db.query(Cluster).join(KubeConfigFile).all()
        return clusters

    @staticmethod
    def getAllForUser(db):
        clusters = db.query(Cluster).with_entities(Cluster.id, Cluster.name).all()
        return clusters

    @staticmethod
    def deleteOne(id, db):
        db.query(Cluster).filter(Cluster.id == id).delete()
        db.commit()
 
    @staticmethod
    def deleteAll(db):
        db.query(Cluster).delete()
        db.commit()

    def __str__(self):
       return f"Cluster(id={self.id}, name={self.name}, email={self.kubeconfig_file_id})"

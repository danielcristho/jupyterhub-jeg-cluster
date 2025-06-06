from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()

class Profile(db.Model):
    """
    Model untuk menyimpan profile JupyterHub
    (single node, multi node, dll)
    """
    __tablename__ = 'profiles'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    node_count = db.Column(db.Integer, default=1)  # Jumlah node yang dibutuhkan
    cpu_requirement = db.Column(db.Float, default=1.0)  # CPU requirement per node
    memory_requirement = db.Column(db.Float, default=2.0)  # Memory requirement per node (GB)
    gpu_required = db.Column(db.Boolean, default=False)
    max_cpu_usage = db.Column(db.Integer, default=60)  # Max CPU usage threshold
    max_memory_usage = db.Column(db.Integer, default=60)  # Max memory usage threshold
    max_active_containers = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship
    allocations = db.relationship('NodeAllocation', backref='profile', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': str(self.id),  # Convert UUID to string
            'name': self.name,
            'description': self.description,
            'node_count': self.node_count,
            'cpu_requirement': self.cpu_requirement,
            'memory_requirement': self.memory_requirement,
            'gpu_required': self.gpu_required,
            'max_cpu_usage': self.max_cpu_usage,
            'max_memory_usage': self.max_memory_usage,
            'max_active_containers': self.max_active_containers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

class NodeAllocation(db.Model):
    """
    Model untuk tracking alokasi node untuk user/session tertentu
    """
    __tablename__ = 'node_allocations'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(db.String(255), nullable=False)  # JupyterHub session ID
    user_id = db.Column(db.String(100), nullable=False)  # JupyterHub user ID
    profile_id = db.Column(UUID(as_uuid=True), db.ForeignKey('profiles.id'), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)  # Node hostname
    node_ip = db.Column(db.String(50))  # Node IP
    status = db.Column(db.String(20), default='allocated')  # allocated, running, stopped, failed
    container_id = db.Column(db.String(255))  # Docker container ID jika ada
    port = db.Column(db.Integer)  # Port yang digunakan
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    stopped_at = db.Column(db.DateTime)
    extra_data = db.Column(db.Text)  # JSON untuk menyimpan metadata tambahan

    def to_dict(self):
        return {
            'id': str(self.id),  # Convert UUID to string
            'session_id': self.session_id,
            'user_id': self.user_id,
            'profile_id': str(self.profile_id),  # Convert UUID to string
            'profile_name': self.profile.name if self.profile else None,
            'hostname': self.hostname,
            'node_ip': self.node_ip,
            'status': self.status,
            'container_id': self.container_id,
            'port': self.port,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None,
            'extra_data': json.loads(self.extra_data) if self.extra_data else None
        }

class UserSession(db.Model):
    """
    Model untuk tracking session user dengan multiple nodes
    """
    __tablename__ = 'user_sessions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(db.String(255), nullable=False, unique=True)
    user_id = db.Column(db.String(100), nullable=False)
    profile_id = db.Column(UUID(as_uuid=True), db.ForeignKey('profiles.id'), nullable=False)
    status = db.Column(db.String(20), default='initializing')  # initializing, running, stopping, stopped
    requested_nodes = db.Column(db.Integer, default=1)
    allocated_nodes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    stopped_at = db.Column(db.DateTime)

    # Relationship
    profile = db.relationship('Profile', backref='sessions')

    def to_dict(self):
        return {
            'id': str(self.id),  # Convert UUID to string
            'session_id': self.session_id,
            'user_id': self.user_id,
            'profile_id': str(self.profile_id),  # Convert UUID to string
            'profile_name': self.profile.name if self.profile else None,
            'status': self.status,
            'requested_nodes': self.requested_nodes,
            'allocated_nodes': self.allocated_nodes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'stopped_at': self.stopped_at.isoformat() if self.stopped_at else None
        }
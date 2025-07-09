from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from . import db

class Node(db.Model):
    __tablename__ = 'nodes'

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip = db.Column(db.String(45), nullable=False, index=True)
    cpu_cores = db.Column(db.Integer, nullable=False)
    ram_gb = db.Column(db.Float, nullable=False)
    has_gpu = db.Column(db.Boolean, default=False, index=True)
    gpu_info = db.Column(JSON, default=list)

    # Node status & capacity
    is_active = db.Column(db.Boolean, default=True, index=True)
    max_containers = db.Column(db.Integer, default=10)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    metrics = db.relationship('NodeMetric', back_populates='node', cascade='all, delete-orphan')

    # Redis state, non persistent
    _current_cpu_usage = None
    _current_memory_usage = None
    _current_disk_usage = None
    _active_jupyterlab = 0
    _active_ray = 0
    _total_containers = 0

    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip': self.ip,
            'cpu_cores': self.cpu_cores,
            'ram_gb': self.ram_gb,
            'has_gpu': self.has_gpu,
            'gpu_info': self.gpu_info,
            'is_active': self.is_active,
            'max_containers': self.max_containers,
            'cpu_usage_percent': self._current_cpu_usage,
            'memory_usage_percent': self._current_memory_usage,
            'disk_usage_percent': self._current_disk_usage,
            'active_jupyterlab': self._active_jupyterlab,
            'active_ray': self._active_ray,
            'total_containers': self._total_containers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_current_metrics(self, metrics_dict):
        """Update current metrics from Redis data"""
        self._current_cpu_usage = metrics_dict.get('cpu_usage_percent', 0)
        self._current_memory_usage = metrics_dict.get('memory_usage_percent', 0)
        self._current_disk_usage = metrics_dict.get('disk_usage_percent', 0)
        self._active_jupyterlab = metrics_dict.get('active_jupyterlab', 0)
        self._active_ray = metrics_dict.get('active_ray', 0)
        self._total_containers = metrics_dict.get('total_containers', 0)

    def __repr__(self):
        return f'<Node {self.hostname}>'
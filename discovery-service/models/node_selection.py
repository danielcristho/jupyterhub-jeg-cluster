from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from . import db

class NodeSelection(db.Model):
    __tablename__ = 'node_selections'

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    user_id = db.Column(db.String(255), index=True)  # JupyterHub user
    session_id = db.Column(db.String(255))
    selected_nodes = db.Column(JSON)  # array of {'id': x, 'hostname': y}
    selection_reason = db.Column(db.String(50))  # 'manual', 'auto_balanced', 'profile_based'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    profile = db.relationship('Profile', back_populates='selections')

    def to_dict(self):
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'profile_name': self.profile.name if self.profile else None,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'selected_nodes': self.selected_nodes,
            'selection_reason': self.selection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NodeMetric(db.Model):
    __tablename__ = 'node_metrics'

    id = db.Column(db.Integer, primary_key=True)
    node_id = db.Column(db.Integer, db.ForeignKey('nodes.id', ondelete='CASCADE'))
    cpu_usage_percent = db.Column(db.Float)
    memory_usage_percent = db.Column(db.Float)
    disk_usage_percent = db.Column(db.Float)
    active_jupyterlab = db.Column(db.Integer, default=0)
    active_ray = db.Column(db.Integer, default=0)
    total_containers = db.Column(db.Integer, default=0)
    load_score = db.Column(db.Float)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    node = db.relationship('Node', back_populates='metrics')

    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'hostname': self.node.hostname if self.node else None,
            'cpu_usage_percent': self.cpu_usage_percent,
            'memory_usage_percent': self.memory_usage_percent,
            'disk_usage_percent': self.disk_usage_percent,
            'active_jupyterlab': self.active_jupyterlab,
            'active_ray': self.active_ray,
            'total_containers': self.total_containers,
            'load_score': self.load_score,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }
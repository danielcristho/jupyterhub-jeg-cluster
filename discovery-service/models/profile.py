from datetime import datetime
from . import db

class Profile(db.Model):
    __tablename__ = 'profiles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    min_nodes = db.Column(db.Integer, default=1)
    max_nodes = db.Column(db.Integer, default=1)
    cpu_requirement = db.Column(db.Integer)  # minimum CPU cores per node
    ram_requirement = db.Column(db.Float)    # minimum RAM GB per node
    gpu_required = db.Column(db.Boolean, default=False)
    max_cpu_usage = db.Column(db.Float, default=80.0)
    max_memory_usage = db.Column(db.Float, default=85.0)
    priority = db.Column(db.Integer, default=0)  # higher priority gets better nodes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    selections = db.relationship('NodeSelection', back_populates='profile')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'min_nodes': self.min_nodes,
            'max_nodes': self.max_nodes,
            'cpu_requirement': self.cpu_requirement,
            'ram_requirement': self.ram_requirement,
            'gpu_required': self.gpu_required,
            'max_cpu_usage': self.max_cpu_usage,
            'max_memory_usage': self.max_memory_usage,
            'priority': self.priority,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def matches_node(self, node):
        """Check if a node meets this profile's requirements"""
        if self.cpu_requirement and node.cpu < self.cpu_requirement:
            return False
        if self.ram_requirement and node.ram_gb < self.ram_requirement:
            return False
        if self.gpu_required and not node.has_gpu:
            return False
        if node._current_cpu_usage and node._current_cpu_usage > self.max_cpu_usage:
            return False
        if node._current_memory_usage and node._current_memory_usage > self.max_memory_usage:
            return False
        return True

    def __repr__(self):
        return f'<Profile {self.name}>'
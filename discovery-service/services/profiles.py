from typing import List, Dict, Optional
from models import db, Profile
import logging

logger = logging.getLogger(__name__)

class ProfileService:

    @staticmethod
    def create_default_profiles():
        """Create default profiles if they don't exist"""
        default_profiles = [
            {
                'name': 'basic',
                'description': 'Basic single node for light workloads',
                'min_nodes': 1,
                'max_nodes': 1,
                'cpu_requirement': 2,
                'ram_requirement': 4.0,
                'gpu_required': False,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
                'priority': 0
            },
            {
                'name': 'distributed',
                'description': 'Multiple nodes for distributed computing',
                'min_nodes': 2,
                'max_nodes': 4,
                'cpu_requirement': 4,
                'ram_requirement': 8.0,
                'gpu_required': False,
                'max_cpu_usage': 70.0,
                'max_memory_usage': 75.0,
                'priority': 1
            },
            {
                'name': 'gpu-compute',
                'description': 'GPU-enabled nodes for ML/AI workloads',
                'min_nodes': 1,
                'max_nodes': 2,
                'cpu_requirement': 4,
                'ram_requirement': 16.0,
                'gpu_required': True,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 80.0,
                'priority': 2
            },
            {
                'name': 'high-performance',
                'description': 'High-performance nodes with strict requirements',
                'min_nodes': 1,
                'max_nodes': 3,
                'cpu_requirement': 8,
                'ram_requirement': 32.0,
                'gpu_required': False,
                'max_cpu_usage': 60.0,
                'max_memory_usage': 60.0,
                'priority': 3
            }
        ]

        for profile_data in default_profiles:
            if not Profile.query.filter_by(name=profile_data['name']).first():
                profile = Profile(**profile_data)
                db.session.add(profile)

        try:
            db.session.commit()
            logger.info("Default profiles created successfully")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating default profiles: {e}")

    @staticmethod
    def create_profile(data: dict) -> Profile:
        """Create a new profile"""
        # Validate required fields
        if not data.get('name'):
            raise ValueError("Profile name is required")

        # Check if profile name already exists
        if Profile.query.filter_by(name=data['name']).first():
            raise ValueError(f"Profile '{data['name']}' already exists")

        # Set defaults
        profile_data = {
            'name': data['name'],
            'description': data.get('description', ''),
            'min_nodes': data.get('min_nodes', 1),
            'max_nodes': data.get('max_nodes', 1),
            'cpu_requirement': data.get('cpu_requirement'),
            'ram_requirement': data.get('ram_requirement'),
            'gpu_required': data.get('gpu_required', False),
            'max_cpu_usage': data.get('max_cpu_usage', 80.0),
            'max_memory_usage': data.get('max_memory_usage', 85.0),
            'priority': data.get('priority', 0),
            'is_active': data.get('is_active', True)
        }

        # Validate min/max nodes
        if profile_data['min_nodes'] > profile_data['max_nodes']:
            raise ValueError("min_nodes cannot be greater than max_nodes")

        profile = Profile(**profile_data)
        db.session.add(profile)
        db.session.commit()

        return profile

    @staticmethod
    def get_all_profiles(active_only: bool = True) -> List[Profile]:
        """Get all profiles"""
        query = Profile.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Profile.priority.desc()).all()

    @staticmethod
    def get_profile(profile_id: int) -> Optional[Profile]:
        """Get a specific profile"""
        return Profile.query.get(profile_id)

    @staticmethod
    def get_profile_by_name(name: str) -> Optional[Profile]:
        """Get a profile by name"""
        return Profile.query.filter_by(name=name).first()

    @staticmethod
    def update_profile(profile_id: int, data: dict) -> Profile:
        """Update an existing profile"""
        profile = Profile.query.get(profile_id)
        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        # Update fields
        for field in ['description', 'min_nodes', 'max_nodes', 'cpu_requirement',
                      'ram_requirement', 'gpu_required', 'max_cpu_usage',
                      'max_memory_usage', 'priority', 'is_active']:
            if field in data:
                setattr(profile, field, data[field])

        # Validate min/max nodes
        if profile.min_nodes > profile.max_nodes:
            raise ValueError("min_nodes cannot be greater than max_nodes")

        db.session.commit()
        return profile

    @staticmethod
    def delete_profile(profile_id: int) -> bool:
        """Delete a profile (soft delete by marking inactive)"""
        profile = Profile.query.get(profile_id)
        if not profile:
            return False

        profile.is_active = False
        db.session.commit()
        return True

    @staticmethod
    def get_suitable_profiles_for_requirements(cpu: int = None,
                                                ram: float = None,
                                                gpu: bool = False) -> List[Profile]:
        """Get profiles that match given requirements"""
        profiles = Profile.query.filter_by(is_active=True)

        suitable = []
        for profile in profiles:
            if cpu and profile.cpu_requirement and profile.cpu_requirement > cpu:
                continue
            if ram and profile.ram_requirement and profile.ram_requirement > ram:
                continue
            if gpu and profile.gpu_required and not gpu:
                continue
            suitable.append(profile)

        return sorted(suitable, key=lambda p: p.priority, reverse=True)
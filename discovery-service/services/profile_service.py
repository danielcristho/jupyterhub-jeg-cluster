from typing import List, Optional
from models import db, Profile
import logging

logger = logging.getLogger(__name__)

class ProfileService:

    @staticmethod
    def create_default_profiles():
        """Create the 4 default profiles"""
        default_profiles = [
            {
                'name': 'single-cpu',
                'description': 'Single node with CPU only',
                'min_nodes': 1,
                'max_nodes': 1,
                'cpu_requirement': 4,
                'ram_requirement': 8.0,
                'gpu_required': False,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
                'priority': 0
            },
            {
                'name': 'single-gpu',
                'description': 'Single node with GPU acceleration',
                'min_nodes': 1,
                'max_nodes': 1,
                'cpu_requirement': 4,
                'ram_requirement': 16.0,
                'gpu_required': True,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
                'priority': 1
            },
            {
                'name': 'multi-cpu',
                'description': 'Multiple nodes with CPU only',
                'min_nodes': 2,
                'max_nodes': 4,
                'cpu_requirement': 4,
                'ram_requirement': 8.0,
                'gpu_required': False,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
                'priority': 2
            },
            {
                'name': 'multi-gpu',
                'description': 'Multiple nodes with GPU acceleration',
                'min_nodes': 2,
                'max_nodes': 4,
                'cpu_requirement': 4,
                'ram_requirement': 16.0,
                'gpu_required': True,
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
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
    def get_all_profiles(active_only: bool = True) -> List[Profile]:
        """Get all profiles"""
        query = Profile.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()

    @staticmethod
    def get_profile(profile_id: int) -> Optional[Profile]:
        """Get a specific profile by ID"""
        return Profile.query.get(profile_id)

    @staticmethod
    def get_profile_by_name(name: str) -> Optional[Profile]:
        """Get a profile by name"""
        return Profile.query.filter_by(name=name).first()
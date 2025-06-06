from flask import Blueprint, request, jsonify
from models import Profile, db
import logging

logger = logging.getLogger("DiscoveryAPI.Profiles")

profiles_bp = Blueprint('profiles', __name__)

@profiles_bp.route('/profiles', methods=['GET'])
def get_profiles():
    """Get all profiles"""
    try:
        profiles = Profile.query.filter_by(is_active=True).all()
        return jsonify({
            "profiles": [profile.to_dict() for profile in profiles],
            "total": len(profiles)
        })
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles', methods=['POST'])
def create_profile():
    """Create new profile"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name'):
            return jsonify({"error": "Profile name is required"}), 400

        # Check if profile name already exists
        existing = Profile.query.filter_by(name=data['name']).first()
        if existing:
            return jsonify({"error": "Profile name already exists"}), 409

        profile = Profile(
            name=data['name'],
            description=data.get('description', ''),
            node_count=data.get('node_count', 1),
            cpu_requirement=data.get('cpu_requirement', 1.0),
            memory_requirement=data.get('memory_requirement', 2.0),
            gpu_required=data.get('gpu_required', False),
            max_cpu_usage=data.get('max_cpu_usage', 60),
            max_memory_usage=data.get('max_memory_usage', 60),
            max_active_containers=data.get('max_active_containers', 5)
        )

        db.session.add(profile)
        db.session.commit()

        logger.info(f"Created profile: {profile.name}")
        return jsonify({
            "message": "Profile created successfully",
            "profile": profile.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating profile: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles/<int:profile_id>', methods=['GET'])
def get_profile(profile_id):
    """Get specific profile"""
    try:
        profile = Profile.query.get(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404

        return jsonify({"profile": profile.to_dict()})
    except Exception as e:
        logger.error(f"Error getting profile {profile_id}: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles/<int:profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """Update profile"""
    try:
        profile = Profile.query.get(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404

        data = request.get_json()

        # Update fields if provided
        if 'name' in data:
            # Check if new name conflicts with existing profile
            existing = Profile.query.filter_by(name=data['name']).first()
            if existing and existing.id != profile_id:
                return jsonify({"error": "Profile name already exists"}), 409
            profile.name = data['name']

        if 'description' in data:
            profile.description = data['description']
        if 'node_count' in data:
            profile.node_count = data['node_count']
        if 'cpu_requirement' in data:
            profile.cpu_requirement = data['cpu_requirement']
        if 'memory_requirement' in data:
            profile.memory_requirement = data['memory_requirement']
        if 'gpu_required' in data:
            profile.gpu_required = data['gpu_required']
        if 'max_cpu_usage' in data:
            profile.max_cpu_usage = data['max_cpu_usage']
        if 'max_memory_usage' in data:
            profile.max_memory_usage = data['max_memory_usage']
        if 'max_active_containers' in data:
            profile.max_active_containers = data['max_active_containers']
        if 'is_active' in data:
            profile.is_active = data['is_active']

        db.session.commit()

        logger.info(f"Updated profile: {profile.name}")
        return jsonify({
            "message": "Profile updated successfully",
            "profile": profile.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile {profile_id}: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles/<int:profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    """Delete profile (soft delete)"""
    try:
        profile = Profile.query.get(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404

        # Soft delete - just mark as inactive
        profile.is_active = False
        db.session.commit()

        logger.info(f"Deleted profile: {profile.name}")
        return jsonify({"message": "Profile deleted successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting profile {profile_id}: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles/<int:profile_id>/compatible-nodes', methods=['GET'])
def get_compatible_nodes(profile_id):
    """Get nodes compatible with profile requirements"""
    try:
        from redis_utils import redis_manager
        from load_balancer import load_balancer

        profile = Profile.query.get(profile_id)
        if not profile:
            return jsonify({"error": "Profile not found"}), 404

        # Get all available nodes
        nodes = redis_manager.get_all_nodes(filtered=True)

        # Filter nodes that meet profile requirements
        compatible_nodes = []
        for node in nodes:
            if load_balancer._node_meets_profile_requirements(node, profile):
                node["load_score"] = load_balancer.calculate_node_score(node)
                compatible_nodes.append(node)

        # Sort by load score
        compatible_nodes.sort(key=lambda x: x["load_score"])

        return jsonify({
            "profile": profile.to_dict(),
            "total_compatible_nodes": len(compatible_nodes),
            "compatible_nodes": compatible_nodes,
            "can_fulfill_request": len(compatible_nodes) >= profile.node_count,
            "requirements_check": {
                "cpu_requirement": f">= {profile.cpu_requirement} cores",
                "memory_requirement": f">= {profile.memory_requirement} GB",
                "gpu_required": profile.gpu_required,
                "max_cpu_usage": f"< {profile.max_cpu_usage}%",
                "max_memory_usage": f"< {profile.max_memory_usage}%",
                "max_active_containers": f"< {profile.max_active_containers}"
            }
        })

    except Exception as e:
        logger.error(f"Error getting compatible nodes for profile {profile_id}: {e}")
        return jsonify({"error": str(e)}), 500

@profiles_bp.route('/profiles/default-profiles', methods=['POST'])
def create_default_profiles():
    """Create default profiles for common use cases"""
    try:
        default_profiles = [
            {
                "name": "Single Node - Light",
                "description": "Single node dengan resource minimal untuk development",
                "node_count": 1,
                "cpu_requirement": 1.0,
                "memory_requirement": 2.0,
                "gpu_required": False,
                "max_cpu_usage": 70,
                "max_memory_usage": 70,
                "max_active_containers": 3
            },
            {
                "name": "Single Node - Standard",
                "description": "Single node dengan resource standard untuk data science",
                "node_count": 1,
                "cpu_requirement": 2.0,
                "memory_requirement": 4.0,
                "gpu_required": False,
                "max_cpu_usage": 60,
                "max_memory_usage": 60,
                "max_active_containers": 5
            },
            {
                "name": "Single Node - GPU",
                "description": "Single node dengan GPU untuk machine learning",
                "node_count": 1,
                "cpu_requirement": 4.0,
                "memory_requirement": 8.0,
                "gpu_required": True,
                "max_cpu_usage": 50,
                "max_memory_usage": 50,
                "max_active_containers": 2
            },
            {
                "name": "Multi Node - Distributed",
                "description": "Multiple nodes untuk distributed computing",
                "node_count": 3,
                "cpu_requirement": 2.0,
                "memory_requirement": 4.0,
                "gpu_required": False,
                "max_cpu_usage": 60,
                "max_memory_usage": 60,
                "max_active_containers": 3
            },
            {
                "name": "Multi Node - High Performance",
                "description": "Multiple high-performance nodes untuk heavy workload",
                "node_count": 5,
                "cpu_requirement": 4.0,
                "memory_requirement": 8.0,
                "gpu_required": False,
                "max_cpu_usage": 50,
                "max_memory_usage": 50,
                "max_active_containers": 2
            }
        ]

        created_profiles = []
        for profile_data in default_profiles:
            # Check if profile already exists
            existing = Profile.query.filter_by(name=profile_data['name']).first()
            if not existing:
                profile = Profile(**profile_data)
                db.session.add(profile)
                created_profiles.append(profile_data['name'])

        db.session.commit()

        return jsonify({
            "message": f"Created {len(created_profiles)} default profiles",
            "created_profiles": created_profiles
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating default profiles: {e}")
        return jsonify({"error": str(e)}), 500
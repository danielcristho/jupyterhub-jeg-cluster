from flask import Blueprint, jsonify, request
from services.profile_service import ProfileService
from models import NodeSelection
import logging

logger = logging.getLogger(__name__)

# Create blueprint
profile_bp = Blueprint('profiles', __name__)

@profile_bp.route("/profiles", methods=["GET"])
def get_profiles():
    """Get all profiles"""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    profiles = ProfileService.get_all_profiles(active_only=active_only)

    return jsonify({
        "total": len(profiles),
        "profiles": [p.to_dict() for p in profiles]
    })

@profile_bp.route("/profiles", methods=["POST"])
def create_profile():
    """Create a new profile"""
    try:
        data = request.get_json()
        profile = ProfileService.create_profile(data)
        return jsonify({
            "status": "ok",
            "profile": profile.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        return jsonify({"error": "Internal error"}), 500

@profile_bp.route("/profiles/<int:profile_id>", methods=["GET"])
def get_profile(profile_id):
    """Get a specific profile"""
    profile = ProfileService.get_profile(profile_id)
    if profile:
        return jsonify(profile.to_dict())
    else:
        return jsonify({"error": "Profile not found"}), 404

@profile_bp.route("/profiles/<int:profile_id>", methods=["PUT"])
def update_profile(profile_id):
    """Update a profile"""
    try:
        data = request.get_json()
        profile = ProfileService.update_profile(profile_id, data)
        return jsonify({
            "status": "ok",
            "profile": profile.to_dict()
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({"error": "Internal error"}), 500

@profile_bp.route("/profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    """Delete a profile (soft delete)"""
    success = ProfileService.delete_profile(profile_id)
    if success:
        return jsonify({"status": "ok", "message": "Profile deleted"})
    else:
        return jsonify({"error": "Profile not found"}), 404

@profile_bp.route("/profiles/suitable", methods=["POST"])
def get_suitable_profiles():
    """Get profiles suitable for given requirements"""
    data = request.get_json()

    cpu = data.get('cpu')
    ram = data.get('ram')
    gpu = data.get('gpu', False)

    profiles = ProfileService.get_suitable_profiles_for_requirements(
        cpu=cpu, ram=ram, gpu=gpu
    )

    return jsonify({
        "total": len(profiles),
        "profiles": [p.to_dict() for p in profiles]
    })

@profile_bp.route("/profiles/<int:profile_id>/selections")
def get_profile_selections(profile_id):
    """Get selection history for a profile"""
    # Get query parameters
    limit = request.args.get('limit', 50, type=int)

    profile = ProfileService.get_profile(profile_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    # Get recent selections
    selections = NodeSelection.query.filter_by(
        profile_id=profile_id
    ).order_by(
        NodeSelection.created_at.desc()
    ).limit(limit).all()

    return jsonify({
        "profile": profile.to_dict(),
        "selections": [s.to_dict() for s in selections],
        "total": len(selections)
    })

@profile_bp.route("/profiles/initialize-defaults", methods=["POST"])
def initialize_defaults():
    """Initialize default profiles"""
    try:
        ProfileService.create_default_profiles()
        return jsonify({
            "status": "ok",
            "message": "Default profiles initialized"
        })
    except Exception as e:
        logger.error(f"Error initializing defaults: {e}")
        return jsonify({"error": str(e)}), 500
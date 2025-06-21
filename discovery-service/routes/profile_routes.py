from flask import Blueprint, jsonify, request
from services.profile_service import ProfileService
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
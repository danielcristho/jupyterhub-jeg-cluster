from flask import Blueprint, request, jsonify
from models import NodeAllocation, UserSession, Profile, db
from redis_utils import redis_manager
from load_balancer import load_balancer
import logging
import time
import json
from datetime import datetime

logger = logging.getLogger("DiscoveryAPI.Allocations")

allocations_bp = Blueprint('allocations', __name__)

@allocations_bp.route('/allocate-nodes', methods=['POST'])
def allocate_nodes():
    """
    Allocate nodes based on profile requirements
    Expected payload: {
        "session_id": "session_123",
        "user_id": "user_456",
        "profile_id": 1
    }
    """
    try:
        data = request.get_json()

        # Validate required fields
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        profile_id = data.get('profile_id')

        if not all([session_id, user_id, profile_id]):
            return jsonify({
                "error": "session_id, user_id, and profile_id are required"
            }), 400

        # Check if Redis is available
        if not redis_manager.is_connected():
            return jsonify({"error": "Redis not available"}), 500

        # Get profile
        profile = Profile.query.get(profile_id)
        if not profile or not profile.is_active:
            return jsonify({"error": "Profile not found or inactive"}), 404

        # Check if session already exists and is active
        existing_session = UserSession.query.filter_by(
            session_id=session_id,
            status='running'
        ).first()

        if existing_session:
            # Return existing allocations
            allocations = NodeAllocation.query.filter_by(
                session_id=session_id,
                status='allocated'
            ).all()

            return jsonify({
                "message": "Session already exists",
                "session": existing_session.to_dict(),
                "allocations": [alloc.to_dict() for alloc in allocations],
                "total_allocated_nodes": len(allocations)
            })

        # Get available nodes
        nodes = redis_manager.get_all_nodes(filtered=True)
        if not nodes:
            return jsonify({"error": "No nodes available"}), 404

        # Allocate nodes using load balancer
        try:
            allocations = load_balancer.allocate_nodes_for_session(
                session_id, user_id, profile_id, nodes
            )

            if not allocations:
                return jsonify({
                    "error": "No suitable nodes found for profile requirements"
                }), 404

            return jsonify({
                "message": "Nodes allocated successfully",
                "session_id": session_id,
                "profile": profile.to_dict(),
                "allocations": [alloc.to_dict() for alloc in allocations],
                "total_allocated_nodes": len(allocations),
                "requested_nodes": profile.node_count,
                "allocation_timestamp": int(time.time())
            }), 201

        except ValueError as e:
            return jsonify({"error": str(e)}), 404
        except Exception as e:
            logger.error(f"Error during node allocation: {e}")
            return jsonify({"error": f"Allocation failed: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Error in allocate_nodes: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/deallocate-nodes', methods=['POST'])
def deallocate_nodes():
    """
    Deallocate nodes for a session
    Expected payload: {
        "session_id": "session_123"
    }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        # Check if session exists
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        # Deallocate nodes
        success = load_balancer.deallocate_session_nodes(session_id)

        if success:
            return jsonify({
                "message": "Nodes deallocated successfully",
                "session_id": session_id,
                "deallocation_timestamp": int(time.time())
            })
        else:
            return jsonify({"error": "Failed to deallocate nodes"}), 500

    except Exception as e:
        logger.error(f"Error in deallocate_nodes: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/sessions/<session_id>/allocations', methods=['GET'])
def get_session_allocations(session_id):
    """Get all allocations for a specific session"""
    try:
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        allocations = NodeAllocation.query.filter_by(session_id=session_id).all()

        return jsonify({
            "session": session.to_dict(),
            "allocations": [alloc.to_dict() for alloc in allocations],
            "total_allocations": len(allocations)
        })

    except Exception as e:
        logger.error(f"Error getting session allocations: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/users/<user_id>/sessions', methods=['GET'])
def get_user_sessions(user_id):
    """Get all sessions for a specific user"""
    try:
        sessions = UserSession.query.filter_by(user_id=user_id).all()

        sessions_data = []
        for session in sessions:
            session_dict = session.to_dict()
            # Add allocation count
            allocation_count = NodeAllocation.query.filter_by(
                session_id=session.session_id
            ).count()
            session_dict['allocation_count'] = allocation_count
            sessions_data.append(session_dict)

        return jsonify({
            "user_id": user_id,
            "sessions": sessions_data,
            "total_sessions": len(sessions_data)
        })

    except Exception as e:
        logger.error(f"Error getting user sessions: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/allocations', methods=['GET'])
def get_all_allocations():
    """Get all allocations with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        profile_id = request.args.get('profile_id')

        # Build query
        query = NodeAllocation.query

        if status:
            query = query.filter(NodeAllocation.status == status)
        if user_id:
            query = query.filter(NodeAllocation.user_id == user_id)
        if profile_id:
            query = query.filter(NodeAllocation.profile_id == profile_id)

        # Order by creation time (newest first)
        allocations = query.order_by(NodeAllocation.created_at.desc()).all()

        return jsonify({
            "allocations": [alloc.to_dict() for alloc in allocations],
            "total_allocations": len(allocations),
            "filters": {
                "status": status,
                "user_id": user_id,
                "profile_id": profile_id
            }
        })

    except Exception as e:
        logger.error(f"Error getting allocations: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/sessions', methods=['GET'])
def get_all_sessions():
    """Get all user sessions with optional filtering"""
    try:
        # Get query parameters
        status = request.args.get('status')
        user_id = request.args.get('user_id')
        profile_id = request.args.get('profile_id')

        # Build query
        query = UserSession.query

        if status:
            query = query.filter(UserSession.status == status)
        if user_id:
            query = query.filter(UserSession.user_id == user_id)
        if profile_id:
            query = query.filter(UserSession.profile_id == profile_id)

        # Order by creation time (newest first)
        sessions = query.order_by(UserSession.created_at.desc()).all()

        sessions_data = []
        for session in sessions:
            session_dict = session.to_dict()
            # Add allocation count
            allocation_count = NodeAllocation.query.filter_by(
                session_id=session.session_id
            ).count()
            session_dict['allocation_count'] = allocation_count
            sessions_data.append(session_dict)

        return jsonify({
            "sessions": sessions_data,
            "total_sessions": len(sessions_data),
            "filters": {
                "status": status,
                "user_id": user_id,
                "profile_id": profile_id
            }
        })

    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        return jsonify({"error": str(e)}), 500

@allocations_bp.route('/allocations/<int:allocation_id>/update-status', methods=['PUT'])
def update_allocation_status(allocation_id):
    """Update allocation status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        container_id = data.get('container_id')
        port = data.get('port')
        extra_data = data.get('extra_data')  # Changed from metadata to extra_data

        if not new_status:
            return jsonify({"error": "status is required"}), 400

        allocation = NodeAllocation.query.get(allocation_id)
        if not allocation:
            return jsonify({"error": "Allocation not found"}), 404

        # Update allocation
        allocation.status = new_status
        if container_id:
            allocation.container_id = container_id
        if port:
            allocation.port = port
        if extra_data:
            allocation.extra_data = json.dumps(extra_data)  # Changed from metadata to extra_data

        # Set timestamps based on status
        if new_status == 'running' and not allocation.started_at:
            allocation.started_at = datetime.utcnow()
        elif new_status in ['stopped', 'failed']:
            allocation.stopped_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            "message": "Allocation status updated",
            "allocation": allocation.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating allocation status: {e}")
        return jsonify({"error": str(e)}), 500
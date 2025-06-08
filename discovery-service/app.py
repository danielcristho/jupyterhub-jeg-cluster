from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
import logging
import os

# Import configuration
from config import Config

# Import models and database
from models import db

# Import blueprints
from routes.node_routes import node_bp
from routes.profile_routes import profile_bp

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DiscoveryAPI")

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions
    CORS(app, origins="*")
    db.init_app(app)
    Migrate(app, db)

    # Register blueprints
    app.register_blueprint(node_bp, url_prefix='')
    app.register_blueprint(profile_bp, url_prefix='')

    # Health check route
    @app.route("/health-check")
    def health_check():
        from services.redis_service import RedisService
        redis_service = RedisService()

        return jsonify({
            "status": "ok",
            "message": "Hello, from [DiscoveryAPI]",
            "database": {
                "postgres": "connected" if db.engine else "disconnected",
                "redis": "connected" if redis_service.is_connected() else "disconnected"
            },
            "config": {
                "redis_host": Config.REDIS_HOST,
                "redis_port": Config.REDIS_PORT,
                "postgres_host": Config.POSTGRES_HOST,
                "postgres_port": Config.POSTGRES_PORT
            }
        }), 200

    # Debug routes (remove in production)
    @app.route("/debug-redis")
    def debug_redis():
        """Debug endpoint to check Redis status"""
        from services.redis_service import RedisService
        redis_service = RedisService()

        if not redis_service.is_connected():
            return jsonify({"error": "Redis not available"}), 500

        try:
            all_keys = redis_service.client.keys("*")
            node_keys = redis_service.get_all_node_keys()

            debug_info = {
                "redis_connected": True,
                "total_keys": len(all_keys),
                "node_keys": node_keys,
                "nodes_data": redis_service.get_all_nodes_data()
            }

            return jsonify(debug_info)
        except Exception as e:
            return jsonify({"error": f"Redis debug error: {str(e)}"}), 500

    # Initialize database and default data
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()

        # Initialize default profiles
        from services.profile_service import ProfileService
        try:
            ProfileService.create_default_profiles()
            logger.info("Default profiles initialized")
        except Exception as e:
            logger.error(f"Error initializing default profiles: {e}")

    return app

def run_periodic_tasks(app):
    """Run periodic maintenance tasks"""
    import threading
    import time

    def cleanup_inactive_nodes():
        with app.app_context():
            from services.node_service import NodeService
            from services.redis_service import RedisService

            redis_service = RedisService()
            node_service = NodeService(redis_service)

            while True:
                try:
                    node_service.mark_nodes_inactive()
                    logger.info("Cleaned up inactive nodes")
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")

                # Run every 5 minutes
                time.sleep(300)

    # Start cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_inactive_nodes, daemon=True)
    cleanup_thread.start()

if __name__ == '__main__':
    app = create_app()

    # Start periodic tasks
    run_periodic_tasks(app)

    # Run the application
    app.run(debug=True, host='0.0.0.0', port=15002)
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
import logging
import os

# Import configurations and models
from config import config
from models import db

# Import route blueprints
from routes.profiles import profiles_bp
from routes.allocations import allocations_bp
from routes.nodes import nodes_bp

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Enable CORS
    CORS(app, origins="*")

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DiscoveryAPI")

    # Register blueprints
    app.register_blueprint(profiles_bp, url_prefix='/api')
    app.register_blueprint(allocations_bp, url_prefix='/api')
    app.register_blueprint(nodes_bp)  # Legacy routes without /api prefix for backward compatibility

    # Create database tables
    with app.app_context():
        db.create_all()

    # ===================== Core Routes ===================== #

    @app.route("/health-check")
    def health_check():
        from redis_utils import redis_manager

        redis_status = "connected" if redis_manager.is_connected() else "disconnected"

        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = "connected"
        except Exception:
            db_status = "disconnected"

        return jsonify({
            "status": "ok",
            "message": "Hello, from [DiscoveryAPI] v2.0",
            "redis_status": redis_status,
            "database_status": db_status,
            "redis_host": app.config['REDIS_HOST'],
            "redis_port": app.config['REDIS_PORT'],
            "database_uri": app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else "hidden",
            "available_endpoints": {
                "legacy_routes": [
                    "/health-check",
                    "/register-node",
                    "/all-nodes",
                    "/available-nodes",
                    "/jupyterhub-nodes",
                    "/balanced-node",
                    "/load-balancer-stats",
                    "/debug-redis",
                    "/node/<hostname>",
                    "/cluster-summary"
                ],
                "new_api_routes": [
                    "/api/profiles",
                    "/api/allocate-nodes",
                    "/api/deallocate-nodes",
                    "/api/sessions",
                    "/api/allocations"
                ]
            }
        }), 200

    # ===================== Error Handlers ===================== #

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host=app.config['API_HOST'],
        port=app.config['API_PORT']
    )
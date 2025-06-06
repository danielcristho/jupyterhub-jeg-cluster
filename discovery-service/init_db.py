#!/usr/bin/env python3
"""
Database initialization and migration script
"""
import os
import sys
from flask_migrate import init, migrate, upgrade
from app import create_app
from models import db, Profile

def init_database():
    """Initialize database with migrations"""
    app = create_app()

    with app.app_context():
        try:
            # Initialize migration repository if it doesn't exist
            if not os.path.exists('migrations'):
                print("Initializing migration repository...")
                init()

            # Create migration
            print("Creating migration...")
            migrate(message='Initial migration')

            # Apply migration
            print("Applying migration...")
            upgrade()

            print("Database initialized successfully!")

        except Exception as e:
            print(f"Error initializing database: {e}")
            return False

    return True

def create_default_profiles():
    """Create default profiles"""
    app = create_app()

    with app.app_context():
        try:
            # Check if profiles already exist
            if Profile.query.count() > 0:
                print("Profiles already exist, skipping creation.")
                return True

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

            print("Creating default profiles...")
            for profile_data in default_profiles:
                profile = Profile(**profile_data)
                db.session.add(profile)

            db.session.commit()
            print(f"Created {len(default_profiles)} default profiles successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"Error creating default profiles: {e}")
            return False

    return True

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            success = init_database()
            if success:
                create_default_profiles()
        elif command == "profiles":
            create_default_profiles()
        else:
            print("Usage: python init_db.py [init|profiles]")
            print("  init     - Initialize database and create default profiles")
            print("  profiles - Create default profiles only")
    else:
        print("Initializing database and creating default profiles...")
        success = init_database()
        if success:
            create_default_profiles()

if __name__ == "__main__":
    main()
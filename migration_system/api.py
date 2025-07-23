from flask import Flask, request, jsonify
from typing import Dict, Any
import logging
from .models import (
    Workload, Migration, MigrationTarget, Credentials, 
    Storage, MountPoint, CloudType, MigrationState
)
from .persistence import WorkloadManager, MigrationManager, DuplicateIPError, ObjectNotFoundError

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


workload_manager = WorkloadManager()
migration_manager = MigrationManager()


def handle_error(e: Exception) -> tuple:
    """Handle API errors consistently."""
    if isinstance(e, DuplicateIPError):
        return jsonify({"error": str(e)}), 409
    elif isinstance(e, ObjectNotFoundError):
        return jsonify({"error": str(e)}), 404
    elif isinstance(e, ValueError):
        return jsonify({"error": str(e)}), 400
    else:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/workloads', methods=['POST'])
def create_workload():
    """Create a new workload."""
    try:
        data = request.get_json()
        
        # Create credentials
        creds = Credentials.from_dict(data['credentials'])
        
        # Create storage with mount points
        storage = Storage()
        for mp_data in data.get('storage', {}).get('mount_points', []):
            storage.add_mount_point(MountPoint.from_dict(mp_data))
        
        # Create workload
        workload = Workload(
            _ip=data['ip'],
            credentials=creds,
            storage=storage
        )
        
        created_workload = workload_manager.create_workload(workload)
        return jsonify(created_workload.to_dict()), 201
    
    except Exception as e:
        return handle_error(e)


@app.route('/workloads/<ip>', methods=['GET'])
def get_workload(ip: str):
    """Get workload by IP."""
    try:
        workload = workload_manager.read_workload(ip)
        return jsonify(workload.to_dict())
    except Exception as e:
        return handle_error(e)


@app.route('/workloads', methods=['GET'])
def list_workloads():
    """List all workloads."""
    try:
        workloads = workload_manager.list_all_workloads()
        return jsonify([w.to_dict() for w in workloads])
    except Exception as e:
        return handle_error(e)


@app.route('/workloads/<ip>', methods=['PUT'])
def update_workload(ip: str):
    """Update workload (IP cannot be changed)."""
    try:

        existing_workload = workload_manager.read_workload(ip)
        
        data = request.get_json()
        

        if data.get('ip') and data['ip'] != ip:
            return jsonify({"error": "IP address cannot be modified"}), 400
        
        if 'credentials' in data:
            existing_workload.credentials = Credentials.from_dict(data['credentials'])
        
        if 'storage' in data:
            storage = Storage()
            for mp_data in data['storage'].get('mount_points', []):
                storage.add_mount_point(MountPoint.from_dict(mp_data))
            existing_workload.storage = storage
        
        updated_workload = workload_manager.update_workload(existing_workload)
        return jsonify(updated_workload.to_dict())
    
    except Exception as e:
        return handle_error(e)


@app.route('/workloads/<ip>', methods=['DELETE'])
def delete_workload(ip: str):
    """Delete workload."""
    try:
        workload_manager.delete_workload(ip)
        return '', 204
    except Exception as e:
        return handle_error(e)


@app.route('/migrations', methods=['POST'])
def create_migration():
    """Create a new migration."""
    try:
        data = request.get_json()
        
        selected_mps = [MountPoint.from_dict(mp) for mp in data['selected_mount_points']]
        
        source = Workload.from_dict(data['source'])
        
        target = MigrationTarget.from_dict(data['migration_target'])
        
        migration = Migration(
            selected_mount_points=selected_mps,
            source=source,
            migration_target=target
        )
        
        created_migration = migration_manager.create_migration(migration)
        return jsonify(created_migration.to_dict()), 201
    
    except Exception as e:
        return handle_error(e)


@app.route('/migrations/<migration_id>', methods=['GET'])
def get_migration(migration_id: str):
    """Get migration by ID."""
    try:
        migration = migration_manager.read_migration(migration_id)
        return jsonify(migration.to_dict())
    except Exception as e:
        return handle_error(e)


@app.route('/migrations', methods=['GET'])
def list_migrations():
    """List all migrations."""
    try:
        migrations = migration_manager.list_all_migrations()
        return jsonify([m.to_dict() for m in migrations])
    except Exception as e:
        return handle_error(e)


@app.route('/migrations/<migration_id>', methods=['PUT'])
def update_migration(migration_id: str):
    """Update migration."""
    try:
        existing_migration = migration_manager.read_migration(migration_id)
        
        data = request.get_json()
        
        if existing_migration.migration_state in [MigrationState.RUNNING, MigrationState.SUCCESS]:
            return jsonify({"error": "Cannot modify running or completed migration"}), 400
        
        if 'selected_mount_points' in data:
            existing_migration.selected_mount_points = [
                MountPoint.from_dict(mp) for mp in data['selected_mount_points']
            ]
        
        c_drive_in_source = any(
            mp.mount_point_name.lower() in ["c:\\", "c:/", "c:"] 
            for mp in existing_migration.source.storage.mount_points
        )
        c_drive_selected = any(
            mp.mount_point_name.lower() in ["c:\\", "c:/", "c:"]
            for mp in existing_migration.selected_mount_points
        )
        
        if c_drive_in_source and not c_drive_selected:
            return jsonify({"error": "C:\\ drive must be selected for migration"}), 400
        
        updated_migration = migration_manager.update_migration(existing_migration)
        return jsonify(updated_migration.to_dict())
    
    except Exception as e:
        return handle_error(e)


@app.route('/migrations/<migration_id>', methods=['DELETE'])
def delete_migration(migration_id: str):
    """Delete migration."""
    try:
        migration_manager.delete_migration(migration_id)
        return '', 204
    except Exception as e:
        return handle_error(e)


@app.route('/migrations/<migration_id>/start', methods=['POST'])
def start_migration(migration_id: str):
    """Start migration execution."""
    try:
        migration = migration_manager.read_migration(migration_id)
        
        if migration.migration_state == MigrationState.RUNNING:
            return jsonify({"error": "Migration is already running"}), 400
        
        sleep_minutes = request.get_json().get('sleep_minutes', 0.1) if request.get_json() else 0.1
        
        migration.run(sleep_minutes)
        updated_migration = migration_manager.update_migration(migration)
        
        return jsonify(updated_migration.to_dict())
    
    except Exception as e:
        return handle_error(e)


@app.route('/migrations/<migration_id>/status', methods=['GET'])
def get_migration_status(migration_id: str):
    """Get migration execution status."""
    try:
        migration = migration_manager.read_migration(migration_id)
        return jsonify({
            "migration_id": migration_id,
            "state": migration.migration_state.value,
            "finished": migration.migration_state in [MigrationState.SUCCESS, MigrationState.ERROR]
        })
    except Exception as e:
        return handle_error(e)


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


import json
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Type, TypeVar, Union
from .models import Workload, Migration, MigrationTarget

T = TypeVar('T')


class PersistenceError(Exception):
    """Base exception for persistence operations."""
    pass


class ObjectNotFoundError(PersistenceError):
    """Exception raised when object is not found."""
    pass


class DuplicateIPError(PersistenceError):
    """Exception raised when trying to create workload with duplicate IP."""
    pass


class BasePersistenceManager:
    """Base class for persistence managers."""
    
    def __init__(self, storage_dir: str = "migration_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, object_type: str, object_id: str) -> Path:
        """Get file path for object storage."""
        return self.storage_dir / f"{object_type}_{object_id}.json"
    
    def create(self, obj: T, object_id: str, object_type: str) -> T:
        """Create a new object."""
        file_path = self._get_file_path(object_type, object_id)
        if file_path.exists():
            raise PersistenceError(f"Object {object_id} already exists")
        
        with open(file_path, 'w') as f:
            json.dump(obj.to_dict(), f, indent=2)
        return obj
    
    def read(self, object_id: str, object_type: str, cls: Type[T]) -> T:
        """Read an object by ID."""
        file_path = self._get_file_path(object_type, object_id)
        if not file_path.exists():
            raise ObjectNotFoundError(f"Object {object_id} not found")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def update(self, obj: T, object_id: str, object_type: str) -> T:
        """Update an existing object."""
        file_path = self._get_file_path(object_type, object_id)
        if not file_path.exists():
            raise ObjectNotFoundError(f"Object {object_id} not found")
        
        with open(file_path, 'w') as f:
            json.dump(obj.to_dict(), f, indent=2)
        return obj
    
    def delete(self, object_id: str, object_type: str) -> None:
        """Delete an object by ID."""
        file_path = self._get_file_path(object_type, object_id)
        if not file_path.exists():
            raise ObjectNotFoundError(f"Object {object_id} not found")
        file_path.unlink()
    
    def list_all(self, object_type: str, cls: Type[T]) -> List[T]:
        """List all objects of a specific type."""
        pattern = f"{object_type}_*.json"
        objects = []
        for file_path in self.storage_dir.glob(pattern):
            with open(file_path, 'r') as f:
                data = json.load(f)
            objects.append(cls.from_dict(data))
        return objects


class WorkloadManager(BasePersistenceManager):
    """Manager for Workload objects."""
    
    def create_workload(self, workload: Workload) -> Workload:
        """Create a new workload, ensuring IP uniqueness."""
        existing_workloads = self.list_all_workloads()
        for existing in existing_workloads:
            if existing.ip == workload.ip:
                raise DuplicateIPError(f"Workload with IP {workload.ip} already exists")
        
        return self.create(workload, workload.ip, "workload")
    
    def read_workload(self, ip: str) -> Workload:
        """Read workload by IP address."""
        return self.read(ip, "workload", Workload)
    
    def update_workload(self, workload: Workload) -> Workload:
        """Update existing workload."""
        return self.update(workload, workload.ip, "workload")
    
    def delete_workload(self, ip: str) -> None:
        """Delete workload by IP address."""
        self.delete(ip, "workload")
    
    def list_all_workloads(self) -> List[Workload]:
        """List all workloads."""
        return self.list_all("workload", Workload)


class MigrationManager(BasePersistenceManager):
    """Manager for Migration objects."""
    
    def create_migration(self, migration: Migration) -> Migration:
        """Create a new migration."""
        return self.create(migration, migration.id, "migration")
    
    def read_migration(self, migration_id: str) -> Migration:
        """Read migration by ID."""
        return self.read(migration_id, "migration", Migration)
    
    def update_migration(self, migration: Migration) -> Migration:
        """Update existing migration."""
        return self.update(migration, migration.id, "migration")
    
    def delete_migration(self, migration_id: str) -> None:
        """Delete migration by ID."""
        self.delete(migration_id, "migration")
    
    def list_all_migrations(self) -> List[Migration]:
        """List all migrations."""
        return self.list_all("migration", Migration)

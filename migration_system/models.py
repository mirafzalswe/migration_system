import json
import time
import threading
from copy import deepcopy
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime


class CloudType(Enum):
    """Allowed cloud types for migration targets."""
    AWS = "aws"
    AZURE = "azure"
    VSPHERE = "vsphere"
    VCLOUD = "vcloud"


class MigrationState(Enum):
    """Migration execution states."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class Credentials:
    """User credentials for system access."""
    username: str
    password: str
    domain: str
    
    def __post_init__(self):
        if not self.username or not self.password:
            raise ValueError("Username and password cannot be None or empty")
    
    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "password": self.password,
            "domain": self.domain
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Credentials':
        return cls(
            username=data["username"],
            password=data["password"],
            domain=data["domain"]
        )


@dataclass
class MountPoint:
    """Storage mount point with size information."""
    mount_point_name: str
    total_size: int
    
    def __post_init__(self):
        if not self.mount_point_name:
            raise ValueError("Mount point name cannot be None or empty")
        if self.total_size < 0:
            raise ValueError("Total size cannot be negative")
    
    def to_dict(self) -> dict:
        return {
            "mount_point_name": self.mount_point_name,
            "total_size": self.total_size
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MountPoint':
        return cls(
            mount_point_name=data["mount_point_name"],
            total_size=data["total_size"]
        )


@dataclass
class Storage:
    """Storage container with multiple mount points."""
    mount_points: List[MountPoint] = field(default_factory=list)
    
    def add_mount_point(self, mount_point: MountPoint):
        """Add a mount point to storage."""
        self.mount_points.append(mount_point)
    
    def get_mount_point(self, name: str) -> Optional[MountPoint]:
        """Get mount point by name."""
        return next((mp for mp in self.mount_points if mp.mount_point_name == name), None)
    
    def to_dict(self) -> dict:
        return {
            "mount_points": [mp.to_dict() for mp in self.mount_points]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Storage':
        storage = cls()
        storage.mount_points = [MountPoint.from_dict(mp) for mp in data["mount_points"]]
        return storage


@dataclass
class Workload:
    """Workload representing a system to be migrated."""
    _ip: str
    credentials: Credentials
    storage: Storage = field(default_factory=Storage)
    _ip_set: bool = field(default=False, init=False)

    def __post_init__(self):
        if not self._ip:
            raise ValueError("IP cannot be None or empty")
        if not self.credentials:
            raise ValueError("Credentials cannot be None")
        self._ip_set = True

    @property
    def ip(self) -> str:
        return self._ip

    @ip.setter
    def ip(self, value: str):
        if self._ip_set:
            raise ValueError("IP address cannot be changed once set")
        if not value:
            raise ValueError("IP cannot be None or empty")
        self._ip = value
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "credentials": self.credentials.to_dict(),
            "storage": self.storage.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Workload':
        workload = cls.__new__(cls)
        workload._ip = data["ip"]
        workload._ip_set = True
        workload.credentials = Credentials.from_dict(data["credentials"])
        workload.storage = Storage.from_dict(data["storage"])
        return workload


@dataclass
class MigrationTarget:
    """Migration target configuration."""
    cloud_type: CloudType
    cloud_credentials: Credentials
    target_vm: Workload
    
    def __post_init__(self):
        if not isinstance(self.cloud_type, CloudType):
            if isinstance(self.cloud_type, str):
                try:
                    self.cloud_type = CloudType(self.cloud_type.lower())
                except ValueError:
                    raise ValueError(f"Invalid cloud type: {self.cloud_type}")
            else:
                raise ValueError("Cloud type must be a CloudType enum value")
    
    def to_dict(self) -> dict:
        return {
            "cloud_type": self.cloud_type.value,
            "cloud_credentials": self.cloud_credentials.to_dict(),
            "target_vm": self.target_vm.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MigrationTarget':
        return cls(
            cloud_type=CloudType(data["cloud_type"]),
            cloud_credentials=Credentials.from_dict(data["cloud_credentials"]),
            target_vm=Workload.from_dict(data["target_vm"])
        )


@dataclass
class Migration:
    """Migration job configuration and execution."""
    selected_mount_points: List[MountPoint]
    source: Workload
    migration_target: MigrationTarget
    migration_state: MigrationState = MigrationState.NOT_STARTED
    id: str = field(default_factory=lambda: str(int(time.time() * 1000)))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __post_init__(self):
        c_drive_in_source = any(
            mp.mount_point_name.lower() in ["c:\\", "c:/", "c:"] 
            for mp in self.source.storage.mount_points
        )
        c_drive_selected = any(
            mp.mount_point_name.lower() in ["c:\\", "c:/", "c:"]
            for mp in self.selected_mount_points
        )
        
        if c_drive_in_source and not c_drive_selected:
            raise ValueError("C:\\ drive must be selected for migration if it exists in source")
    
    def run(self, sleep_minutes: float = 0.1) -> None:
        """
        Execute the migration.
        
        Args:
            sleep_minutes: Duration to sleep (in minutes) to simulate migration
        """
        if self.migration_state == MigrationState.RUNNING:
            raise ValueError("Migration is already running")
        
        def _run_migration():
            try:
                self.migration_state = MigrationState.RUNNING
                
                time.sleep(sleep_minutes * 60)
                
                target_storage = Storage()
                for selected_mp in self.selected_mount_points:
                    source_mp = self.source.storage.get_mount_point(selected_mp.mount_point_name)
                    if source_mp:
                        target_storage.add_mount_point(deepcopy(source_mp))
                
                self.migration_target.target_vm.storage = target_storage
                self.migration_state = MigrationState.SUCCESS
                
            except Exception as e:
                self.migration_state = MigrationState.ERROR
                raise e
        
        migration_thread = threading.Thread(target=_run_migration)
        migration_thread.start()
        migration_thread.join()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "selected_mount_points": [mp.to_dict() for mp in self.selected_mount_points],
            "source": self.source.to_dict(),
            "migration_target": self.migration_target.to_dict(),
            "migration_state": self.migration_state.value,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Migration':
        migration = cls.__new__(cls)
        migration.id = data["id"]
        migration.selected_mount_points = [MountPoint.from_dict(mp) for mp in data["selected_mount_points"]]
        migration.source = Workload.from_dict(data["source"])
        migration.migration_target = MigrationTarget.from_dict(data["migration_target"])
        migration.migration_state = MigrationState(data["migration_state"])
        migration.created_at = data.get("created_at", datetime.now().isoformat())
        return migration
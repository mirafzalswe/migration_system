import pytest
import tempfile
import shutil
from pathlib import Path
from migration_system.models import (
    Credentials, MountPoint, Storage, Workload,
    MigrationTarget, Migration, CloudType
)
from migration_system.persistence import (
    WorkloadManager, MigrationManager,
    DuplicateIPError, ObjectNotFoundError
)


class TestWorkloadManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = WorkloadManager(self.temp_dir)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_create_workload(self):
        creds = Credentials("user", "pass", "domain.com")
        workload = Workload(_ip="192.168.1.1", credentials=creds)

        created = self.manager.create_workload(workload)
        assert created.ip == workload.ip


        file_path = Path(self.temp_dir) / "workload_192.168.1.1.json"
        assert file_path.exists()

    def test_duplicate_ip_error(self):
        creds = Credentials("user", "pass", "domain.com")
        workload1 = Workload(_ip="192.168.1.1", credentials=creds)
        workload2 = Workload(_ip="192.168.1.1", credentials=creds)

        self.manager.create_workload(workload1)

        with pytest.raises(DuplicateIPError):
            self.manager.create_workload(workload2)

    def test_read_workload(self):
        creds = Credentials("user", "pass", "domain.com")
        original = Workload(_ip="192.168.1.1", credentials=creds)

        self.manager.create_workload(original)
        retrieved = self.manager.read_workload("192.168.1.1")

        assert retrieved.ip == original.ip
        assert retrieved.credentials.username == original.credentials.username

    def test_read_nonexistent_workload(self):
        with pytest.raises(ObjectNotFoundError):
            self.manager.read_workload("nonexistent.ip")

    def test_update_workload(self):
        creds1 = Credentials("user1", "pass1", "domain1.com")
        workload1 = Workload(_ip="192.168.1.1", credentials=creds1)
        self.manager.create_workload(workload1)

        creds2 = Credentials("user2", "pass2", "domain2.com")
        workload2 = Workload(_ip="192.168.1.1", credentials=creds2)  

        updated = self.manager.update_workload(workload2)
        assert updated.credentials.username == "user2"


        retrieved = self.manager.read_workload("192.168.1.1")
        assert retrieved.credentials.username == "user2"

    def test_delete_workload(self):
        creds = Credentials("user", "pass", "domain.com")
        workload = Workload(_ip="192.168.1.1", credentials=creds)
        self.manager.create_workload(workload)

        self.manager.delete_workload("192.168.1.1")

        with pytest.raises(ObjectNotFoundError):
            self.manager.read_workload("192.168.1.1")


class TestMigrationManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MigrationManager(self.temp_dir)

        
        self.creds = Credentials("user", "pass", "domain.com")
        self.cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")

        self.source_storage = Storage()
        self.c_drive = MountPoint("C:\\", 1000)
        self.source_storage.add_mount_point(self.c_drive)

        self.source = Workload(_ip="192.168.1.1", credentials=self.creds, storage=self.source_storage)
        self.target_vm = Workload(_ip="192.168.1.100", credentials=self.creds)
        self.target = MigrationTarget(CloudType.AWS, self.cloud_creds, self.target_vm)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir)

    def test_create_migration(self):
        migration = Migration([self.c_drive], self.source, self.target)
        created = self.manager.create_migration(migration)

        assert created.id == migration.id
        assert (Path(self.temp_dir) / f"migration_{migration.id}.json").exists()

    def test_migration_crud_operations(self):

        migration = Migration([self.c_drive], self.source, self.target)
        created = self.manager.create_migration(migration)
        migration_id = created.id


        retrieved = self.manager.read_migration(migration_id)
        assert retrieved.id == migration_id

        new_target_vm = Workload(_ip="192.168.1.200", credentials=self.creds)
        new_target = MigrationTarget(CloudType.AZURE, self.cloud_creds, new_target_vm)
        retrieved.migration_target = new_target

        updated = self.manager.update_migration(retrieved)
        assert updated.migration_target.target_vm.ip == "192.168.1.200"
        assert updated.migration_target.cloud_type == CloudType.AZURE


        self.manager.delete_migration(migration_id)
        with pytest.raises(ObjectNotFoundError):
            self.manager.read_migration(migration_id)

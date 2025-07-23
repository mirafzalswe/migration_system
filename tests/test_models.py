import pytest
import time
from migration_system.models import (
    Credentials, MountPoint, Storage, Workload,
    MigrationTarget, Migration, CloudType, MigrationState
)


class TestCredentials:
    def test_valid_credentials(self):
        creds = Credentials("user", "pass", "domain.com")
        assert creds.username == "user"
        assert creds.password == "pass"
        assert creds.domain == "domain.com"

    def test_invalid_credentials(self):
        with pytest.raises(ValueError):
            Credentials("", "pass", "domain.com")

        with pytest.raises(ValueError):
            Credentials("user", "", "domain.com")

    def test_credentials_serialization(self):
        creds = Credentials("user", "pass", "domain.com")
        data = creds.to_dict()
        restored = Credentials.from_dict(data)
        assert restored.username == creds.username
        assert restored.password == creds.password
        assert restored.domain == creds.domain


class TestMountPoint:
    def test_valid_mount_point(self):
        mp = MountPoint("C:\\", 1000)
        assert mp.mount_point_name == "C:\\"
        assert mp.total_size == 1000

    def test_invalid_mount_point(self):
        with pytest.raises(ValueError):
            MountPoint("", 1000)

        with pytest.raises(ValueError):
            MountPoint("C:\\", -1)

    def test_mount_point_serialization(self):
        mp = MountPoint("C:\\", 1000)
        data = mp.to_dict()
        restored = MountPoint.from_dict(data)
        assert restored.mount_point_name == mp.mount_point_name
        assert restored.total_size == mp.total_size


class TestStorage:
    def test_storage_operations(self):
        storage = Storage()
        mp1 = MountPoint("C:\\", 1000)
        mp2 = MountPoint("D:\\", 2000)

        storage.add_mount_point(mp1)
        storage.add_mount_point(mp2)

        assert len(storage.mount_points) == 2
        assert storage.get_mount_point("C:\\") == mp1
        assert storage.get_mount_point("D:\\") == mp2
        assert storage.get_mount_point("E:\\") is None


class TestWorkload:
    def test_valid_workload(self):
        creds = Credentials("user", "pass", "domain.com")
        workload = Workload(_ip="192.168.1.1", credentials=creds)
        assert workload.ip == "192.168.1.1"
        assert workload.credentials == creds

    def test_invalid_workload(self):
        creds = Credentials("user", "pass", "domain.com")

        with pytest.raises(ValueError):
            Workload(_ip="", credentials=creds)

        with pytest.raises(ValueError):
            Workload(_ip="192.168.1.1", credentials=None)

    def test_ip_immutability(self):
        creds = Credentials("user", "pass", "domain.com")
        workload = Workload(_ip="192.168.1.1", credentials=creds)

        with pytest.raises(ValueError):
            workload.ip = "192.168.1.2"

    def test_workload_serialization(self):
        creds = Credentials("user", "pass", "domain.com")
        storage = Storage()
        storage.add_mount_point(MountPoint("C:\\", 1000))

        workload = Workload(_ip="192.168.1.1", credentials=creds, storage=storage)
        data = workload.to_dict()
        restored = Workload.from_dict(data)

        assert restored.ip == workload.ip
        assert restored.credentials.username == workload.credentials.username
        assert len(restored.storage.mount_points) == 1


class TestMigrationTarget:
    def test_valid_migration_target(self):
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)

        target = MigrationTarget(CloudType.AWS, cloud_creds, target_vm)
        assert target.cloud_type == CloudType.AWS
        assert target.cloud_credentials == cloud_creds
        assert target.target_vm == target_vm

    def test_string_cloud_type_conversion(self):
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)

        target = MigrationTarget("aws", cloud_creds, target_vm)
        assert target.cloud_type == CloudType.AWS

    def test_invalid_cloud_type(self):
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)

        with pytest.raises(ValueError):
            MigrationTarget("invalid_cloud", cloud_creds, target_vm)


class TestMigration:
    def test_valid_migration(self):
        # Setup
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")

        # Source with C: and D: drives
        source_storage = Storage()
        c_drive = MountPoint("C:\\", 1000)
        d_drive = MountPoint("D:\\", 2000)
        source_storage.add_mount_point(c_drive)
        source_storage.add_mount_point(d_drive)
        source = Workload(_ip="192.168.1.1", credentials=creds, storage=source_storage)

        # Target
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)
        target = MigrationTarget(CloudType.AWS, cloud_creds, target_vm)

        # Migration with C: selected (required)
        selected_mps = [c_drive]
        migration = Migration(selected_mps, source, target)

        assert migration.migration_state == MigrationState.NOT_STARTED
        assert len(migration.selected_mount_points) == 1
        assert migration.selected_mount_points[0] == c_drive

    def test_migration_without_c_drive_fails(self):
        # Setup
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")

        # Source with C: and D: drives
        source_storage = Storage()
        c_drive = MountPoint("C:\\", 1000)
        d_drive = MountPoint("D:\\", 2000)
        source_storage.add_mount_point(c_drive)
        source_storage.add_mount_point(d_drive)
        source = Workload(_ip="192.168.1.1", credentials=creds, storage=source_storage)

        # Target
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)
        target = MigrationTarget(CloudType.AWS, cloud_creds, target_vm)

        # Migration without C: selected (should fail)
        selected_mps = [d_drive]

        with pytest.raises(ValueError, match="C:\\\\ drive must be selected"):
            Migration(selected_mps, source, target)

    def test_migration_run(self):
        # Setup
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")

        # Source with C: and D: drives
        source_storage = Storage()
        c_drive = MountPoint("C:\\", 1000)
        d_drive = MountPoint("D:\\", 2000)
        source_storage.add_mount_point(c_drive)
        source_storage.add_mount_point(d_drive)
        source = Workload(_ip="192.168.1.1", credentials=creds, storage=source_storage)

        # Target
        target_vm = Workload(_ip="192.168.1.100", credentials=creds)
        target = MigrationTarget(CloudType.AWS, cloud_creds, target_vm)

        # Migration with both drives selected
        selected_mps = [c_drive, d_drive]
        migration = Migration(selected_mps, source, target)

        # Run migration (very short duration for testing)
        migration.run(sleep_minutes=0.001)  # 0.06 seconds

        assert migration.migration_state == MigrationState.SUCCESS
        # Target should have both selected mount points
        assert len(migration.migration_target.target_vm.storage.mount_points) == 2

    def test_migration_serialization(self):
        # Setup
        creds = Credentials("user", "pass", "domain.com")
        cloud_creds = Credentials("cloud_user", "cloud_pass", "cloud.com")

        source_storage = Storage()
        c_drive = MountPoint("C:\\", 1000)
        source_storage.add_mount_point(c_drive)
        source = Workload(_ip="192.168.1.1", credentials=creds, storage=source_storage)

        target_vm = Workload(_ip="192.168.1.100", credentials=creds)
        target = MigrationTarget(CloudType.AWS, cloud_creds, target_vm)

        migration = Migration([c_drive], source, target)
        data = migration.to_dict()
        restored = Migration.from_dict(data)

        assert restored.id == migration.id
        assert restored.migration_state == migration.migration_state
        assert len(restored.selected_mount_points) == 1
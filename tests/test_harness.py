import requests
import json
import time
import sys


class APITestHarness:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_workload_crud(self):
        """Test workload CRUD operations."""
        print("Testing Workload CRUD operations...")
        
        # Test data
        workload_data = {
            "ip": "192.168.1.1",
            "credentials": {
                "username": "testuser",
                "password": "testpass",
                "domain": "testdomain.com"
            },
            "storage": {
                "mount_points": [
                    {
                        "mount_point_name": "C:\\",
                        "total_size": 1000
                    },
                    {
                        "mount_point_name": "D:\\",
                        "total_size": 2000
                    }
                ]
            }
        }
        
        # Create workload
        response = self.session.post(f"{self.base_url}/workloads", json=workload_data)
        assert response.status_code == 201, f"Create failed: {response.text}"
        print("✓ Workload created successfully")
        
        # Get workload
        response = self.session.get(f"{self.base_url}/workloads/192.168.1.1")
        assert response.status_code == 200, f"Get failed: {response.text}"
        print("✓ Workload retrieved successfully")
        
        # Update workload
        workload_data['credentials']['username'] = 'updateduser'
        response = self.session.put(f"{self.base_url}/workloads/192.168.1.1", json=workload_data)
        assert response.status_code == 200, f"Update failed: {response.text}"
        print("✓ Workload updated successfully")
        
        # Try to update IP (should fail)
        workload_data['ip'] = '192.168.1.2'
        response = self.session.put(f"{self.base_url}/workloads/192.168.1.1", json=workload_data)
        assert response.status_code == 400, f"IP update should fail: {response.text}"
        print("✓ IP update correctly rejected")
        
        # List workloads
        response = self.session.get(f"{self.base_url}/workloads")
        assert response.status_code == 200, f"List failed: {response.text}"
        workloads = response.json()
        assert len(workloads) >= 1, "Should have at least one workload"
        print("✓ Workloads listed successfully")
    
    def test_migration_operations(self):
        """Test migration operations."""
        print("\nTesting Migration operations...")
        
        # Migration data
        migration_data = {
            "selected_mount_points": [
                {
                    "mount_point_name": "C:\\",
                    "total_size": 1000
                }
            ],
            "source": {
                "ip": "192.168.1.1",
                "credentials": {
                    "username": "testuser",
                    "password": "testpass",
                    "domain": "testdomain.com"
                },
                "storage": {
                    "mount_points": [
                        {
                            "mount_point_name": "C:\\",
                            "total_size": 1000
                        }
                    ]
                }
            },
            "migration_target": {
                "cloud_type": "aws",
                "cloud_credentials": {
                    "username": "clouduser",
                    "password": "cloudpass",
                    "domain": "cloud.com"
                },
                "target_vm": {
                    "ip": "192.168.1.100",
                    "credentials": {
                        "username": "targetuser",
                        "password": "targetpass",
                        "domain": "target.com"
                    },
                    "storage": {
                        "mount_points": []
                    }
                }
            }
        }
        
        # Create migration
        response = self.session.post(f"{self.base_url}/migrations", json=migration_data)
        assert response.status_code == 201, f"Migration create failed: {response.text}"
        migration = response.json()
        migration_id = migration['id']
        print("✓ Migration created successfully")
        
        # Get migration status
        response = self.session.get(f"{self.base_url}/migrations/{migration_id}/status")
        assert response.status_code == 200, f"Status check failed: {response.text}"
        status = response.json()
        assert status['state'] == 'not_started', "Migration should be not started"
        print("✓ Migration status retrieved successfully")
        
        # Start migration
        start_data = {"sleep_minutes": 0.01}  # 0.6 seconds for testing
        response = self.session.post(f"{self.base_url}/migrations/{migration_id}/start", json=start_data)
        assert response.status_code == 200, f"Migration start failed: {response.text}"
        print("✓ Migration started successfully")
        
        # Check final status
        response = self.session.get(f"{self.base_url}/migrations/{migration_id}/status")
        assert response.status_code == 200, f"Final status check failed: {response.text}"
        status = response.json()
        assert status['state'] == 'success', f"Migration should be successful, got: {status['state']}"
        assert status['finished'] == True, "Migration should be finished"
        print("✓ Migration completed successfully")
        
        # List migrations
        response = self.session.get(f"{self.base_url}/migrations")
        assert response.status_code == 200, f"List migrations failed: {response.text}"
        migrations = response.json()
        assert len(migrations) >= 1, "Should have at least one migration"
        print("✓ Migrations listed successfully")
    
    def test_error_cases(self):
        """Test error cases."""
        print("\nTesting error cases...")
        
        # Try to create migration without C: drive
        invalid_migration = {
            "selected_mount_points": [
                {
                    "mount_point_name": "D:\\",
                    "total_size": 2000
                }
            ],
            "source": {
                "ip": "192.168.1.1",
                "credentials": {
                    "username": "testuser",
                    "password": "testpass",
                    "domain": "testdomain.com"
                },
                "storage": {
                    "mount_points": [
                        {
                            "mount_point_name": "C:\\",
                            "total_size": 1000
                        },
                        {
                            "mount_point_name": "D:\\",
                            "total_size": 2000
                        }
                    ]
                }
            },
            "migration_target": {
                "cloud_type": "aws",
                "cloud_credentials": {
                    "username": "clouduser",
                    "password": "cloudpass",
                    "domain": "cloud.com"
                },
                "target_vm": {
                    "ip": "192.168.1.100",
                    "credentials": {
                        "username": "targetuser",
                        "password": "targetpass",
                        "domain": "target.com"
                    },
                    "storage": {
                        "mount_points": []
                    }
                }
            }
        }
        
        response = self.session.post(f"{self.base_url}/migrations", json=invalid_migration)
        assert response.status_code == 400, "Should reject migration without C: drive"
        print("✓ Migration without C: drive correctly rejected")
        
        response = self.session.get(f"{self.base_url}/workloads/192.168.1.99")
        assert response.status_code == 404, "Should return 404 for non-existent workload"
        print("✓ Non-existent workload correctly returns 404")
    
    def run_all_tests(self):
        """Run all test cases."""
        print("Starting API Test Harness...")
        print("=" * 50)
        
        try:
            self.test_workload_crud()
            self.test_migration_operations()
            self.test_error_cases()
            
            print("\n" + "=" * 50)
            print("All tests passed! ✓")
            
        except Exception as e:
            print(f"\nTest failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    print("Waiting for server to start...")
    time.sleep(2)
    
    harness = APITestHarness()
    harness.run_all_tests()
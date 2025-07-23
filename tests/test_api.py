import pytest
import json
import tempfile
import shutil
from migration_system.api import app
from migration_system.models import CloudType, MigrationState


@pytest.fixture
def client():
    temp_dir = tempfile.mkdtemp()
    app.config['TESTING'] = True
    app.config['DATA_DIR'] = temp_dir

    from migration_system.persistence import WorkloadManager, MigrationManager
    from migration_system import api
    api.workload_manager = WorkloadManager(temp_dir)
    api.migration_manager = MigrationManager(temp_dir)

    with app.test_client() as client:
        yield client

    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_workload_data():
    return {
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


@pytest.fixture
def sample_migration_data():
    return {
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


class TestWorkloadAPI:
    def test_create_workload(self, client, sample_workload_data):
        response = client.post('/workloads', 
                              data=json.dumps(sample_workload_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['ip'] == sample_workload_data['ip']
    
    def test_create_duplicate_workload(self, client, sample_workload_data):

        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        

        response = client.post('/workloads', 
                              data=json.dumps(sample_workload_data),
                              content_type='application/json')
        
        assert response.status_code == 409
    
    def test_get_workload(self, client, sample_workload_data):

        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        

        response = client.get(f'/workloads/{sample_workload_data["ip"]}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['ip'] == sample_workload_data['ip']
    
    def test_get_nonexistent_workload(self, client):
        response = client.get('/workloads/192.168.1.99')
        assert response.status_code == 404
    
    def test_update_workload(self, client, sample_workload_data):
        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        update_data = sample_workload_data.copy()
        update_data['credentials']['username'] = 'updateduser'
        
        response = client.put(f'/workloads/{sample_workload_data["ip"]}',
                             data=json.dumps(update_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['credentials']['username'] == 'updateduser'
    
    def test_update_workload_ip_forbidden(self, client, sample_workload_data):
  
        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        
     
        update_data = sample_workload_data.copy()
        update_data['ip'] = '192.168.1.2'
        
        response = client.put(f'/workloads/{sample_workload_data["ip"]}',
                             data=json.dumps(update_data),
                             content_type='application/json')
        
        assert response.status_code == 400
    
    def test_delete_workload(self, client, sample_workload_data):

        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        
       
        response = client.delete(f'/workloads/{sample_workload_data["ip"]}')
        assert response.status_code == 204
        
    
        response = client.get(f'/workloads/{sample_workload_data["ip"]}')
        assert response.status_code == 404
    
    def test_list_workloads(self, client, sample_workload_data):

        workload2 = sample_workload_data.copy()
        workload2['ip'] = '192.168.1.2'
        
        client.post('/workloads', 
                   data=json.dumps(sample_workload_data),
                   content_type='application/json')
        client.post('/workloads', 
                   data=json.dumps(workload2),
                   content_type='application/json')
        

        response = client.get('/workloads')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) == 2


class TestMigrationAPI:
    def test_create_migration(self, client, sample_migration_data):
        response = client.post('/migrations',
                              data=json.dumps(sample_migration_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['migration_state'] == 'not_started'
    
    def test_create_migration_without_c_drive(self, client, sample_migration_data):

        sample_migration_data['selected_mount_points'] = [
            {
                "mount_point_name": "D:\\",
                "total_size": 2000
            }
        ]
        
        response = client.post('/migrations',
                              data=json.dumps(sample_migration_data),
                              content_type='application/json')
        
        assert response.status_code == 400
    
    def test_start_migration(self, client, sample_migration_data):

        response = client.post('/migrations',
                              data=json.dumps(sample_migration_data),
                              content_type='application/json')
        
        migration_data = json.loads(response.data)
        migration_id = migration_data['id']
        
      
        start_data = {"sleep_minutes": 0.001}  
        response = client.post(f'/migrations/{migration_id}/start',
                              data=json.dumps(start_data),
                              content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['migration_state'] == 'success'
    
    def test_get_migration_status(self, client, sample_migration_data):

        response = client.post('/migrations',
                              data=json.dumps(sample_migration_data),
                              content_type='application/json')
        
        migration_data = json.loads(response.data)
        migration_id = migration_data['id']
        response = client.get(f'/migrations/{migration_id}/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['migration_id'] == migration_id
        assert data['state'] == 'not_started'
        assert data['finished'] == False

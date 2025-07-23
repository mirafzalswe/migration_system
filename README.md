# Migration System

A comprehensive system for managing workload migrations. This project provides a Flask-based REST API to create, manage, and monitor workload migrations from one environment to another.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [API Endpoints](#api-endpoints)
  - [Workloads](#workloads)
  - [Migrations](#migrations)

## Prerequisites

- Python 3.10 or higher
- `pip` for package management

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mirafzalswe/migration_system
    cd migration-task
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
    *On Windows, use `venv\Scripts\activate`*

3.  **Install the required dependencies:**
    The project uses `Flask` and `pytest`. You can install them directly:
    ```bash
    pip install Flask pytest
    ```

## Running the Application

To start the Flask development server, run the following command from the root directory of the project (`migration-task`):

```bash
python3 -m migration_system.api
```

The API will be available at `http://127.0.0.1:5000`.

## Running Tests

The project uses `pytest` for testing. To run the entire test suite, execute the following command from the root directory (`migration-task`):

```bash
pytest
```

This will discover and run all tests in the `tests/` directory. All tests should pass if the environment is set up correctly.

## API Endpoints

The API provides endpoints for managing workloads and migrations.

### Workloads

#### `POST /workloads`

Create a new workload.

-   **Request Body:**
    ```json
    {
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
    }
    ```

-   **Response (201 Created):** The created workload object.

#### `GET /workloads/<ip>`

Retrieve a workload by its IP address.

-   **Response (200 OK):** The requested workload object.

#### `GET /workloads`

List all existing workloads.

-   **Response (200 OK):** A list of all workload objects.

#### `PUT /workloads/<ip>`

Update an existing workload. The IP address cannot be changed.

-   **Request Body:** Same structure as the `POST` request.
-   **Response (200 OK):** The updated workload object.

#### `DELETE /workloads/<ip>`

Delete a workload by its IP address.

-   **Response (204 No Content):** An empty response indicating success.

### Migrations

#### `POST /migrations`

Create a new migration.

-   **Response (201 Created):** The created migration object.

#### `GET /migrations/<migration_id>`

Retrieve a migration by its ID.

-   **Response (200 OK):** The requested migration object.

#### `POST /migrations/<migration_id>/start`

Start a migration.

-   **Response (200 OK):** The updated migration object with the state set to `RUNNING`.

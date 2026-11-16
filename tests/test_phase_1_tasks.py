from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_task_success(client: TestClient):
    """Test POST /api/v1/projects/{project_id}/tasks with valid payload."""
    project_id = 1
    payload = {
        "title": "Thiết kế database schema",
        "description": "Chi tiết về cấu trúc PostgreSQL",
        "status": "TODO",
        "priority": "HIGH",
        "assignee_id": 2,
    }

    response = client.post(f"/api/v1/projects/{project_id}/tasks", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["project_id"] == project_id
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["status"] == "TODO"
    assert data["priority"] == "HIGH"
    assert data["assignee_id"] == 2
    assert data["created_by"] == 1
    assert "created_at" in data


def test_create_task_validation_errors(client: TestClient):
    """Test validation errors on task creation returning 422 Unprocessable Entity."""
    project_id = 1

    # 1. Empty title (violation of min_length=1)
    response_empty_title = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "", "status": "TODO"},
    )
    assert response_empty_title.status_code == 422

    # 2. Missing title
    response_missing_title = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"description": "Missing title"},
    )
    assert response_missing_title.status_code == 422

    # 3. Invalid status enum
    response_invalid_status = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Valid title", "status": "INVALID_STATUS"},
    )
    assert response_invalid_status.status_code == 422

    # 4. Invalid priority enum
    response_invalid_priority = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Valid title", "priority": "SUPER_HIGH"},
    )
    assert response_invalid_priority.status_code == 422


def test_get_project_tasks_and_filtering(client: TestClient):
    """Test listing tasks of a project with pagination and filter criteria."""
    project_id = 10

    # Seed 3 tasks
    _task1 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task 1", "status": "TODO", "priority": "LOW"},
    ).json()
    task2 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task 2", "status": "IN_PROGRESS", "priority": "HIGH"},
    ).json()
    _task3 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task 3", "status": "TODO", "priority": "HIGH"},
    ).json()

    # 1. List all tasks for project
    response = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert response.status_code == 200
    all_tasks = response.json()
    assert len(all_tasks) == 3

    # 2. Filter by status=TODO
    resp_filter_status = client.get(f"/api/v1/projects/{project_id}/tasks?status=TODO")
    assert resp_filter_status.status_code == 200
    todo_tasks = resp_filter_status.json()
    assert len(todo_tasks) == 2
    assert all(t["status"] == "TODO" for t in todo_tasks)

    # 3. Filter by priority=HIGH
    resp_filter_priority = client.get(f"/api/v1/projects/{project_id}/tasks?priority=HIGH")
    assert resp_filter_priority.status_code == 200
    high_tasks = resp_filter_priority.json()
    assert len(high_tasks) == 2
    assert all(t["priority"] == "HIGH" for t in high_tasks)

    # 4. Pagination (skip=1, limit=1)
    resp_paginated = client.get(f"/api/v1/projects/{project_id}/tasks?skip=1&limit=1")
    assert resp_paginated.status_code == 200
    paginated_tasks = resp_paginated.json()
    assert len(paginated_tasks) == 1
    assert paginated_tasks[0]["id"] == task2["id"]


def test_get_task_by_id(client: TestClient):
    """Test getting a task by ID: 200 for existing ID, 404 for non-existing ID."""
    # Create a task
    created = client.post(
        "/api/v1/projects/5/tasks",
        json={"title": "Test Task", "priority": "MEDIUM"},
    ).json()
    task_id = created["id"]

    # 1. Existing ID
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["id"] == task_id
    assert task_data["title"] == "Test Task"

    # 2. Non-existing ID (9999)
    response_not_found = client.get("/api/v1/tasks/9999")
    assert response_not_found.status_code == 404
    assert response_not_found.json()["detail"] == "Task with id 9999 not found"


def test_update_task(client: TestClient):
    """Test partially updating a task via PATCH /api/v1/tasks/{task_id}."""
    # Create initial task
    created = client.post(
        "/api/v1/projects/1/tasks",
        json={"title": "Tiêu đề ban đầu", "status": "TODO", "priority": "LOW"},
    ).json()
    task_id = created["id"]

    # 1. Update status and title
    patch_payload = {
        "status": "IN_PROGRESS",
        "title": "Tiêu đề mới",
    }
    response = client.patch(f"/api/v1/tasks/{task_id}", json=patch_payload)
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["id"] == task_id
    assert updated_data["title"] == "Tiêu đề mới"
    assert updated_data["status"] == "IN_PROGRESS"
    # Unchanged fields remain preserved
    assert updated_data["priority"] == "LOW"

    # 2. Update non-existing task
    response_not_found = client.patch("/api/v1/tasks/9999", json={"title": "NotFound"})
    assert response_not_found.status_code == 404
    assert response_not_found.json()["detail"] == "Task with id 9999 not found"


def test_delete_task(client: TestClient):
    """Test deleting a task via DELETE /api/v1/tasks/{task_id}."""
    # Create task
    created = client.post(
        "/api/v1/projects/1/tasks",
        json={"title": "Task to delete"},
    ).json()
    task_id = created["id"]

    # 1. Delete task -> 204 No Content
    response = client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 204
    assert response.content == b""

    # 2. Verify task is gone -> 404 Not Found
    response_check = client.get(f"/api/v1/tasks/{task_id}")
    assert response_check.status_code == 404

    # 3. Second DELETE call on the same ID -> 404 Not Found
    response_delete_again = client.delete(f"/api/v1/tasks/{task_id}")
    assert response_delete_again.status_code == 404

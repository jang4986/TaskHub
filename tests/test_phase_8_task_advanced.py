from fastapi.testclient import TestClient

from taskhub.core.enums import ProjectStatus, TaskPriority, TaskStatus


def test_filter_tasks_by_assignee(client: TestClient):
    project_id = 1

    # 1. Create a task assigned to User 1
    resp_u1 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task for User 1", "assignee_id": 1},
    )
    assert resp_u1.status_code == 201

    # 2. Create a task assigned to User 2
    resp_u2 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task for User 2", "assignee_id": 2},
    )
    assert resp_u2.status_code == 201

    # 3. Create an unassigned task
    resp_none = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Unassigned Task", "assignee_id": None},
    )
    assert resp_none.status_code == 201

    # 4. Filter tasks with assignee_id=2
    resp_filter = client.get(f"/api/v1/projects/{project_id}/tasks?assignee_id=2")
    assert resp_filter.status_code == 200
    data = resp_filter.json()
    assert len(data) == 1
    assert data[0]["assignee_id"] == 2
    assert data[0]["title"] == "Task for User 2"
    assert "X-Total-Count" in resp_filter.headers
    assert int(resp_filter.headers["X-Total-Count"]) == 1


def test_combined_filters_and_page_limit(client: TestClient):
    project_id = 1

    # Seed 2 tasks matching status=TODO, priority=HIGH, assignee_id=2
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Match Task 1",
            "status": TaskStatus.TODO.value,
            "priority": TaskPriority.HIGH.value,
            "assignee_id": 2,
        },
    )
    assert resp1.status_code == 201
    task1_id = resp1.json()["id"]

    resp2 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Match Task 2",
            "status": TaskStatus.TODO.value,
            "priority": TaskPriority.HIGH.value,
            "assignee_id": 2,
        },
    )
    assert resp2.status_code == 201
    task2_id = resp2.json()["id"]

    # Seed 1 task that does NOT match (status=DONE)
    resp3 = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Non-matching Task",
            "status": TaskStatus.DONE.value,
            "priority": TaskPriority.HIGH.value,
            "assignee_id": 2,
        },
    )
    assert resp3.status_code == 201

    # Query with combined filters and pagination: page=1&limit=1
    url = f"/api/v1/projects/{project_id}/tasks?status=TODO&priority=HIGH&assignee_id=2"
    resp_p1 = client.get(f"{url}&page=1&limit=1")
    assert resp_p1.status_code == 200
    data_p1 = resp_p1.json()
    assert len(data_p1) == 1
    assert int(resp_p1.headers["X-Total-Count"]) == 2

    # Query page=2&limit=1
    resp_p2 = client.get(f"{url}&page=2&limit=1")
    assert resp_p2.status_code == 200
    data_p2 = resp_p2.json()
    assert len(data_p2) == 1
    assert int(resp_p2.headers["X-Total-Count"]) == 2

    # Ensure page 1 and page 2 returned different tasks
    assert data_p1[0]["id"] != data_p2[0]["id"]
    ids = {data_p1[0]["id"], data_p2[0]["id"]}
    assert ids == {task1_id, task2_id}


def test_assign_stranger_to_task_fails(client: TestClient):
    project_id = 1
    # User 4 (stranger) is not in Workspace 1

    # 1. Creating task with stranger assignee fails (400)
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Invalid Assignee Task", "assignee_id": 4},
    )
    assert resp_create.status_code == 400
    assert "Assignee must be a member of the project's workspace" in resp_create.json()["detail"]

    # 2. Creating a valid task first
    resp_valid = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Valid Task", "assignee_id": 1},
    )
    assert resp_valid.status_code == 201
    task_id = resp_valid.json()["id"]

    # 3. Updating task to stranger assignee fails (400)
    resp_update = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"assignee_id": 4},
    )
    assert resp_update.status_code == 400
    assert "Assignee must be a member of the project's workspace" in resp_update.json()["detail"]


def test_modify_task_in_archived_project_fails(client: TestClient):
    project_id = 1

    # 1. Create a valid task while project is ACTIVE
    resp_task = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Pre-archive Task", "assignee_id": 1},
    )
    assert resp_task.status_code == 201
    task_id = resp_task.json()["id"]

    # 2. Archive the project
    resp_archive = client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": ProjectStatus.ARCHIVED.value},
    )
    assert resp_archive.status_code == 200
    assert resp_archive.json()["status"] == ProjectStatus.ARCHIVED.value

    # 3. Attempting to create task in archived project fails (400)
    resp_create_fail = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task in Archived Project"},
    )
    assert resp_create_fail.status_code == 400
    assert "Cannot modify tasks in an archived project" in resp_create_fail.json()["detail"]

    # 4. Attempting to update task in archived project fails (400)
    resp_update_fail = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Title in Archived Project"},
    )
    assert resp_update_fail.status_code == 400
    assert "Cannot modify tasks in an archived project" in resp_update_fail.json()["detail"]

    # 5. Attempting to delete task in archived project fails (400)
    resp_delete_fail = client.delete(f"/api/v1/tasks/{task_id}")
    assert resp_delete_fail.status_code == 400
    assert "Cannot modify tasks in an archived project" in resp_delete_fail.json()["detail"]

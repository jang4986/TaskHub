from fastapi.testclient import TestClient

from taskhub.core.enums import ProjectStatus, TaskPriority, TaskStatus
from taskhub.main import app


def test_project_crud_archive_and_rbac(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
):
    # 1. Editor (User 5) creates project in Workspace 1 -> 201 Created
    with TestClient(app, headers=editor_headers) as editor_client:
        create_payload = {
            "name": "Editor Project",
            "description": "Created by editor",
        }
        resp_create = editor_client.post("/api/v1/workspaces/1/projects", json=create_payload)
        assert resp_create.status_code == 201
        proj_data = resp_create.json()
        assert proj_data["name"] == "Editor Project"
        assert proj_data["status"] == ProjectStatus.ACTIVE.value
        proj_id = proj_data["id"]

        # 2. Editor updates project status to ARCHIVED -> 200 OK
        resp_archive = editor_client.patch(
            f"/api/v1/projects/{proj_id}",
            json={"status": ProjectStatus.ARCHIVED.value},
        )
        assert resp_archive.status_code == 200
        assert resp_archive.json()["status"] == ProjectStatus.ARCHIVED.value

        # 3. Editor tries to delete project -> 403 Forbidden (Only OWNER can delete)
        resp_editor_del = editor_client.delete(f"/api/v1/projects/{proj_id}")
        assert resp_editor_del.status_code == 403

    # 4. Viewer (User 3) tries to create project -> 403 Forbidden
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_viewer_create = viewer_client.post(
            "/api/v1/workspaces/1/projects",
            json={"name": "Viewer Project"},
        )
        assert resp_viewer_create.status_code == 403

        # Viewer tries to update project -> 403 Forbidden
        resp_viewer_patch = viewer_client.patch(
            f"/api/v1/projects/{proj_id}",
            json={"name": "Hacked Name"},
        )
        assert resp_viewer_patch.status_code == 403

    # 5. Owner (User 1) deletes project -> 204 No Content
    resp_owner_del = client.delete(f"/api/v1/projects/{proj_id}")
    assert resp_owner_del.status_code == 204


def test_task_filtering_pagination_and_assignee_validation(
    client: TestClient,
    editor_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # 1. Create task assigning to Member (User 2, in workspace 1) -> 201 Created
        resp_task = editor_client.post(
            "/api/v1/projects/1/tasks",
            json={
                "title": "Task assigned to user 2",
                "assignee_id": 2,
                "status": TaskStatus.TODO.value,
                "priority": TaskPriority.HIGH.value,
            },
        )
        assert resp_task.status_code == 201
        task_id = resp_task.json()["id"]

        # 2. Try to assign task to Stranger (User 4, NOT in workspace 1) -> 400 Bad Request
        resp_invalid_assignee = editor_client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"assignee_id": 4},
        )
        assert resp_invalid_assignee.status_code == 400
        assert "Assignee must be a member" in resp_invalid_assignee.json()["detail"]

        # Also test on creation with invalid assignee -> 400 Bad Request
        resp_invalid_create = editor_client.post(
            "/api/v1/projects/1/tasks",
            json={
                "title": "Task with stranger assignee",
                "assignee_id": 4,
            },
        )
        assert resp_invalid_create.status_code == 400

        # 3. Create more tasks for pagination testing
        editor_client.post(
            "/api/v1/projects/1/tasks",
            json={"title": "Task 2 for user 2", "assignee_id": 2},
        )
        editor_client.post(
            "/api/v1/projects/1/tasks",
            json={"title": "Task 3 unassigned"},
        )

        # 4. Filter by assignee_id = 2
        resp_filter = editor_client.get("/api/v1/projects/1/tasks?assignee_id=2")
        assert resp_filter.status_code == 200
        data_filtered = resp_filter.json()
        assert len(data_filtered) >= 2
        assert all(t["assignee_id"] == 2 for t in data_filtered)

        # 5. Pagination with page & limit
        resp_p1 = editor_client.get("/api/v1/projects/1/tasks?page=1&limit=2")
        assert resp_p1.status_code == 200
        assert len(resp_p1.json()) <= 2
        assert "X-Total-Count" in resp_p1.headers

        resp_p2 = editor_client.get("/api/v1/projects/1/tasks?page=2&limit=2")
        assert resp_p2.status_code == 200


def test_label_crud_and_task_attachment(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # 1. Editor creates label in Project 1 -> 201 Created
        resp_create = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "Bug", "color": "#FF0000"},
        )
        assert resp_create.status_code == 201
        label1 = resp_create.json()
        assert label1["name"] == "Bug"
        assert label1["color"] == "#FF0000"
        label_id = label1["id"]

        # 2. Duplicate label in same project -> 409 Conflict
        resp_dup = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "Bug", "color": "#00FF00"},
        )
        assert resp_dup.status_code == 409

        # 3. Create a task in Project 1 and attach label
        task_res = editor_client.post(
            "/api/v1/projects/1/tasks",
            json={"title": "Task for label test"},
        )
        task_id = task_res.json()["id"]

        resp_attach = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}")
        assert resp_attach.status_code == 201
        assert resp_attach.json()["id"] == label_id

        # 4. Attach same label again -> 409 Conflict
        resp_attach_dup = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}")
        assert resp_attach_dup.status_code == 409

        # 5. Create a label in Project 5 and try attaching to task in Project 1 -> 400 Bad Request
        resp_l5 = editor_client.post(
            "/api/v1/projects/5/labels",
            json={"name": "Feature", "color": "#00AA00"},
        )
        l5_id = resp_l5.json()["id"]
        resp_cross_attach = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{l5_id}")
        assert resp_cross_attach.status_code == 400
        assert "not belong to the same project" in resp_cross_attach.json()["detail"]

        # 6. Detach label -> 204 No Content
        resp_detach = editor_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}")
        assert resp_detach.status_code == 204

    # 7. Viewer cannot create label -> 403 Forbidden
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_v = viewer_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "Viewer Label", "color": "#112233"},
        )
        assert resp_v.status_code == 403


def test_comment_lifecycle_and_permissions(
    client: TestClient,
    viewer_headers: dict[str, str],
    user2_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # Create a task in Project 1
    task_res = client.post("/api/v1/projects/1/tasks", json={"title": "Task for comments"})
    task_id = task_res.json()["id"]

    # 1. Viewer (User 3) adds comment -> 201 Created (Viewers can comment on tasks they can view)
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_c = viewer_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Viewer's comment"},
        )
        assert resp_c.status_code == 201
        comment_data = resp_c.json()
        assert comment_data["content"] == "Viewer's comment"
        assert comment_data["author_id"] == 3
        assert comment_data["author"] is not None
        assert comment_data["author"]["id"] == 3
        comment_id = comment_data["id"]

    # 2. Stranger (User 4) tries to comment -> 403 Forbidden
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger = stranger_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Stranger trying to comment"},
        )
        assert resp_stranger.status_code == 403

    # 3. List comments
    resp_list = client.get(f"/api/v1/tasks/{task_id}/comments?page=1&limit=10")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1
    assert "X-Total-Count" in resp_list.headers

    # 4. User 2 (not author, not workspace owner) tries to delete viewer's comment -> 403 Forbidden
    with TestClient(app, headers=user2_headers) as user2_client:
        resp_del_unauthorized = user2_client.delete(f"/api/v1/comments/{comment_id}")
        assert resp_del_unauthorized.status_code == 403

    # 5. Viewer deletes their own comment -> 204 No Content
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_del_author = viewer_client.delete(f"/api/v1/comments/{comment_id}")
        assert resp_del_author.status_code == 204

    # 6. Workspace OWNER can delete any comment
    # Create another comment as viewer
    with TestClient(app, headers=viewer_headers) as viewer_client:
        c2 = viewer_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Another comment"},
        ).json()
        c2_id = c2["id"]

    # Owner (User 1) deletes viewer's comment -> 204 No Content
    resp_owner_del = client.delete(f"/api/v1/comments/{c2_id}")
    assert resp_owner_del.status_code == 204


def test_label_edge_cases_and_patch_validation(
    client: TestClient,
    editor_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create a label
        resp = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "UI/UX", "color": "#123456"},
        )
        assert resp.status_code == 201
        label_id = resp.json()["id"]

        # Update label name and color
        resp_update = editor_client.patch(
            f"/api/v1/labels/{label_id}",
            json={"name": "UI/UX Redesign", "color": "#654321"},
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["name"] == "UI/UX Redesign"
        assert resp_update.json()["color"] == "#654321"

        # PATCH with name: null -> 422
        resp_null_name = editor_client.patch(
            f"/api/v1/labels/{label_id}",
            json={"name": None},
        )
        assert resp_null_name.status_code == 422

        # PATCH with color: null -> 422
        resp_null_color = editor_client.patch(
            f"/api/v1/labels/{label_id}",
            json={"color": None},
        )
        assert resp_null_color.status_code == 422

        # Create a task to test detach on unattached label
        t_res = editor_client.post("/api/v1/projects/1/tasks", json={"title": "Task Detach Test"})
        task_id = t_res.json()["id"]

        # Detach label that is not attached -> 404
        resp_detach_not_found = editor_client.delete(f"/api/v1/tasks/{task_id}/labels/{label_id}")
        assert resp_detach_not_found.status_code == 404

        # Delete label -> 204
        resp_delete = editor_client.delete(f"/api/v1/labels/{label_id}")
        assert resp_delete.status_code == 204

        # Deleting already deleted label -> 404
        resp_delete_again = editor_client.delete(f"/api/v1/labels/{label_id}")
        assert resp_delete_again.status_code == 404


def test_assignee_viewer_restriction(
    client: TestClient,
    editor_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # User 3 is VIEWER in Workspace 1
        resp_create = editor_client.post(
            "/api/v1/projects/1/tasks",
            json={"title": "Viewer Assigned Task", "assignee_id": 3},
        )
        assert resp_create.status_code == 400
        assert (
            "cannot be a VIEWER" in resp_create.json()["detail"]
            or "write permissions" in resp_create.json()["detail"]
        )

        # Create valid task then try updating assignee to VIEWER
        t_valid = editor_client.post("/api/v1/projects/1/tasks", json={"title": "Valid Task"})
        task_id = t_valid.json()["id"]

        resp_update = editor_client.patch(
            f"/api/v1/tasks/{task_id}",
            json={"assignee_id": 3},
        )
        assert resp_update.status_code == 400


def test_whitespace_trimming_and_uniqueness(
    client: TestClient,
    editor_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create label with leading/trailing spaces
        resp1 = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "  Refactor  ", "color": "#AABBCC"},
        )
        assert resp1.status_code == 201
        assert resp1.json()["name"] == "Refactor"

        # Create label with different spacing that trims to the same name -> 409 Conflict
        resp2 = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "Refactor  ", "color": "#112233"},
        )
        assert resp2.status_code == 409

        # Comment with only spaces -> 422
        t = editor_client.post("/api/v1/projects/1/tasks", json={"title": "Trim Test Task"}).json()
        resp_space_comment = editor_client.post(
            f"/api/v1/tasks/{t['id']}/comments",
            json={"content": "    "},
        )
        assert resp_space_comment.status_code == 422


def test_cross_workspace_information_disclosure_prevention(
    client: TestClient,
    editor_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        lbl = editor_client.post(
            "/api/v1/projects/1/labels", json={"name": "Secret", "color": "#123123"}
        ).json()
        label_id = lbl["id"]

        tsk = editor_client.post("/api/v1/projects/1/tasks", json={"title": "Secret Task"}).json()
        task_id = tsk["id"]

        cmt = editor_client.post(
            f"/api/v1/tasks/{task_id}/comments", json={"content": "Secret note"}
        ).json()
        comment_id = cmt["id"]

    with TestClient(app, headers=stranger_headers) as stranger_client:
        # Stranger attempting to update or delete label in Project 1 gets 404 (not leaking 403)
        assert (
            stranger_client.patch(f"/api/v1/labels/{label_id}", json={"name": "Hacked"}).status_code
            == 404
        )
        assert stranger_client.delete(f"/api/v1/labels/{label_id}").status_code == 404

        # Stranger attempting to attach label to task gets 403
        # (stopped at task project access check and cannot tell if label_id exists)
        assert stranger_client.post(f"/api/v1/tasks/{task_id}/labels/{label_id}").status_code == 403
        assert stranger_client.post(f"/api/v1/tasks/{task_id}/labels/99999").status_code == 403

        # Stranger attempting to delete comment in Project 1 gets 404
        assert stranger_client.delete(f"/api/v1/comments/{comment_id}").status_code == 404

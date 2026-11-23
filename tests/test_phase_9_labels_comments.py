from fastapi.testclient import TestClient

from taskhub.main import app


def test_project_label_crud_and_permissions(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    project_id = 1

    # 1. EDITOR creates label successfully -> 201
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_create = editor_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "Bug", "color": "#10B981"},
        )
        assert resp_create.status_code == 201
        data = resp_create.json()
        assert data["name"] == "Bug"
        assert data["color"] == "#10B981"
        assert data["project_id"] == project_id
        label_id = data["id"]

        # 2. Validation error: invalid hex color -> 422
        resp_bad_color = editor_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "Feature", "color": "blue"},
        )
        assert resp_bad_color.status_code == 422

        # 3. Duplicate label name in same project -> 409
        resp_dup = editor_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "Bug", "color": "#EF4444"},
        )
        assert resp_dup.status_code == 409

    # 4. VIEWER cannot create, update, or delete label -> 403
    with TestClient(app, headers=viewer_headers) as viewer_client:
        # Create blocked
        resp_viewer_create = viewer_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "Viewer Label", "color": "#F59E0B"},
        )
        assert resp_viewer_create.status_code == 403

        # Update blocked
        resp_viewer_patch = viewer_client.patch(
            f"/api/v1/labels/{label_id}",
            json={"name": "Hacked Name"},
        )
        assert resp_viewer_patch.status_code == 403

        # Delete blocked
        resp_viewer_del = viewer_client.delete(f"/api/v1/labels/{label_id}")
        assert resp_viewer_del.status_code == 403

    # 5. Stranger cannot access project labels -> 403
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger_list = stranger_client.get(f"/api/v1/projects/{project_id}/labels")
        assert resp_stranger_list.status_code == 403

    # 6. EDITOR updates label successfully -> 200
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_update = editor_client.patch(
            f"/api/v1/labels/{label_id}",
            json={"name": "Critical Bug", "color": "#EF4444"},
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["name"] == "Critical Bug"
        assert resp_update.json()["color"] == "#EF4444"

        # List project labels with X-Total-Count
        resp_list = editor_client.get(f"/api/v1/projects/{project_id}/labels?page=1&limit=10")
        assert resp_list.status_code == 200
        assert "X-Total-Count" in resp_list.headers
        assert int(resp_list.headers["X-Total-Count"]) >= 1

        # Delete label successfully -> 204
        resp_del = editor_client.delete(f"/api/v1/labels/{label_id}")
        assert resp_del.status_code == 204

        # Verify deleted -> 404
        resp_check = editor_client.patch(f"/api/v1/labels/{label_id}", json={"name": "Ghost"})
        assert resp_check.status_code == 404


def test_attach_and_detach_label_to_task(
    client: TestClient,
    editor_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create a task in Project 1
        resp_task = editor_client.post(
            "/api/v1/projects/1/tasks",
            json={"title": "Task with Labels"},
        )
        assert resp_task.status_code == 201
        task_id = resp_task.json()["id"]

        # Create a label in Project 1
        resp_label1 = editor_client.post(
            "/api/v1/projects/1/labels",
            json={"name": "Backend", "color": "#10B981"},
        )
        assert resp_label1.status_code == 201
        l1_id = resp_label1.json()["id"]

        # Create a label in Project 5
        resp_label5 = editor_client.post(
            "/api/v1/projects/5/labels",
            json={"name": "Frontend", "color": "#3B82F6"},
        )
        assert resp_label5.status_code == 201
        l5_id = resp_label5.json()["id"]

        # 1. Attach label from same project -> 201
        resp_attach = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{l1_id}")
        assert resp_attach.status_code in (200, 201)
        assert resp_attach.json()["id"] == l1_id

        # 2. Attach duplicate label -> 409
        resp_attach_dup = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{l1_id}")
        assert resp_attach_dup.status_code == 409
        assert "already attached" in resp_attach_dup.json()["detail"]

        # 3. Attach label from different project (Project 5 label to Project 1 task) -> 400
        resp_cross_attach = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{l5_id}")
        assert resp_cross_attach.status_code == 400
        assert "does not belong to the task's project" in resp_cross_attach.json()["detail"]

        # 4. Detach label from task -> 204
        resp_detach = editor_client.delete(f"/api/v1/tasks/{task_id}/labels/{l1_id}")
        assert resp_detach.status_code == 204

        # 5. Detach again -> 404
        resp_detach_again = editor_client.delete(f"/api/v1/tasks/{task_id}/labels/{l1_id}")
        assert resp_detach_again.status_code == 404


def test_task_comments_flow_and_permissions(
    client: TestClient,
    viewer_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    # 1. Create a task in Project 1
    resp_task = client.post(
        "/api/v1/projects/1/tasks",
        json={"title": "Task for Discussion"},
    )
    assert resp_task.status_code == 201
    task_id = resp_task.json()["id"]

    # 2. Member (VIEWER - User 3) creates comment successfully -> 201
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_comment = viewer_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Here is a helpful comment from viewer."},
        )
        assert resp_comment.status_code == 201
        comment_data = resp_comment.json()
        assert comment_data["content"] == "Here is a helpful comment from viewer."
        assert comment_data["author_id"] == 3
        assert "author" in comment_data
        assert comment_data["author"] is not None
        assert comment_data["author"]["id"] == 3

    # 3. Stranger (User 4) cannot create comment -> 403
    with TestClient(app, headers=stranger_headers) as stranger_client:
        resp_stranger_comment = stranger_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Malicious comment"},
        )
        assert resp_stranger_comment.status_code == 403

        # Stranger cannot list comments -> 403
        resp_stranger_list = stranger_client.get(f"/api/v1/tasks/{task_id}/comments")
        assert resp_stranger_list.status_code == 403

    # 4. Member lists comments with X-Total-Count header
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_list = viewer_client.get(f"/api/v1/tasks/{task_id}/comments?page=1&limit=10")
        assert resp_list.status_code == 200
        data = resp_list.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "X-Total-Count" in resp_list.headers
        assert int(resp_list.headers["X-Total-Count"]) >= 1


def test_delete_comment_authorization(
    client: TestClient,
    editor_headers: dict[str, str],
    viewer_headers: dict[str, str],
):
    # 1. Create task
    resp_task = client.post(
        "/api/v1/projects/1/tasks",
        json={"title": "Task to test comment deletion"},
    )
    assert resp_task.status_code == 201
    task_id = resp_task.json()["id"]

    # 2. Viewer (User 3) posts a comment
    with TestClient(app, headers=viewer_headers) as viewer_client:
        resp_c1 = viewer_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Viewer comment to be deleted"},
        )
        assert resp_c1.status_code == 201
        c1_id = resp_c1.json()["id"]

    # 3. Editor (User 5, regular member) tries to delete Viewer's comment -> 403
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_del_unauth = editor_client.delete(f"/api/v1/comments/{c1_id}")
        assert resp_del_unauth.status_code == 403
        assert "permission" in resp_del_unauth.json()["detail"].lower()

    # 4. Workspace OWNER (User 1 - client) deletes Viewer's comment -> 204
    resp_owner_del = client.delete(f"/api/v1/comments/{c1_id}")
    assert resp_owner_del.status_code == 204

    # 5. Editor posts another comment
    with TestClient(app, headers=editor_headers) as editor_client:
        resp_c2 = editor_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Editor self comment"},
        )
        assert resp_c2.status_code == 201
        c2_id = resp_c2.json()["id"]

        # Author (Editor) deletes their own comment -> 204
        resp_author_del = editor_client.delete(f"/api/v1/comments/{c2_id}")
        assert resp_author_del.status_code == 204


def test_label_default_color_and_length_and_member_role(
    client: TestClient,
    user2_headers: dict[str, str],
):
    project_id = 1
    # 1. WorkspaceRole.MEMBER (user 2) CAN create label (MEMBER role restored to label write roles)
    with TestClient(app, headers=user2_headers) as member_client:
        # Omitting color -> defaults to #3B82F6
        resp_default_color = member_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "AutoColorLabel"},
        )
        assert resp_default_color.status_code == 201
        data = resp_default_color.json()
        assert data["name"] == "AutoColorLabel"
        assert data["color"] == "#3B82F6"

        # Label name length up to 100 succeeds
        long_name_100 = "x" * 100
        resp_100 = member_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": long_name_100},
        )
        assert resp_100.status_code == 201
        assert resp_100.json()["name"] == long_name_100

        # Label name length 101 fails -> 422
        long_name_101 = "y" * 101
        resp_101 = member_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": long_name_101},
        )
        assert resp_101.status_code == 422


def test_archived_project_blocks_labels_and_comments_without_leaking_to_strangers(
    client: TestClient,
    editor_headers: dict[str, str],
    stranger_headers: dict[str, str],
):
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create dedicated project for archive testing
        resp_proj = editor_client.post(
            "/api/v1/workspaces/1/projects",
            json={"name": "Archived Label Project"},
        )
        assert resp_proj.status_code == 201
        proj_id = resp_proj.json()["id"]

        # Create task in this project
        resp_task = editor_client.post(
            f"/api/v1/projects/{proj_id}/tasks",
            json={"title": "Task in soon-archived project"},
        )
        assert resp_task.status_code == 201
        task_id = resp_task.json()["id"]

        # Create label in this project
        resp_lbl = editor_client.post(
            f"/api/v1/projects/{proj_id}/labels",
            json={"name": "PreArchiveLabel"},
        )
        assert resp_lbl.status_code == 201
        lbl_id = resp_lbl.json()["id"]

        # Create comment on the task
        resp_cmt = editor_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Pre-archive comment"},
        )
        assert resp_cmt.status_code == 201
        cmt_id = resp_cmt.json()["id"]

        # Archive the project
        resp_archive = editor_client.patch(
            f"/api/v1/projects/{proj_id}",
            json={"status": "ARCHIVED"},
        )
        assert resp_archive.status_code == 200

    # 1. Stranger (User 4) tests: MUST NOT receive 400 "archived" (must receive 403 or 404)
    with TestClient(app, headers=stranger_headers) as stranger_client:
        # Create label -> 403 (not 400)
        resp_s_create_lbl = stranger_client.post(
            f"/api/v1/projects/{proj_id}/labels",
            json={"name": "StrangerLabel"},
        )
        assert resp_s_create_lbl.status_code == 403
        assert "Cannot modify labels in an archived project" not in resp_s_create_lbl.text

        # Update label -> 404 (not 400)
        resp_s_patch_lbl = stranger_client.patch(
            f"/api/v1/labels/{lbl_id}",
            json={"name": "StrangerUpdate"},
        )
        assert resp_s_patch_lbl.status_code == 404
        assert "Cannot modify labels in an archived project" not in resp_s_patch_lbl.text

        # Delete label -> 404 (not 400)
        resp_s_del_lbl = stranger_client.delete(f"/api/v1/labels/{lbl_id}")
        assert resp_s_del_lbl.status_code == 404

        # Attach label -> 403 (not 400)
        resp_s_attach = stranger_client.post(f"/api/v1/tasks/{task_id}/labels/{lbl_id}")
        assert resp_s_attach.status_code == 403

        # Create comment -> 403 (not 400)
        resp_s_create_cmt = stranger_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Stranger comment"},
        )
        assert resp_s_create_cmt.status_code == 403

        # Delete comment -> 404 (not 400)
        resp_s_del_cmt = stranger_client.delete(f"/api/v1/comments/{cmt_id}")
        assert resp_s_del_cmt.status_code == 404

    # 2. Member/Editor tests: MUST receive 400 with archived error
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create label on archived project -> 400
        resp_create_fail = editor_client.post(
            f"/api/v1/projects/{proj_id}/labels",
            json={"name": "FailLabel"},
        )
        assert resp_create_fail.status_code == 400
        assert "Cannot modify labels in an archived project" in resp_create_fail.json()["detail"]

        # Update label on archived project -> 400
        resp_update_fail = editor_client.patch(
            f"/api/v1/labels/{lbl_id}",
            json={"name": "NewNameFail"},
        )
        assert resp_update_fail.status_code == 400
        assert "Cannot modify labels in an archived project" in resp_update_fail.json()["detail"]

        # Delete label on archived project -> 400
        resp_del_lbl_fail = editor_client.delete(f"/api/v1/labels/{lbl_id}")
        assert resp_del_lbl_fail.status_code == 400
        assert "Cannot modify labels in an archived project" in resp_del_lbl_fail.json()["detail"]

        # Attach label on archived project -> 400
        resp_attach_fail = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{lbl_id}")
        assert resp_attach_fail.status_code == 400
        assert "Cannot modify labels in an archived project" in resp_attach_fail.json()["detail"]

        # Create comment on archived project -> 400
        resp_cmt_fail = editor_client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Should fail comment"},
        )
        assert resp_cmt_fail.status_code == 400
        assert "Cannot comment on tasks in an archived project" in resp_cmt_fail.json()["detail"]

        # Delete comment on archived project -> 400
        resp_del_cmt_fail = editor_client.delete(f"/api/v1/comments/{cmt_id}")
        assert resp_del_cmt_fail.status_code == 400
        assert "Cannot delete comments in an archived project" in resp_del_cmt_fail.json()["detail"]

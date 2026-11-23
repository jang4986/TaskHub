import fnmatch
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from taskhub.core import cache
from taskhub.main import app


class FakeAsyncRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.calls: list[str] = []

    async def get(self, key: str) -> str | None:
        self.calls.append(f"GET {key}")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.calls.append(f"SET {key}")
        self.store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        self.calls.append(f"DELETE {keys}")
        count = 0
        for k in keys:
            if k in self.store:
                del self.store[k]
                count += 1
        return count

    async def scan_iter(self, match: str | None = None) -> AsyncGenerator[str, None]:
        self.calls.append(f"SCAN {match}")
        for key in list(self.store.keys()):
            if match is None or fnmatch.fnmatch(key, match):
                yield key

    async def aclose(self) -> None:
        self.store.clear()


class BrokenAsyncRedis:
    async def get(self, key: str) -> str | None:
        raise RedisConnectionError("Simulated Redis connection failure")

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        raise RedisConnectionError("Simulated Redis connection failure")

    async def delete(self, *keys: str) -> int:
        raise RedisConnectionError("Simulated Redis connection failure")

    async def scan_iter(self, match: str | None = None) -> AsyncGenerator[str, None]:
        raise RedisConnectionError("Simulated Redis connection failure")
        yield ""  # pragma: no cover

    async def aclose(self) -> None:
        pass


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeAsyncRedis:
    fake = FakeAsyncRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: fake)
    return fake


@pytest.fixture
def broken_redis(monkeypatch: pytest.MonkeyPatch) -> BrokenAsyncRedis:
    broken = BrokenAsyncRedis()
    monkeypatch.setattr(cache, "get_redis_client", lambda: broken)
    return broken


def test_get_project_tasks_cache_hit_and_miss(
    client: TestClient,
    fake_redis: FakeAsyncRedis,
):
    """Calling GET /projects/{id}/tasks twice returns MISS on 1st, HIT on 2nd."""
    project_id = 1

    # Call 1: Cache MISS
    resp1 = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp1.status_code == 200
    assert resp1.headers.get("X-Cache") == "MISS"
    assert "X-Total-Count" in resp1.headers
    data1 = resp1.json()
    assert isinstance(data1, list)
    assert len(fake_redis.store) == 1

    # Call 2: Cache HIT
    resp2 = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Cache") == "HIT"
    assert resp2.headers["X-Total-Count"] == resp1.headers["X-Total-Count"]
    data2 = resp2.json()
    assert data1 == data2


def test_cache_invalidation_on_task_mutation(
    client: TestClient,
    editor_headers: dict[str, str],
    fake_redis: FakeAsyncRedis,
):
    """Mutating tasks (POST/PATCH/DELETE) and attaching/removing labels invalidates cache."""
    project_id = 1

    # 1. Warm cache
    resp_init = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_init.status_code == 200
    assert resp_init.headers.get("X-Cache") == "MISS"

    resp_hit = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_hit.status_code == 200
    assert resp_hit.headers.get("X-Cache") == "HIT"
    assert len(fake_redis.store) == 1

    # 2. CREATE task invalidates cache
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task for Invalidation Test"},
    )
    assert resp_create.status_code == 201
    task_id = resp_create.json()["id"]
    assert len(fake_redis.store) == 0

    # Query again -> MISS, then HIT
    resp_after_create = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_after_create.status_code == 200
    assert resp_after_create.headers.get("X-Cache") == "MISS"

    resp_after_create_hit = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_after_create_hit.status_code == 200
    assert resp_after_create_hit.headers.get("X-Cache") == "HIT"
    assert len(fake_redis.store) == 1

    # 3. UPDATE task invalidates cache
    resp_patch = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Task Invalidation Test"},
    )
    assert resp_patch.status_code == 200
    assert len(fake_redis.store) == 0

    # Query again -> MISS, then HIT
    resp_after_patch = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_after_patch.status_code == 200
    assert resp_after_patch.headers.get("X-Cache") == "MISS"

    resp_after_patch_hit = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_after_patch_hit.status_code == 200
    assert resp_after_patch_hit.headers.get("X-Cache") == "HIT"

    # 4. ATTACH LABEL to task invalidates cache
    with TestClient(app, headers=editor_headers) as editor_client:
        # Create a label first
        resp_lbl = editor_client.post(
            f"/api/v1/projects/{project_id}/labels",
            json={"name": "CacheTestLabel"},
        )
        assert resp_lbl.status_code == 201
        lbl_id = resp_lbl.json()["id"]

        # Attach label
        resp_attach = editor_client.post(f"/api/v1/tasks/{task_id}/labels/{lbl_id}")
        assert resp_attach.status_code in (200, 201)
        assert len(fake_redis.store) == 0

        # Query again -> MISS, then HIT
        resp_after_attach = editor_client.get(f"/api/v1/projects/{project_id}/tasks")
        assert resp_after_attach.status_code == 200
        assert resp_after_attach.headers.get("X-Cache") == "MISS"

        resp_after_attach_hit = editor_client.get(f"/api/v1/projects/{project_id}/tasks")
        assert resp_after_attach_hit.status_code == 200
        assert resp_after_attach_hit.headers.get("X-Cache") == "HIT"

        # 5. REMOVE LABEL from task invalidates cache
        resp_detach = editor_client.delete(f"/api/v1/tasks/{task_id}/labels/{lbl_id}")
        assert resp_detach.status_code == 204
        assert len(fake_redis.store) == 0

        # Query again -> MISS, then HIT
        resp_after_detach = editor_client.get(f"/api/v1/projects/{project_id}/tasks")
        assert resp_after_detach.status_code == 200
        assert resp_after_detach.headers.get("X-Cache") == "MISS"

        resp_after_detach_hit = editor_client.get(f"/api/v1/projects/{project_id}/tasks")
        assert resp_after_detach_hit.status_code == 200
        assert resp_after_detach_hit.headers.get("X-Cache") == "HIT"

    # 6. DELETE task invalidates cache
    resp_del = client.delete(f"/api/v1/tasks/{task_id}")
    assert resp_del.status_code == 204
    assert len(fake_redis.store) == 0

    # Query again -> MISS
    resp_final = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_final.status_code == 200
    assert resp_final.headers.get("X-Cache") == "MISS"


def test_redis_connection_failure_graceful_fallback(
    client: TestClient,
    broken_redis: BrokenAsyncRedis,
):
    """When Redis fails, API gracefully degrades by directly querying DB without throwing 500."""
    project_id = 1

    # GET operations succeed with X-Cache: MISS and 200 OK
    resp_get = client.get(f"/api/v1/projects/{project_id}/tasks")
    assert resp_get.status_code == 200
    assert resp_get.headers.get("X-Cache") == "MISS"
    assert "X-Total-Count" in resp_get.headers
    assert isinstance(resp_get.json(), list)

    # Mutation operations succeed with 201/200 without throwing error on invalidation
    resp_create = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task during Redis Outage"},
    )
    assert resp_create.status_code == 201
    created_id = resp_create.json()["id"]

    # PATCH succeeds
    resp_patch = client.patch(
        f"/api/v1/tasks/{created_id}",
        json={"title": "Updated Task during Outage"},
    )
    assert resp_patch.status_code == 200

    # DELETE succeeds
    resp_del = client.delete(f"/api/v1/tasks/{created_id}")
    assert resp_del.status_code == 204

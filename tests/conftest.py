from collections.abc import AsyncGenerator
from fastapi.testclient import TestClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskhub.core.security import create_access_token, get_password_hash
from taskhub.db.session import get_db
from taskhub.enums.common import UserRole
from taskhub.main import app
from taskhub.models.base import Base
from taskhub.models.project import Project
from taskhub.models.user import User
from taskhub.models.workspace import Workspace

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    # Setup tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Seed initial test data: Users, Workspaces, and Projects
    async with TestingSessionLocal() as session:
        user1 = User(
            id=1,
            email="user1@example.com",
            full_name="User One",
            hashed_password=get_password_hash("password123"),
            role=UserRole.MEMBER.value,
            is_active=True,
        )
        user2 = User(
            id=2,
            email="user2@example.com",
            full_name="User Two",
            hashed_password=get_password_hash("password123"),
            role=UserRole.MEMBER.value,
            is_active=True,
        )
        admin_user = User(
            id=99,
            email="admin@example.com",
            full_name="Admin User",
            hashed_password=get_password_hash("adminpassword123"),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        inactive_user = User(
            id=100,
            email="inactive@example.com",
            full_name="Inactive User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.MEMBER.value,
            is_active=False,
        )
        session.add_all([user1, user2, admin_user, inactive_user])
        await session.flush()

        ws1 = Workspace(id=1, name="Workspace Alpha", owner_id=1)
        session.add(ws1)
        await session.flush()

        proj1 = Project(id=1, workspace_id=1, name="Project Alpha", description="Alpha project", owner_id=1)
        proj5 = Project(id=5, workspace_id=1, name="Project Beta", description="Beta project", owner_id=1)
        proj10 = Project(id=10, workspace_id=1, name="Project Gamma", description="Gamma project", owner_id=1)
        session.add_all([proj1, proj5, proj10])
        await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def member_token() -> str:
    return create_access_token({"sub": "1", "role": UserRole.MEMBER.value})


@pytest.fixture
def admin_token() -> str:
    return create_access_token({"sub": "99", "role": UserRole.ADMIN.value})


@pytest.fixture
def member_headers(member_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {member_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def unauth_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(member_headers: dict[str, str]):
    with TestClient(app, headers=member_headers) as test_client:
        yield test_client

# TaskHub — Task & Workspace Management API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x_Async-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![uv](https://img.shields.io/badge/Package_Manager-uv-DE5FE9.svg)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)

TaskHub là hệ thống API quản lý công việc và không gian làm việc nhóm (Workspace & Task Management API) chuẩn doanh nghiệp, được xây dựng trên nền tảng **FastAPI**, **SQLAlchemy 2.x Async**, **PostgreSQL**, **Redis**, và **Pydantic v2**. Dự án tuân thủ nghiêm ngặt chuẩn kiến trúc phân tầng (**Layered Architecture**), hệ thống phân quyền đa cấp (**RBAC**), cơ chế lưu bộ nhớ đệm chủ động (**Cache-Aside with Invalidation**), và xử lý tác vụ nền bất đồng bộ (**FastAPI BackgroundTasks**).

---

## 1. TỔNG QUAN CÔNG NGHỆ (TECH STACK)

| Thành phần | Công nghệ / Thư viện | Vai trò |
|---|---|---|
| **Core Framework** | FastAPI >= 0.111 (Python 3.12+) | Web framework hiệu năng cao, auto OpenAPI / Swagger / ReDoc |
| **Package Manager** | `uv` (Astral) | Quản lý môi trường ảo, dependencies, và lockfile siêu tốc |
| **ORM & Database** | SQLAlchemy 2.x Async + asyncpg / aiosqlite | Truy vấn cơ sở dữ liệu bất đồng bộ |
| **Database Migrations** | Alembic | Quản lý phiên bản và đồng bộ hóa schema cơ sở dữ liệu |
| **Validation & Settings** | Pydantic v2 & Pydantic-Settings | Validate dữ liệu đầu vào/ra (fail-fast, 422) và nạp cấu hình môi trường |
| **Cache & Invalidation** | Redis 7 + `redis.asyncio` | Caching danh sách tasks, tự động hủy cache khi phát sinh mutation |
| **Authentication** | PyJWT + pwdlib[argon2] | JWT Access token (30m) + Refresh token (7d) có blacklist revocation |
| **Quality & Testing** | Ruff, Mypy, Pytest, Pytest-Asyncio | Linter 100% pass, Type checker 0 error, 80 automated unit/integration tests |
| **Containerization** | Docker (Multi-stage build) & Docker Compose | Đóng gói production image tối ưu và điều phối stack `app`, `db`, `redis` |

---

## 2. KIẾN TRÚC HỆ THỐNG (LAYERED ARCHITECTURE)

Dự án áp dụng mô hình phân tầng chặt chẽ với nguyên tắc phụ thuộc một chiều (**One-way Dependency Rule**):

```
HTTP Request
     │
     ▼
┌────────────────────────────────────────────────────────┐
│  API Presentation Layer (src/taskhub/api/v1/)          │
│  - Router definitions & parameter parsing              │
│  - Dependency Injection (src/taskhub/api/deps.py)      │
└────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────┐
│  Business Service Layer (src/taskhub/services/)        │
│  - RBAC verification & resource ownership validation   │
│  - Cache read (HIT/MISS) & invalidation dispatch       │
│  - Background task worker scheduling                   │
└────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────┐
│  Data Access Layer (src/taskhub/repositories/)         │
│  - Generic BaseRepository[T, CreateSchema, Update]     │
│  - Dedicated queries, pagination, aggregation          │
└────────────────────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────────────────────┐
│  Domain & Storage Layer                                │
│  - SQLAlchemy 2.x Models (src/taskhub/models/)         │
│  - Pydantic v2 Contracts (src/taskhub/schemas/)        │
│  - PostgreSQL 16 & Redis 7 Infrastructure              │
└────────────────────────────────────────────────────────┘
```

### Cấu Trúc Thư Mục Codebase
```
TaskHub/
├── .env.example                # File mẫu cấu hình biến môi trường
├── .dockerignore               # Danh sách file/thư mục loại trừ khi build Docker
├── Dockerfile                  # Multi-stage Docker build với uv & python:3.12-slim
├── docker-compose.yml          # Điều phối 3 services: db (postgres), redis, app
├── pyproject.toml              # Cấu hình dự án, dependencies, ruff, mypy, pytest
├── alembic.ini                 # Cấu hình migration của Alembic
├── alembic/                    # Mã nguồn migration và versions
│   ├── env.py                  # Dynamic connection config từ App Settings
│   └── versions/               # Lịch sử các bản migration database
├── src/taskhub/                # Mã nguồn chính của ứng dụng
│   ├── main.py                 # FastAPI application, lifespan, custom OpenAPI metadata
│   ├── core/                   # Cấu hình, bảo mật, cache và exceptions dùng chung
│   │   ├── config.py           # Pydantic Settings (.env, DATABASE_URL, REDIS_URL)
│   │   ├── security.py         # Password hashing (Argon2) & JWT generation/decoding
│   │   ├── cache.py            # Redis async client, graceful degradation, invalidation
│   │   ├── constants.py        # Hằng số toàn hệ thống (page size, colors, regex)
│   │   ├── enums.py            # Enum định danh UserRole, WorkspaceRole, TaskStatus...
│   │   └── exceptions.py       # Domain-specific HTTPExceptions
│   ├── models/                 # SQLAlchemy 2.x Mapped ORM Models
│   │   ├── user.py             # Entity Người dùng
│   │   ├── workspace.py        # Entity Không gian làm việc
│   │   ├── workspace_member.py # Entity Thành viên Workspace (kèm Role)
│   │   ├── project.py          # Entity Dự án (ACTIVE / ARCHIVED)
│   │   ├── task.py             # Entity Công việc (assignee, priority, status)
│   │   ├── label.py            # Entity Nhãn phân loại
│   │   ├── task_label.py       # Entity Bảng liên kết N-N giữa Task & Label
│   │   ├── comment.py          # Entity Bình luận
│   │   ├── notification.py     # Entity Thông báo người dùng
│   │   └── revoked_token.py    # Entity Refresh Token đã thu hồi (Blacklist)
│   ├── schemas/                # Pydantic v2 Models (Validation & Serialization)
│   ├── repositories/           # Generic & Specific Data Repositories
│   ├── services/               # Business Logic, RBAC & Workflows
│   └── api/                    # API Routing & Fastapi Dependencies
│       ├── deps.py             # Dependency Injection providers & Annotations
│       └── v1/
│           ├── router.py       # Định nghĩa API v1 router kèm standard error responses
│           └── endpoints/      # Controllers theo tài nguyên
└── tests/                      # Bộ kiểm thử tự động toàn diện (80 tests)
```

---

## 3. CÁC QUYẾT ĐỊNH THIẾT KẾ TRỌNG TÂM (CORE DESIGN DECISIONS)

### 3.1. Database Schema (8 Thực thể Chính + 2 Thực thể Hỗ trợ)
1. `users`: Quản lý danh tính, `email` (unique index), `hashed_password`, `role` (`ADMIN`/`MEMBER`), `token_version`.
2. `workspaces`: Không gian làm việc nhóm, liên kết với `owner_id` (FK `users.id`).
3. `workspace_members`: Bảng thành viên với vai trò cụ thể trong từng workspace: `OWNER`, `ADMIN`, `EDITOR`, `VIEWER`, `MEMBER`.
4. `projects`: Dự án thuộc workspace hoặc cá nhân, có trạng thái `status` (`ACTIVE` hoặc `ARCHIVED`).
5. `tasks`: Công việc thuộc dự án, liên kết `assignee_id`, `created_by`, `status` (`TODO`/`IN_PROGRESS`/`IN_REVIEW`/`DONE`), `priority` (`LOW`/`MEDIUM`/`HIGH`/`URGENT`), `due_date`.
6. `labels`: Nhãn đánh dấu với mã màu HEX chuẩn regex `^#[0-9A-Fa-f]{6}$` và tên nhãn unique trong từng project.
7. `task_labels`: Quan hệ nhiều-nhiều (N-N) giữa `tasks` và `labels`.
8. `comments`: Bình luận trao đổi trên task, lưu `author_id` và `content`.
9. `notifications`: Thông báo hệ thống (`TASK_ASSIGNED`...) kèm trạng thái `is_read`.
10. `revoked_tokens`: Bảng blacklist lưu token ID (`jti`) của các refresh token đã bị thu hồi khi logout.

### 3.2. Ma Trận Phân Quyền (RBAC & Multi-tenant Isolation)
- **Cấp độ Hệ thống**:
  * `ADMIN`: Có toàn quyền quản trị hệ sinh thái, truy cập các endpoint quản lý user toàn cục.
  * `MEMBER`: Người dùng thông thường trong hệ thống.
- **Cấp độ Workspace**:
  * `OWNER`: Chủ sở hữu workspace, có quyền xóa workspace, xóa project, xóa comment của bất kỳ ai trong workspace.
  * `ADMIN`: Quản trị viên workspace, có quyền xóa/thêm thành viên, tạo/sửa project, xóa project.
  * `EDITOR` / `MEMBER`: Thành viên có quyền tạo project, tạo/sửa task, gán/tạo label, bình luận, và xóa comment của chính mình.
  * `VIEWER`: Chỉ có quyền đọc (read-only) danh sách task, bình luận, và project. Bị chặn tuyệt đối khi tạo/sửa task, label hoặc khi được gán task.
- **Quy tắc An toàn Dữ liệu (Project ARCHIVED)**:
  * Khi project ở trạng thái `ARCHIVED`, cấm toàn bộ các thao tác ghi (tạo/sửa/xóa task, gắn/gỡ label, tạo/xóa comment, đổi tên/mô tả project). Thao tác duy nhất được cho phép là mở lại project (`{"status": "ACTIVE"}`).
  * Kiểm tra quyền người dùng luôn được thực hiện **trước** khi kiểm tra trạng thái lưu trữ (`ARCHIVED`) nhằm ngăn chặn việc rò rỉ trạng thái nội bộ của dự án cho người ngoài (BP31).

### 3.3. Caching Chủ Động (Cache-Aside & Invalidation) với Graceful Degradation
- **Cache Key Chuẩn**:
  `tasks:project:{project_id}:status:{status}:priority:{priority}:assignee:{assignee}:offset:{offset}:limit:{limit}`
- **Cache Invalidation**:
  Bất cứ thao tác nào làm thay đổi dữ liệu task (`create_task`, `update_task`, `delete_task`, `add_label_to_task`, `remove_label_from_task`) đều tự động quét mẫu `tasks:project:{project_id}:*` và xóa sạch toàn bộ cache liên quan của project đó.
- **Graceful Degradation**:
  Nếu Redis server gặp sự cố hoặc ngoại tuyến, hệ thống tự động bắt lỗi `RedisError`, ghi log cảnh báo và tự động fallback truy vấn trực tiếp từ cơ sở dữ liệu. API luôn hoạt động bình thường mà không gây lỗi HTTP 500.

### 3.4. Background Tasks & Notification Worker
- Khi tạo task mới hoặc reassign task cho người khác (`assignee_id != old_assignee_id`), API sử dụng `FastAPI.BackgroundTasks` đưa tác vụ gửi thông báo vào hàng đợi nền.
- Worker `send_task_assigned_notification` chạy độc lập với session database riêng biệt: tạo bản ghi `Notification` và log email dispatch mà không làm nghẽn luồng xử lý HTTP request chính.

---

## 4. HƯỚNG DẪN CÀI ĐẶT & CHẠY LOCAL (VỚI UV)

### 4.1. Yêu cầu hệ thống
- **Python**: `>= 3.12`
- **uv**: Đã cài đặt (`pip install uv` hoặc cài đặt qua script chính thức từ Astral)
- **Git**

### 4.2. Các bước cài đặt chi tiết

1. **Clone repository**:
   ```bash
   git clone https://github.com/ngyuenduyhan/TaskHub.git
   cd TaskHub
   ```

2. **Cài đặt dependencies qua `uv`**:
   ```bash
   # Tạo virtual environment và đồng bộ toàn bộ dependencies
   uv sync
   ```

3. **Cấu hình biến môi trường**:
   ```bash
   # Sao chép file cấu hình mẫu
   cp .env.example .env
   ```
   *Chỉnh sửa `.env` nếu muốn thay đổi secret key hoặc kết nối cơ sở dữ liệu.*

4. **Chạy Migration Database**:
   ```bash
   uv run alembic upgrade head
   ```

5. **Khởi chạy Development Server**:
   ```bash
   uv run uvicorn taskhub.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - **Healthcheck**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 5. HƯỚNG DẪN CHẠY BẰNG DOCKER COMPOSE

Dự án cung cấp file [docker-compose.yml](file:///e:/TaskHub/docker-compose.yml) đóng gói sẵn toàn bộ môi trường bao gồm:
- **`db`**: PostgreSQL 16 Alpine với healthcheck `pg_isready` và volume lưu trữ bền vững `postgres_data`.
- **`redis`**: Redis 7 Alpine với healthcheck `redis-cli ping`.
- **`app`**: Multi-stage build Python 3.12-slim tự động chạy `alembic upgrade head` và khởi chạy server khi các dịch vụ `db` và `redis` đã sẵn sàng (`service_healthy`).

### Khởi động Stack:
```bash
docker compose up --build -d
```

### Kiểm tra trạng thái containers:
```bash
docker compose ps
```

### Xem log theo thời gian thực:
```bash
docker compose logs -f app
```

### Dừng stack:
```bash
docker compose down
```

---

## 6. DANH MỤC ENDPOINTS CHÍNH

Tất cả các endpoint (trừ Auth công khai và Health) đều yêu cầu Bearer Token trong header `Authorization: Bearer <access_token>`.

### 6.1. Xác thực & Tài khoản (Auth & Users)
| Phương thức | Đường dẫn | Mô tả | Quyền yêu cầu |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Đăng ký tài khoản mới | Công khai |
| `POST` | `/api/v1/auth/login` | Đăng nhập lấy access token & refresh token | Công khai |
| `POST` | `/api/v1/auth/refresh` | Làm mới access token (hỗ trợ token rotation) | Bearer Refresh Token |
| `POST` | `/api/v1/auth/logout` | Thu hồi refresh token hiện tại (đưa vào blacklist) | Đăng nhập |
| `GET` | `/api/v1/users/me` | Lấy thông tin profile người dùng hiện tại | Đăng nhập |
| `PATCH` | `/api/v1/users/me` | Cập nhật họ tên, email người dùng | Đăng nhập |
| `POST` | `/api/v1/users/change-password` | Đổi mật khẩu (thu hồi mọi phiên đăng nhập cũ) | Đăng nhập |

### 6.2. Không gian làm việc (Workspaces)
| Phương thức | Đường dẫn | Mô tả | Quyền yêu cầu |
|---|---|---|---|
| `POST` | `/api/v1/workspaces` | Tạo workspace mới | Đăng nhập |
| `GET` | `/api/v1/workspaces` | Lấy danh sách workspace người dùng tham gia | Đăng nhập |
| `GET` | `/api/v1/workspaces/{id}` | Xem chi tiết workspace kèm danh sách thành viên | Thành viên Workspace |
| `POST` | `/api/v1/workspaces/{id}/members` | Mời/thêm thành viên vào workspace | OWNER hoặc ADMIN |
| `DELETE` | `/api/v1/workspaces/{id}/members/{user_id}` | Xóa thành viên khỏi workspace | OWNER hoặc ADMIN |
| `DELETE` | `/api/v1/workspaces/{id}` | Xóa toàn bộ workspace | OWNER |

### 6.3. Dự án (Projects)
| Phương thức | Đường dẫn | Mô tả | Quyền yêu cầu |
|---|---|---|---|
| `POST` | `/api/v1/workspaces/{id}/projects` | Tạo dự án mới trong workspace | OWNER, ADMIN, EDITOR |
| `GET` | `/api/v1/workspaces/{id}/projects` | Lấy danh sách dự án (mặc định ẩn archived) | Thành viên Workspace |
| `GET` | `/api/v1/projects/{id}` | Xem chi tiết dự án | Thành viên Workspace |
| `PATCH` | `/api/v1/projects/{id}` | Sửa tên, mô tả hoặc archive / un-archive dự án | OWNER, ADMIN, EDITOR |
| `DELETE` | `/api/v1/projects/{id}` | Xóa dự án | OWNER hoặc ADMIN |

### 6.4. Công việc & Nhãn (Tasks & Labels)
| Phương thức | Đường dẫn | Mô tả | Caching / Tác vụ |
|---|---|---|---|
| `GET` | `/api/v1/projects/{id}/tasks` | Lấy danh sách tasks (lọc status/priority/assignee) | **Redis Cache HIT/MISS** |
| `POST` | `/api/v1/projects/{id}/tasks` | Tạo task mới cho dự án | **Xóa cache + Gửi thông báo** |
| `GET` | `/api/v1/tasks/{id}` | Xem chi tiết task | Đọc trực tiếp |
| `PATCH` | `/api/v1/tasks/{id}` | Cập nhật task (trạng thái, độ ưu tiên, người làm) | **Xóa cache + Gửi thông báo** |
| `DELETE` | `/api/v1/tasks/{id}` | Xóa công việc | **Xóa cache** |
| `POST` | `/api/v1/projects/{id}/labels` | Tạo nhãn phân loại mới cho dự án | Ghi nhãn |
| `GET` | `/api/v1/projects/{id}/labels` | Lấy danh sách nhãn của dự án | Đọc danh sách |
| `PATCH` | `/api/v1/labels/{id}` | Cập nhật tên hoặc mã màu nhãn | Cập nhật nhãn |
| `DELETE` | `/api/v1/labels/{id}` | Xóa nhãn | Xóa nhãn |
| `POST` | `/api/v1/tasks/{id}/labels/{label_id}` | Gắn nhãn vào công việc | **Xóa cache tasks** |
| `DELETE` | `/api/v1/tasks/{id}/labels/{label_id}` | Tháo nhãn khỏi công việc | **Xóa cache tasks** |

### 6.5. Bình luận & Thông báo (Comments & Notifications)
| Phương thức | Đường dẫn | Mô tả |
|---|---|---|
| `POST` | `/api/v1/tasks/{id}/comments` | Thêm bình luận vào task |
| `GET` | `/api/v1/tasks/{id}/comments` | Xem danh sách bình luận (phân trang chronologically) |
| `DELETE` | `/api/v1/comments/{id}` | Xóa bình luận (Tác giả hoặc Workspace Owner) |
| `GET` | `/api/v1/notifications` | Lấy danh sách thông báo của tôi (lọc `unread_only`) |
| `PATCH` | `/api/v1/notifications/{id}/read` | Đánh dấu 1 thông báo là đã đọc |
| `POST` | `/api/v1/notifications/read-all` | Đánh dấu tất cả thông báo là đã đọc |

---

## 7. KIỂM ĐỊNH CHẤT LƯỢNG MÃ NGUỒN & AUTOMATED TESTS

Dự án sở hữu bộ test tự động toàn diện bao phủ toàn bộ 12 Phase tính năng từ Authentication, RBAC, Caching tới Background Tasks.

### 7.1. Chạy Linter (Ruff)
```bash
# Kiểm tra vi phạm cú pháp và quy chuẩn code (100% Pass)
uv run ruff check .

# Kiểm tra định dạng code
uv run ruff format --check .

# Tự động format code theo chuẩn PEP 8
uv run ruff format .
```

### 7.2. Kiểm tra Kiểu Dữ liệu Tĩnh (Mypy)
```bash
# Type check với Pydantic v2 plugin (0 Errors)
uv run mypy src/
```

### 7.3. Chạy Toàn Bộ Test Suite (Pytest)
```bash
# Chạy toàn bộ 80 test cases với SQLite In-Memory độc lập
uv run pytest -v
```

---

## 8. GIẤY PHÉP (LICENSE)
Dự án được phân phối dưới giấy phép mã nguồn mở [MIT License](LICENSE).
Tác giả: **Nguyen Duy Han** ([ngyuenduyhan235@gmail.com](mailto:ngyuenduyhan235@gmail.com)).

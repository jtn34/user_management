from unittest.mock import AsyncMock
from datetime import timedelta
# tests/conftest.py
import os, sys
from sqlalchemy.engine.url import make_url
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL not set")

url = make_url(TEST_DATABASE_URL)
if url.drivername in {"postgresql", "postgresql+psycopg2", "postgres"}:
    url = url.set(drivername="postgresql+asyncpg")
TEST_DATABASE_URL = str(url)

print(">> Using TEST_DATABASE_URL:", TEST_DATABASE_URL, file=sys.stderr)
print(">> Driver:", make_url(TEST_DATABASE_URL).drivername, file=sys.stderr)

import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base  # avoid importing Database to prevent side effects
from app.dependencies import get_db, get_settings
from app.models.user_model import User, UserRole
from app.utils.security import hash_password
from app.services.email_service import EmailService
from app.services.jwt_service import create_access_token
from app.utils.template_manager import TemplateManager  # if you need it elsewhere

fake = Faker()
settings = get_settings()

# ---- Force async driver for tests ----
RAW_URL = os.getenv("TEST_DATABASE_URL")
if not RAW_URL:
    raise RuntimeError("TEST_DATABASE_URL not set (expected postgresql+asyncpg://...)")

url = make_url(RAW_URL)
if url.drivername in {"postgresql", "postgresql+psycopg2", "postgres"}:
    url = url.set(drivername="postgresql+asyncpg")

TEST_DATABASE_URL = str(url)
print(">> Using TEST_DATABASE_URL:", TEST_DATABASE_URL, file=sys.stderr)
print(">> Driver:", make_url(TEST_DATABASE_URL).drivername, file=sys.stderr)

# One async engine for all tests
engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
AsyncTestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ---- Fixtures ----

@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    # create all tables before each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # drop all tables after each test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session():
    async with AsyncTestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def async_client(db_session):
    async def _override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

# Email service: mocked by default to avoid real sends
@pytest.fixture
def email_service():
    if getattr(settings, "send_real_mail", "false") == "true":
        return EmailService(template_manager=TemplateManager())
    mock_service = AsyncMock(spec=EmailService)
    mock_service.send_verification_email.return_value = None
    mock_service.send_user_email.return_value = None
    return mock_service

# ---- Sample data fixtures ----

@pytest.fixture(scope="function")
async def locked_user(db_session):
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=True,
        failed_login_attempts=settings.max_login_attempts,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def user(db_session):
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def verified_user(db_session):
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=True,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def unverified_user(db_session):
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=hash_password("MySuperPassword$1234"),
        role=UserRole.AUTHENTICATED,
        email_verified=False,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
async def users_with_same_role_50_users(db_session):
    users = []
    for _ in range(50):
        u = User(
            nickname=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            hashed_password=fake.password(),
            role=UserRole.AUTHENTICATED,
            email_verified=False,
            is_locked=False,
        )
        db_session.add(u)
        users.append(u)
    await db_session.commit()
    return users

@pytest.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        nickname="admin_user",
        email="admin@example.com",
        first_name="John",
        last_name="Doe",
        hashed_password="securepassword",
        role=UserRole.ADMIN,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def manager_user(db_session: AsyncSession):
    user = User(
        nickname="manager_john",
        first_name="John",
        last_name="Doe",
        email="manager_user@example.com",
        hashed_password="securepassword",
        role=UserRole.MANAGER,
        is_locked=False,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture(scope="function")
def admin_token(admin_user):
    token_data = {"sub": str(admin_user.id), "role": admin_user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))

@pytest.fixture(scope="function")
def manager_token(manager_user):
    token_data = {"sub": str(manager_user.id), "role": manager_user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))

@pytest.fixture(scope="function")
def user_token(user):
    token_data = {"sub": str(user.id), "role": user.role.name}
    return create_access_token(data=token_data, expires_delta=timedelta(minutes=30))  # typo fixed below
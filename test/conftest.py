import os 
from collections.abc import AsyncGenerator

## Test DB and Bucket
os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://bloguser:blogpass@localhost/test_blog"
)
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

## Dummy S3/AWS Credentials
os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"] = "ap-southeast-2"

os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"

# OS credentials must be defined before import

## App Imports
import boto3
import pytest
from httpx import ASGITransport, AsyncClient # Used to make async test requests to our app
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.app import app


pytest_plugin = ["anyio"] # Help us write async test function

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# A fixture in pytest is a function that sets up something your tests need, then (optionally) tears it down afterward. 
 
@pytest.fixture(scope="session")  # scope='session' define that this fixture will be run once for the entire session rather than once per test
def anyio_backend():
    return "asyncio"

## Test Engine
@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool,    # disable pool connections
    )
    return engine


## Setup Database
@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) # create_all is synchronus function

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # drop all the table 
 
    await test_engine.dispose()

## DB Session (Transactional Rollback)
# This is functional scope 
@pytest.fixture
async def db_session(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    # Create a session that bound to the specific connection but not the engine
    test_async_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",  # fake commit (it looks like commit but it is just created a savepoint)
    )

    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()


## Mocked AWS
# Moto aws is a synchronus process 
# Each test get empty bucket
@pytest.fixture
def mocked_aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name="ap-southeast-2")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"],CreateBucketConfiguration={"LocationConstraint": "ap-southeast-2"})
        yield s3


## Client Fixture
@pytest.fixture
async def client(
    db_session: AsyncSession,
    mocked_aws,
) -> AsyncGenerator[AsyncClient]:

    async def override_get_db():
        yield db_session

    
    # Override the dependency injection that we created for the real production with the test db session
    app.dependency_overrides[get_db] = override_get_db

    # Tie our test client to actual application
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()



## Auth Helpers
async def create_test_user(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> dict:
    response = await client.post(
        "/api/users",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    
    # assert [condition to check], [message when the condition is false]
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    return response.json()


async def login_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> str:
    response = await client.post(
        "/api/users/token",
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}




from datetime import date

import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from src.models.task_models import Priority, TaskCreate, TaskResponse, TaskStatus
from src.repositories.task_repository import TaskRepository


@pytest.fixture
def dynamodb_table():
    with mock_aws():
        import boto3

        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="todo-app-data",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
                {"AttributeName": "GSI3PK", "AttributeType": "S"},
                {"AttributeName": "GSI3SK", "AttributeType": "S"},
                {"AttributeName": "GSI4PK", "AttributeType": "S"},
                {"AttributeName": "GSI4SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI3",
                    "KeySchema": [
                        {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI4",
                    "KeySchema": [
                        {"AttributeName": "GSI4PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI4SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        )
        table.wait_until_exists()
        yield table


@pytest.fixture
def task_repo(dynamodb_table):
    return TaskRepository(table_name="todo-app-data", region="us-east-1")


class TestTaskRepositoryCreate:
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_repo):
        task_create = TaskCreate(
            title="Test Task",
            description="Description",
            priority=Priority.high,
            category="work",
            due_date=date(2023, 10, 1),
        )
        response = await task_repo.create_task("user-123", task_create)
        assert isinstance(response, TaskResponse)
        assert response.title == "Test Task"
        assert response.id != ""
        assert response.status == TaskStatus.pending

    @pytest.mark.asyncio
    async def test_create_task_boundary_values(self, task_repo):
        long_title = "A" * 200
        task_create = TaskCreate(title=long_title, priority=Priority.low)
        response = await task_repo.create_task("user-456", task_create)
        assert response.title == long_title


class TestTaskRepositoryRead:
    @pytest.mark.asyncio
    async def test_get_task_success(self, task_repo):
        task_create = TaskCreate(title="Retrieve Test")
        created = await task_repo.create_task("user-123", task_create)
        response = await task_repo.get_task("user-123", created.id)
        assert response is not None
        assert response.title == "Retrieve Test"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_repo):
        with pytest.raises(ValueError, match="not found"):
            await task_repo.get_task("user-123", "nonexistent")

    @pytest.mark.asyncio
    async def test_get_tasks_success(self, task_repo):
        task1 = TaskCreate(title="Task 1")
        task2 = TaskCreate(title="Task 2")
        await task_repo.create_task("user-123", task1)
        await task_repo.create_task("user-123", task2)
        tasks = await task_repo.get_tasks("user-123")
        assert len(tasks) == 2


class TestTaskRepositoryUpdate:
    @pytest.mark.asyncio
    async def test_update_task_success(self, task_repo):
        task_create = TaskCreate(title="Original")
        created = await task_repo.create_task("user-123", task_create)
        response = await task_repo.update_task(
            "user-123", created.id, {"title": "Updated"}
        )
        assert response.title == "Updated"

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, task_repo):
        with pytest.raises(ValueError, match="not found"):
            await task_repo.update_task("user-123", "nonexistent", {"title": "Fail"})


class TestTaskRepositoryDelete:
    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_repo):
        task_create = TaskCreate(title="Delete Test")
        created = await task_repo.create_task("user-123", task_create)
        await task_repo.delete_task("user-123", created.id)
        with pytest.raises(ValueError, match="not found"):
            await task_repo.get_task("user-123", created.id)

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, task_repo):
        with pytest.raises(ClientError):
            await task_repo.delete_task("user-123", "nonexistent")


class TestTaskRepositoryGSIQueries:
    @pytest.mark.asyncio
    async def test_get_tasks_by_status(self, task_repo):
        task1 = TaskCreate(title="Pending Task", status=TaskStatus.pending)
        task2 = TaskCreate(title="Completed Task", status=TaskStatus.completed)
        await task_repo.create_task("user-123", task1)
        await task_repo.create_task("user-123", task2)
        pending_tasks = await task_repo.get_tasks_by_status(
            "user-123", TaskStatus.pending
        )
        assert len(pending_tasks) == 1
        assert pending_tasks[0].status == TaskStatus.pending

    @pytest.mark.asyncio
    async def test_get_tasks_by_due_date(self, task_repo):
        due_date = date(2023, 10, 1)
        task = TaskCreate(title="Due Task", due_date=due_date)
        await task_repo.create_task("user-123", task)
        tasks = await task_repo.get_tasks_by_due_date("user-123", due_date.isoformat())
        assert len(tasks) == 1

    @pytest.mark.asyncio
    async def test_get_tasks_by_priority(self, task_repo):
        task1 = TaskCreate(title="High Priority", priority=Priority.high)
        task2 = TaskCreate(title="Low Priority", priority=Priority.low)
        await task_repo.create_task("user-123", task1)
        await task_repo.create_task("user-123", task2)
        high_tasks = await task_repo.get_tasks_by_priority("user-123", Priority.high)
        assert len(high_tasks) == 1
        assert high_tasks[0].priority == Priority.high

    @pytest.mark.asyncio
    async def test_get_tasks_by_category(self, task_repo):
        task1 = TaskCreate(title="Work Task", category="work")
        task2 = TaskCreate(title="Personal Task", category="personal")
        await task_repo.create_task("user-123", task1)
        await task_repo.create_task("user-123", task2)
        work_tasks = await task_repo.get_tasks_by_category("user-123", "work")
        assert len(work_tasks) == 1
        assert work_tasks[0].category == "work"


class TestTaskRepositoryErrors:
    @pytest.mark.asyncio
    async def test_dynamodb_client_error_simulation(self, task_repo, mocker):
        mocker.patch.object(
            task_repo.table,
            "put_item",
            side_effect=ClientError(
                {"Error": {"Code": "ThrottlingException"}}, "PutItem"
            ),
        )
        task_create = TaskCreate(title="Fail Task")
        with pytest.raises(ClientError):
            await task_repo.create_task("user-123", task_create)

    @pytest.mark.asyncio
    async def test_invalid_user_id_scoping(self, task_repo):
        task_create = TaskCreate(title="Scoped Task")
        created = await task_repo.create_task("user-123", task_create)
        with pytest.raises(ValueError, match="not found"):
            await task_repo.get_task("user-456", created.id)


class TestTaskRepositoryModelIntegration:
    @pytest.mark.asyncio
    async def test_full_crud_cycle(self, task_repo):
        task_create = TaskCreate(title="Cycle Task", priority=Priority.urgent)
        created = await task_repo.create_task("user-123", task_create)
        assert created.priority == Priority.urgent

        fetched = await task_repo.get_task("user-123", created.id)
        assert fetched.title == "Cycle Task"

        updated = await task_repo.update_task(
            "user-123", created.id, {"title": "Updated Cycle"}
        )
        assert updated.title == "Updated Cycle"

        await task_repo.delete_task("user-123", created.id)
        with pytest.raises(ValueError, match="not found"):
            await task_repo.get_task("user-123", created.id)

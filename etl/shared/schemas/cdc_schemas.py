from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class EventType(str, Enum):
    """DynamoDB Streams event types"""

    INSERT = "INSERT"
    MODIFY = "MODIFY"
    REMOVE = "REMOVE"


class EntityType(str, Enum):
    """Entity types in the system"""

    USER = "USER"
    TASK = "TASK"
    IDEMPOTENCY = "IDEMPOTENCY"


class TaskStatus(str, Enum):
    """Task status values"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UserVerificationStatus(str, Enum):
    """User verification status"""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class CdcEvent(BaseModel):
    """CDC event from DynamoDB Streams"""

    event_name: EventType
    event_time: datetime
    sequence_number: str
    table_name: str
    processed_at: datetime
    partition_key: Optional[str] = None
    data: Dict[str, Any]


class UserData(BaseModel):
    """User entity data"""

    user_id: str
    email: str
    name: str
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    last_login: Optional[datetime] = None
    login_count: int = 0
    is_active: bool = True
    verification_status: UserVerificationStatus = UserVerificationStatus.PENDING
    created_at: datetime
    updated_at: datetime


class TaskData(BaseModel):
    """Task entity data"""

    task_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class IdempotencyData(BaseModel):
    """Idempotency entity data"""

    idempotency_key: str
    user_id: str
    operation: str
    created_at: datetime
    expires_at: datetime


class ProcessedCdcEvent(BaseModel):
    """Processed CDC event for Firehose"""

    event_name: EventType
    event_time: datetime
    sequence_number: str
    table_name: str
    processed_at: datetime
    partition_key: Optional[str] = None
    data: Dict[str, Any]
    year: int
    month: int
    day: int


class UserAnalytics(BaseModel):
    """User analytics data"""

    user_id: str
    email: str
    name: str
    is_active: bool
    verification_status: UserVerificationStatus
    first_seen: datetime
    last_login: Optional[datetime] = None
    total_logins: int = 0
    data_points: int = 0
    activity_types: int = 0
    days_since_last_login: Optional[int] = None
    engagement_level: str
    user_segment: str


class TaskAnalytics(BaseModel):
    """Task analytics data"""

    user_id: str
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    high_priority_tasks: int
    medium_priority_tasks: int
    low_priority_tasks: int
    categories_used: int
    first_task_date: datetime
    last_task_date: datetime
    completion_rate: float
    productivity_score: float


class CategoryTrends(BaseModel):
    """Category trends data"""

    category: str
    total_tasks: int
    completed_tasks: int
    high_priority_tasks: int
    avg_completion_days: Optional[float] = None
    completion_rate: float


class BusinessKpi(BaseModel):
    """Business KPI data"""

    metric: str
    value: float


class DailyActiveUsers(BaseModel):
    """Daily active users data"""

    date: str
    active_users: int


class TaskCompletionTrends(BaseModel):
    """Task completion trends data"""

    date: str
    completed_tasks: int


class UserGrowth(BaseModel):
    """User growth data"""

    date: str
    new_users: int
    cumulative_users: int


class GlueTableSchema(BaseModel):
    """Glue table schema definition"""

    name: str
    database: str
    columns: List[Dict[str, Any]]
    partition_keys: List[str]
    table_type: str = "EXTERNAL_TABLE"
    input_format: str = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format: str = (
        "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    )
    serde_info: Dict[str, str] = {
        "serializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }
    location: str
    parameters: Dict[str, str] = {}


class GlueDatabaseSchema(BaseModel):
    """Glue database schema definition"""

    name: str
    description: str
    location_uri: str
    parameters: Dict[str, str] = {}


class PartitioningStrategy(BaseModel):
    """Data partitioning strategy"""

    partition_keys: List[str]
    partition_format: str
    date_format: str = "yyyy-MM-dd"
    time_format: str = "HH:mm:ss"


class DataQualityRules(BaseModel):
    """Data quality rules"""

    required_fields: List[str]
    data_types: Dict[str, str]
    constraints: Dict[str, Any]
    validation_rules: List[str]


class ETLJobConfig(BaseModel):
    """ETL job configuration"""

    job_name: str
    job_type: str
    source_bucket: str
    target_bucket: str
    database_name: str
    partitioning_strategy: PartitioningStrategy
    data_quality_rules: DataQualityRules
    processing_schedule: str
    max_capacity: int = 2
    timeout: int = 60
    glue_version: str = "4.0"

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Float, Boolean, Date,
    DateTime, SmallInteger, Numeric, Enum, ForeignKey, JSON, ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PG_ENUM
from app.database import RemoteBase, LocalBase

# Remote DB ENUM types
quarter_enum = PG_ENUM('Q1', 'Q2', 'Q3', 'Q4', name='quarter_enum', create_type=False)
goal_status_enum = PG_ENUM(
    'draft', 'active', 'submitted', 'approved', 'in_progress',
    'done', 'cancelled', 'overdue', 'archived',
    name='goal_status_enum', create_type=False,
)


# ========== REMOTE MODELS (read-only from 95.47.96.41) ==========

class Department(RemoteBase):
    __tablename__ = "departments"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    code = Column(Text, nullable=True)
    parent_id = Column(BigInteger, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class Position(RemoteBase):
    __tablename__ = "positions"

    id = Column(BigInteger, primary_key=True)
    name = Column(Text, nullable=False)
    grade = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class Employee(RemoteBase):
    __tablename__ = "employees"

    id = Column(BigInteger, primary_key=True)
    employee_code = Column(Text, nullable=True)
    full_name = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    department_id = Column(BigInteger, nullable=False)
    position_id = Column(BigInteger, nullable=False)
    manager_id = Column(BigInteger, nullable=True)
    hire_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class Goal(RemoteBase):
    __tablename__ = "goals"

    goal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(BigInteger, nullable=False)
    department_id = Column(BigInteger, nullable=False)
    employee_name_snapshot = Column(Text, nullable=True)
    position_snapshot = Column(Text, nullable=True)
    department_name_snapshot = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    system_id = Column(BigInteger, nullable=True)
    goal_text = Column(Text, nullable=False)
    year = Column(SmallInteger, nullable=False)
    quarter = Column(quarter_enum, nullable=False)
    metric = Column(Text, nullable=True)
    deadline = Column(Date, nullable=True)
    weight = Column(Numeric, nullable=False)
    status = Column(goal_status_enum, nullable=False)
    external_ref = Column(Text, nullable=True)
    priority = Column(SmallInteger, nullable=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class GoalEvent(RemoteBase):
    __tablename__ = "goal_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(Text, nullable=False)
    actor_id = Column(BigInteger, nullable=True)
    old_status = Column(Text, nullable=True)
    new_status = Column(Text, nullable=True)
    old_text = Column(Text, nullable=True)
    new_text = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True))


class GoalReview(RemoteBase):
    __tablename__ = "goal_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), nullable=False)
    reviewer_id = Column(BigInteger, nullable=True)
    verdict = Column(Text, nullable=False)
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True))


class Document(RemoteBase):
    __tablename__ = "documents"

    doc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doc_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    owner_department_id = Column(BigInteger, nullable=True)
    department_scope = Column(JSONB, nullable=True)
    keywords = Column(ARRAY(Text), nullable=True)
    version = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class KpiCatalog(RemoteBase):
    __tablename__ = "kpi_catalog"

    metric_key = Column(Text, primary_key=True)
    title = Column(Text, nullable=False)
    unit = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))


class KpiTimeseries(RemoteBase):
    __tablename__ = "kpi_timeseries"

    id = Column(BigInteger, primary_key=True)
    scope_type = Column(Text, nullable=False)
    department_id = Column(BigInteger, nullable=True)
    employee_id = Column(BigInteger, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    system_id = Column(BigInteger, nullable=True)
    metric_key = Column(Text, nullable=False)
    period_date = Column(Date, nullable=False)
    value_num = Column(Numeric, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True))


# ========== LOCAL MODELS (read-write, AI results) ==========

class AiEvaluation(LocalBase):
    __tablename__ = "ai_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    goal_id = Column(Text, nullable=True)  # UUID as string from remote
    employee_id = Column(BigInteger)
    goal_text = Column(Text)
    scores_json = Column(JSON)
    overall_index = Column(Float)
    goal_type = Column(String(20))
    alignment_level = Column(String(20))
    alignment_source = Column(Text, nullable=True)
    recommendations = Column(JSON)
    reformulation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AiGeneratedGoals(LocalBase):
    __tablename__ = "ai_generated_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(BigInteger)
    quarter = Column(String(2))
    year = Column(Integer)
    goals_json = Column(JSON)
    context_json = Column(JSON, nullable=True)
    warnings = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AcceptedGoals(LocalBase):
    __tablename__ = "accepted_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(BigInteger, nullable=False)
    quarter = Column(String(2), nullable=False)
    year = Column(Integer, nullable=False)
    goals_json = Column(JSON, nullable=False)   # list of accepted GeneratedGoal dicts
    accepted_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

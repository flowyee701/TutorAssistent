# core/db/models.py
# SQLAlchemy 2.0 модели для AI-ассистента репетиторов (Telegram-бот + Mini App)
# PostgreSQL 16 + pgvector

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer,
    String, Text, UniqueConstraint, Index, func,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
# from pgvector.sqlalchemy import Vector  # подключить при добавлении эмбеддингов


class Base(DeclarativeBase):
    pass


# =========================================
# Перечисления
# =========================================

class Subject(str, enum.Enum):
    MATH_PROFILE = "MATH_PROFILE"
    MATH_BASE = "MATH_BASE"
    PHYSICS = "PHYSICS"
    INFORMATICS = "INFORMATICS"


class ExamType(str, enum.Enum):
    OGE = "OGE"
    EGE = "EGE"


class SubscriptionPlan(str, enum.Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    PRO = "PRO"
    PREMIUM = "PREMIUM"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    GRACE_PERIOD = "GRACE_PERIOD"


class VerificationStatus(str, enum.Enum):
    AUTO_PARSED = "AUTO_PARSED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    COMMUNITY_VERIFIED = "COMMUNITY_VERIFIED"
    FLAGGED = "FLAGGED"


class HomeworkStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    GENERATED = "GENERATED"
    ARCHIVED = "ARCHIVED"


class HomeworkFormat(str, enum.Enum):
    WARMUP = "WARMUP"
    HOMEWORK_BY_TOPIC = "HOMEWORK_BY_TOPIC"
    TEST = "TEST"
    EGE_VARIANT = "EGE_VARIANT"
    CUSTOM = "CUSTOM"


class MaterialStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


# =========================================
# Пользователи и подписки
# =========================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscription: Mapped["Subscription"] = relationship(back_populates="user", uselist=False)
    students: Mapped[list["Student"]] = relationship(back_populates="tutor")
    homeworks: Mapped[list["Homework"]] = relationship(back_populates="tutor")
    owned_tasks: Mapped[list["Task"]] = relationship(back_populates="owner")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Счётчик ДЗ за текущий период (для лимитов)
    homeworks_this_period: Mapped[int] = mapped_column(Integer, default=0)
    period_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Рекуррент ЮKassa
    yukassa_payment_method_id: Mapped[str | None] = mapped_column(String(255))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="subscription")
    payments: Mapped[list["PaymentRecord"]] = relationship(back_populates="subscription")

    __table_args__ = (Index("ix_sub_status_end", "status", "end_date"),)


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    amount_kopecks: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(String(32))  # succeeded, pending, canceled
    yukassa_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subscription: Mapped["Subscription"] = relationship(back_populates="payments")


# =========================================
# Ученики
# =========================================

class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    grade: Mapped[int | None] = mapped_column(Integer)
    exam_target: Mapped[ExamType | None] = mapped_column(Enum(ExamType))
    subject: Mapped[Subject | None] = mapped_column(Enum(Subject))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tutor: Mapped["User"] = relationship(back_populates="students")
    weak_topics: Mapped[list["StudentWeakTopic"]] = relationship(back_populates="student")


class StudentWeakTopic(Base):
    __tablename__ = "student_weak_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("task_tags.id"))
    severity: Mapped[int] = mapped_column(Integer, default=2)  # 1-3
    notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped["Student"] = relationship(back_populates="weak_topics")
    tag: Mapped["TaskTag"] = relationship()

    __table_args__ = (UniqueConstraint("student_id", "tag_id"),)


# =========================================
# Дерево тегов
# =========================================

class TaskTag(Base):
    __tablename__ = "task_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(255), unique=True)
    path: Mapped[str] = mapped_column(String(512), unique=True, index=True)  # algebra.equations.quadratic
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[Subject] = mapped_column(Enum(Subject))
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("task_tags.id"))
    depth: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    children: Mapped[list["TaskTag"]] = relationship()

    __table_args__ = (Index("ix_tag_subject_exam", "subject", "exam_type"),)


# =========================================
# Задачи
# =========================================

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[Subject] = mapped_column(Enum(Subject))
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType))
    task_number: Mapped[int | None] = mapped_column(Integer)  # № задания ЕГЭ
    difficulty: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    source: Mapped[str] = mapped_column(String(255))  # FIPI_2024_DEMO, USER_UPLOAD...
    source_metadata: Mapped[dict | None] = mapped_column(JSONB)

    statement_latex: Mapped[str] = mapped_column(Text)
    statement_text: Mapped[str] = mapped_column(Text)  # plain для full-text search
    image_urls: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    answer: Mapped[str | None] = mapped_column(Text)
    solution_latex: Mapped[str | None] = mapped_column(Text)

    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # NULL = общий банк
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.AUTO_PARSED
    )
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 statement_text
    flag_count: Mapped[int] = mapped_column(Integer, default=0)

    # embedding: Mapped[list[float] | None] = mapped_column(Vector(256))  # pgvector, позже

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped["User"] = relationship(back_populates="owned_tasks")
    tag_links: Mapped[list["TaskTagLink"]] = relationship(back_populates="task")

    __table_args__ = (
        Index("ix_task_subject_exam", "subject", "exam_type"),
        Index("ix_task_verif", "verification_status"),
        Index("ix_task_owner", "owner_id"),
        Index("ix_task_difficulty", "difficulty"),
    )


class TaskTagLink(Base):
    __tablename__ = "task_tag_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("task_tags.id"), index=True)

    task: Mapped["Task"] = relationship(back_populates="tag_links")
    tag: Mapped["TaskTag"] = relationship()

    __table_args__ = (UniqueConstraint("task_id", "tag_id"),)


# =========================================
# Домашние задания
# =========================================

class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[HomeworkFormat] = mapped_column(Enum(HomeworkFormat), default=HomeworkFormat.HOMEWORK_BY_TOPIC)
    status: Mapped[HomeworkStatus] = mapped_column(Enum(HomeworkStatus), default=HomeworkStatus.DRAFT)
    pdf_url: Mapped[str | None] = mapped_column(String(512))
    pdf_answers_url: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tutor: Mapped["User"] = relationship(back_populates="homeworks")
    tasks: Mapped[list["HomeworkTask"]] = relationship(back_populates="homework", order_by="HomeworkTask.order")


class HomeworkTask(Base):
    __tablename__ = "homework_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    homework_id: Mapped[int] = mapped_column(ForeignKey("homeworks.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    order: Mapped[int] = mapped_column(Integer)

    homework: Mapped["Homework"] = relationship(back_populates="tasks")
    task: Mapped["Task"] = relationship()

    __table_args__ = (UniqueConstraint("homework_id", "order"),)


# =========================================
# Ведомости занятий
# =========================================

class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topics: Mapped[list["LessonTopic"]] = relationship(back_populates="lesson")


class LessonTopic(Base):
    __tablename__ = "lesson_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("task_tags.id"))
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    lesson: Mapped["Lesson"] = relationship(back_populates="topics")
    tag: Mapped["TaskTag"] = relationship()

    __table_args__ = (UniqueConstraint("lesson_id", "tag_id"),)


# =========================================
# Учёт оплат ученика репетитору (не подписка!)
# =========================================

class StudentPayment(Base):
    __tablename__ = "student_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    amount_kopecks: Mapped[int] = mapped_column(Integer)
    lessons_count: Mapped[int] = mapped_column(Integer)  # на сколько занятий
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


# =========================================
# Методички (позже)
# =========================================

class TutorMaterial(Base):
    __tablename__ = "tutor_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    tutor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    s3_key: Mapped[str] = mapped_column(String(512))
    file_size: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[MaterialStatus] = mapped_column(Enum(MaterialStatus), default=MaterialStatus.UPLOADED)
    extracted_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# =========================================
# Лог вызовов LLM (для отладки и unit-экономики)
# =========================================

class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    purpose: Mapped[str] = mapped_column(String(64))  # parse_query, tag_task, ...
    model: Mapped[str] = mapped_column(String(64))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_kopecks: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

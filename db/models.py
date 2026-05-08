import uuid
import datetime
from sqlalchemy import Column, Text, Integer, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    status = Column(Text, default="pending")
    source_dialect = Column(Text, nullable=False)
    target_dialect = Column(Text, nullable=False)
    input_hash = Column(Text)
    statement_count = Column(Integer, default=0)
    done_count = Column(Integer, default=0)
    quality_avg = Column(Float)
    statements = relationship("Statement", back_populates="job")


class Statement(Base):
    __tablename__ = "statements"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(Text, ForeignKey("jobs.id"), nullable=False)
    position = Column(Integer, nullable=False)
    original_sql = Column(Text, nullable=False)
    modernized_sql = Column(Text)
    quality_score = Column(Integer)
    validation_pass = Column(Boolean, default=False)
    retries = Column(Integer, default=0)
    flag = Column(Text)
    processing_ms = Column(Integer)
    job = relationship("Job", back_populates="statements")
    optimizations = relationship("Optimization", back_populates="statement")


class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = Column(Text, ForeignKey("statements.id"), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    statement = relationship("Statement", back_populates="optimizations")


class Cache(Base):
    __tablename__ = "cache"
    input_hash = Column(Text, primary_key=True)
    target_dialect = Column(Text, primary_key=True)
    modernized_sql = Column(Text, nullable=False)
    quality_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

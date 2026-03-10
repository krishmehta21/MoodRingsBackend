from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, SmallInteger, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.sql import func
import uuid
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invite_code = Column(String(6), nullable=True)
    invite_code_expires_at = Column(DateTime(timezone=True), nullable=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Profile fields
    display_name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    relationship_type = Column(String, nullable=True)
    together_duration = Column(String, nullable=True)
    anniversary_date = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    profile_complete = Column(Boolean, default=False, server_default='false', nullable=False)
    
    partner = relationship("User", remote_side=[id])

class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    logged_at = Column(DateTime(timezone=True), server_default=func.now())  # now a timestamp
    score = Column(SmallInteger, nullable=False)
    emotion_tags = Column(ARRAY(String), nullable=True)
    journal_text = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    calendar_stress = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # UniqueConstraint REMOVED

class RiskScore(Base):
    __tablename__ = "risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    couple_id = Column(UUID(as_uuid=True), nullable=False)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())
    p_stress = Column(Float, nullable=False)
    features_snapshot = Column(JSONB, nullable=True)
    suggestion_triggered = Column(Boolean, default=False)

class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    couple_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tier = Column(String, nullable=False)
    message = Column(String, nullable=False)
    actions = Column(ARRAY(String), nullable=True)
    acted_on = Column(Boolean, default=False)
    acted_on_at = Column(DateTime(timezone=True), nullable=True)
"""
Challenge database models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum as SQLEnum, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ChallengeCategory(str, enum.Enum):
    INVISCID_FLOW = "inviscid_flow"
    VISCOUS_EFFECTS = "viscous_effects"
    STALL_PREDICTION = "stall_prediction"
    DRAG_OPTIMIZATION = "drag_optimization"
    LIFT_OPTIMIZATION = "lift_optimization"
    MULTI_ELEMENT = "multi_element"
    DESIGN = "design"


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=False)
    category = Column(SQLEnum(ChallengeCategory), nullable=False)

    # Challenge configuration
    constraints = Column(JSON, nullable=False)
    # Example: {
    #   "airfoil_type": "naca_4digit",
    #   "airfoil_options": ["0012", "2412", "4412"],
    #   "reynolds_range": [1e5, 1e7],
    #   "alpha_range": [-5, 20],
    #   "max_simulations": 10
    # }

    validation_criteria = Column(JSON, nullable=False)
    # Example: {
    #   "target_cl_max": 1.45,
    #   "tolerance": 0.05,
    #   "check_alpha_stall": true,
    #   "max_cd": 0.01
    # }

    # Educational content
    hints = Column(JSON)  # List of progressive hints
    # Example: [
    #   "Start by visualizing the Cp distribution",
    #   "Look for flow separation indicators",
    #   "Try increasing the angle of attack gradually"
    # ]

    learning_objectives = Column(JSON)  # List of learning objectives
    reference_solution = Column(JSON)  # Reference solution data (hidden from users)

    # Metadata
    points = Column(Integer, default=100)  # Points awarded for completion
    order = Column(Integer, default=0)  # Display order
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    simulations = relationship("Simulation", back_populates="challenge")
    submissions = relationship("ChallengeSubmission", back_populates="challenge")

    def __repr__(self):
        return f"<Challenge(title='{self.title}', difficulty='{self.difficulty}')>"


class ChallengeSubmission(Base):
    __tablename__ = "challenge_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    challenge_id = Column(UUID(as_uuid=True), ForeignKey("challenges.id"), nullable=False)
    simulation_id = Column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)

    # Validation results
    is_correct = Column(Boolean, nullable=False)
    validation_results = Column(JSON)  # Detailed validation breakdown
    # Example: {
    #   "cl_max_achieved": 1.47,
    #   "cl_max_target": 1.45,
    #   "meets_tolerance": true,
    #   "alpha_stall": 14.5,
    #   "score": 95
    # }

    score = Column(Integer)  # Score out of 100
    time_taken_seconds = Column(Integer)  # Time to solve
    attempts = Column(Integer, default=1)  # Number of attempts

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="challenge_submissions")
    challenge = relationship("Challenge", back_populates="submissions")
    simulation = relationship("Simulation")

    def __repr__(self):
        return f"<ChallengeSubmission(user_id='{self.user_id}', challenge_id='{self.challenge_id}', correct={self.is_correct})>"

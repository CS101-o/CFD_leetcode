"""
Simulation database model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class SimulationStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SolverType(str, enum.Enum):
    XFOIL = "xfoil"
    PINN = "pinn"
    OPENFOAM = "openfoam"


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    challenge_id = Column(UUID(as_uuid=True), ForeignKey("challenges.id"), nullable=True)

    # Simulation configuration
    airfoil_type = Column(String(50), nullable=False)  # "naca_4digit", "naca_5digit", "custom"
    airfoil_designation = Column(String(50))  # e.g., "0012", "2412"
    airfoil_coords = Column(JSON)  # Store airfoil coordinates if custom

    # Flow parameters
    alpha = Column(Float, nullable=False)  # Angle of attack (degrees)
    reynolds = Column(Float, nullable=False)  # Reynolds number
    mach = Column(Float, default=0.0)  # Mach number
    n_crit = Column(Float, default=9.0)  # Critical amplification factor

    # Solver configuration
    solver_type = Column(SQLEnum(SolverType), default=SolverType.XFOIL)
    viscous = Column(JSON, default=True)  # Enable viscous analysis
    max_iterations = Column(Integer, default=100)

    # Status
    status = Column(SQLEnum(SimulationStatus), default=SimulationStatus.QUEUED)
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    error_message = Column(String(500))

    # Results (stored as JSON)
    results = Column(JSON)  # {cl, cd, cdp, cm, top_xtr, bot_xtr, converged, cp_distribution, ...}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="simulations")
    challenge = relationship("Challenge", back_populates="simulations")

    def __repr__(self):
        return f"<Simulation(id='{self.id}', airfoil='{self.airfoil_designation}', alpha={self.alpha})>"

    @property
    def runtime_seconds(self) -> float:
        """Calculate simulation runtime in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

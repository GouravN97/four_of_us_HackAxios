"""
Patient repository for CRUD operations on patient records.
Handles patient registration, retrieval, and unique ID generation.
"""

import logging
import secrets
import string
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from src.models.db_models import Patient, ArrivalModeEnum

logger = logging.getLogger(__name__)


class PatientRepository:
    """Repository for patient data access operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def generate_unique_patient_id(self, max_attempts: int = 10) -> str:
        """
        Generate a unique patient ID.
        
        Uses a combination of timestamp and random characters to ensure uniqueness.
        Format: P{YYYYMMDD}{HHMMSS}{RANDOM}
        
        Args:
            max_attempts: Maximum attempts to generate unique ID
            
        Returns:
            Unique patient ID string
            
        Raises:
            RuntimeError: If unable to generate unique ID after max attempts
        """
        for attempt in range(max_attempts):
            # Create timestamp-based prefix
            now = datetime.utcnow()
            timestamp_part = now.strftime("%Y%m%d%H%M%S")
            
            # Add random suffix for uniqueness
            random_chars = ''.join(secrets.choice(string.ascii_uppercase + string.digits) 
                                 for _ in range(4))
            
            patient_id = f"P{timestamp_part}{random_chars}"
            
            # Check if ID already exists
            if not self.exists(patient_id):
                return patient_id
                
            logger.warning(f"Patient ID collision on attempt {attempt + 1}: {patient_id}")
        
        raise RuntimeError(f"Failed to generate unique patient ID after {max_attempts} attempts")
    
    def create(self, patient_id: Optional[str], arrival_mode: ArrivalModeEnum, 
               acuity_level: int) -> Patient:
        """
        Create a new patient record.
        
        Args:
            patient_id: Optional patient ID (will generate if None)
            arrival_mode: How the patient arrived
            acuity_level: Clinical severity rating (1-5)
            
        Returns:
            Created patient record
            
        Raises:
            ValueError: If acuity level is invalid
            IntegrityError: If patient ID already exists
            SQLAlchemyError: For database errors
        """
        # Validate acuity level
        if not (1 <= acuity_level <= 5):
            raise ValueError(f"Acuity level must be between 1 and 5, got {acuity_level}")
        
        # Generate patient ID if not provided
        if patient_id is None:
            patient_id = self.generate_unique_patient_id()
        
        try:
            patient = Patient(
                patient_id=patient_id,
                arrival_mode=arrival_mode,
                acuity_level=acuity_level,
                registration_time=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)
            
            logger.info(f"Created patient: {patient_id}")
            return patient
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Patient ID already exists: {patient_id}")
            raise IntegrityError(f"Patient with ID {patient_id} already exists", 
                               orig=e.orig, params=e.params)
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating patient {patient_id}: {e}")
            raise
    
    def get_by_id(self, patient_id: str, include_relations: bool = False) -> Optional[Patient]:
        """
        Retrieve patient by ID.
        
        Args:
            patient_id: Patient identifier
            include_relations: Whether to eagerly load vital signs and risk assessments
            
        Returns:
            Patient record if found, None otherwise
        """
        try:
            query = self.db.query(Patient).filter(Patient.patient_id == patient_id)
            
            if include_relations:
                query = query.options(
                    selectinload(Patient.vital_signs),
                    selectinload(Patient.risk_assessments)
                )
            
            patient = query.first()
            
            if patient:
                logger.debug(f"Retrieved patient: {patient_id}")
            else:
                logger.debug(f"Patient not found: {patient_id}")
                
            return patient
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patient {patient_id}: {e}")
            raise
    
    def exists(self, patient_id: str) -> bool:
        """
        Check if patient exists.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if patient exists, False otherwise
        """
        try:
            count = self.db.query(Patient).filter(Patient.patient_id == patient_id).count()
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Database error checking patient existence {patient_id}: {e}")
            raise
    
    def update_last_updated(self, patient_id: str) -> bool:
        """
        Update the last_updated timestamp for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if updated successfully, False if patient not found
        """
        try:
            patient = self.get_by_id(patient_id)
            if not patient:
                return False
            
            patient.last_updated = datetime.utcnow()
            self.db.commit()
            
            logger.debug(f"Updated last_updated for patient: {patient_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating patient {patient_id}: {e}")
            raise
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Patient]:
        """
        Retrieve all patients with optional pagination.
        
        Args:
            limit: Maximum number of patients to return
            offset: Number of patients to skip
            
        Returns:
            List of patient records
        """
        try:
            query = self.db.query(Patient).order_by(Patient.registration_time.desc())
            
            if offset > 0:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            
            patients = query.all()
            logger.debug(f"Retrieved {len(patients)} patients")
            return patients
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patients: {e}")
            raise
    
    def get_by_arrival_mode(self, arrival_mode: ArrivalModeEnum) -> List[Patient]:
        """
        Retrieve patients by arrival mode.
        
        Args:
            arrival_mode: Arrival mode to filter by
            
        Returns:
            List of patients with specified arrival mode
        """
        try:
            patients = (self.db.query(Patient)
                       .filter(Patient.arrival_mode == arrival_mode)
                       .order_by(Patient.registration_time.desc())
                       .all())
            
            logger.debug(f"Retrieved {len(patients)} patients with arrival mode: {arrival_mode}")
            return patients
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patients by arrival mode {arrival_mode}: {e}")
            raise
    
    def get_by_acuity_level(self, acuity_level: int) -> List[Patient]:
        """
        Retrieve patients by acuity level.
        
        Args:
            acuity_level: Acuity level to filter by (1-5)
            
        Returns:
            List of patients with specified acuity level
        """
        try:
            patients = (self.db.query(Patient)
                       .filter(Patient.acuity_level == acuity_level)
                       .order_by(Patient.registration_time.desc())
                       .all())
            
            logger.debug(f"Retrieved {len(patients)} patients with acuity level: {acuity_level}")
            return patients
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patients by acuity level {acuity_level}: {e}")
            raise
    
    def delete(self, patient_id: str) -> bool:
        """
        Delete a patient record.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            True if deleted successfully, False if patient not found
        """
        try:
            patient = self.get_by_id(patient_id)
            if not patient:
                return False
            
            self.db.delete(patient)
            self.db.commit()
            
            logger.info(f"Deleted patient: {patient_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting patient {patient_id}: {e}")
            raise
    
    def count(self) -> int:
        """
        Get total count of patients.
        
        Returns:
            Total number of patients in the system
        """
        try:
            count = self.db.query(Patient).count()
            logger.debug(f"Total patient count: {count}")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Database error counting patients: {e}")
            raise
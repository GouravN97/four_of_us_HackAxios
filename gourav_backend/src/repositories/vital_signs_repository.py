"""
Vital signs repository for time-series storage and retrieval.
Handles vital signs CRUD operations with timestamp-based queries.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.db_models import VitalSigns

logger = logging.getLogger(__name__)


class VitalSignsRepository:
    """Repository for vital signs time-series data access operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, patient_id: str, heart_rate: float, systolic_bp: float,
               diastolic_bp: float, respiratory_rate: float, oxygen_saturation: float,
               temperature: float, timestamp: Optional[datetime] = None,
               recorded_by: Optional[str] = None) -> VitalSigns:
        """
        Create a new vital signs record.
        
        Args:
            patient_id: Patient identifier
            heart_rate: Heart rate in bpm
            systolic_bp: Systolic blood pressure in mmHg
            diastolic_bp: Diastolic blood pressure in mmHg
            respiratory_rate: Respiratory rate in breaths/min
            oxygen_saturation: Oxygen saturation percentage
            temperature: Body temperature in Celsius
            timestamp: When vital signs were recorded (defaults to now)
            recorded_by: Who recorded the vital signs
            
        Returns:
            Created vital signs record
            
        Raises:
            SQLAlchemyError: For database errors
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Ensure timestamp is timezone-naive for consistent storage
        if timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        
        try:
            vital_signs = VitalSigns(
                id=str(uuid4()),
                patient_id=patient_id,
                heart_rate=heart_rate,
                systolic_bp=systolic_bp,
                diastolic_bp=diastolic_bp,
                respiratory_rate=respiratory_rate,
                oxygen_saturation=oxygen_saturation,
                temperature=temperature,
                timestamp=timestamp,
                recorded_by=recorded_by,
                created_at=datetime.utcnow()
            )
            
            self.db.add(vital_signs)
            self.db.commit()
            self.db.refresh(vital_signs)
            
            logger.info(f"Created vital signs record for patient {patient_id}: {vital_signs.id}")
            return vital_signs
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating vital signs for patient {patient_id}: {e}")
            raise
    
    def get_by_id(self, vital_signs_id: str) -> Optional[VitalSigns]:
        """
        Retrieve vital signs record by ID.
        
        Args:
            vital_signs_id: Vital signs record identifier
            
        Returns:
            Vital signs record if found, None otherwise
        """
        try:
            vital_signs = (self.db.query(VitalSigns)
                          .filter(VitalSigns.id == vital_signs_id)
                          .first())
            
            if vital_signs:
                logger.debug(f"Retrieved vital signs: {vital_signs_id}")
            else:
                logger.debug(f"Vital signs not found: {vital_signs_id}")
                
            return vital_signs
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving vital signs {vital_signs_id}: {e}")
            raise
    
    def get_latest_for_patient(self, patient_id: str) -> Optional[VitalSigns]:
        """
        Get the most recent vital signs for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest vital signs record if found, None otherwise
        """
        try:
            vital_signs = (self.db.query(VitalSigns)
                          .filter(VitalSigns.patient_id == patient_id)
                          .order_by(desc(VitalSigns.timestamp))
                          .first())
            
            if vital_signs:
                logger.debug(f"Retrieved latest vital signs for patient {patient_id}")
            else:
                logger.debug(f"No vital signs found for patient {patient_id}")
                
            return vital_signs
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving latest vital signs for patient {patient_id}: {e}")
            raise
    
    def get_for_patient(self, patient_id: str, limit: Optional[int] = None,
                       offset: int = 0) -> List[VitalSigns]:
        """
        Get all vital signs for a patient, ordered by timestamp (newest first).
        
        Args:
            patient_id: Patient identifier
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of vital signs records
        """
        try:
            query = (self.db.query(VitalSigns)
                    .filter(VitalSigns.patient_id == patient_id)
                    .order_by(desc(VitalSigns.timestamp)))
            
            if offset > 0:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            
            vital_signs_list = query.all()
            logger.debug(f"Retrieved {len(vital_signs_list)} vital signs records for patient {patient_id}")
            return vital_signs_list
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving vital signs for patient {patient_id}: {e}")
            raise
    
    def get_for_patient_in_time_range(self, patient_id: str, start_time: datetime,
                                     end_time: datetime) -> List[VitalSigns]:
        """
        Get vital signs for a patient within a specific time range.
        
        Args:
            patient_id: Patient identifier
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            
        Returns:
            List of vital signs records in chronological order (oldest first)
        """
        try:
            # Ensure timestamps are timezone-naive for consistent comparison
            if start_time.tzinfo is not None:
                start_time = start_time.replace(tzinfo=None)
            if end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)
            
            vital_signs_list = (self.db.query(VitalSigns)
                               .filter(and_(
                                   VitalSigns.patient_id == patient_id,
                                   VitalSigns.timestamp >= start_time,
                                   VitalSigns.timestamp <= end_time
                               ))
                               .order_by(VitalSigns.timestamp)  # Oldest first for time range queries
                               .all())
            
            logger.debug(f"Retrieved {len(vital_signs_list)} vital signs records for patient {patient_id} "
                        f"between {start_time} and {end_time}")
            return vital_signs_list
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving vital signs for patient {patient_id} "
                        f"in time range {start_time} to {end_time}: {e}")
            raise
    
    def get_recent_for_patient(self, patient_id: str, hours: int = 24) -> List[VitalSigns]:
        """
        Get recent vital signs for a patient within the last N hours.
        
        Args:
            patient_id: Patient identifier
            hours: Number of hours to look back
            
        Returns:
            List of vital signs records in chronological order (oldest first)
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        return self.get_for_patient_in_time_range(patient_id, start_time, end_time)
    
    def get_count_for_patient(self, patient_id: str) -> int:
        """
        Get count of vital signs records for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Number of vital signs records
        """
        try:
            count = (self.db.query(VitalSigns)
                    .filter(VitalSigns.patient_id == patient_id)
                    .count())
            
            logger.debug(f"Patient {patient_id} has {count} vital signs records")
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Database error counting vital signs for patient {patient_id}: {e}")
            raise
    
    def get_time_range_for_patient(self, patient_id: str) -> Optional[Tuple[datetime, datetime]]:
        """
        Get the time range (earliest to latest) of vital signs for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Tuple of (earliest_timestamp, latest_timestamp) or None if no records
        """
        try:
            result = (self.db.query(
                        func.min(VitalSigns.timestamp).label('earliest'),
                        func.max(VitalSigns.timestamp).label('latest')
                      )
                      .filter(VitalSigns.patient_id == patient_id)
                      .first())
            
            if result and result.earliest and result.latest:
                logger.debug(f"Patient {patient_id} vital signs range: {result.earliest} to {result.latest}")
                return (result.earliest, result.latest)
            else:
                logger.debug(f"No vital signs time range found for patient {patient_id}")
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting time range for patient {patient_id}: {e}")
            raise
    
    def delete_for_patient(self, patient_id: str) -> int:
        """
        Delete all vital signs records for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Number of records deleted
        """
        try:
            count = (self.db.query(VitalSigns)
                    .filter(VitalSigns.patient_id == patient_id)
                    .count())
            
            self.db.query(VitalSigns).filter(VitalSigns.patient_id == patient_id).delete()
            self.db.commit()
            
            logger.info(f"Deleted {count} vital signs records for patient {patient_id}")
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting vital signs for patient {patient_id}: {e}")
            raise
    
    def delete_by_id(self, vital_signs_id: str) -> bool:
        """
        Delete a specific vital signs record.
        
        Args:
            vital_signs_id: Vital signs record identifier
            
        Returns:
            True if deleted successfully, False if record not found
        """
        try:
            vital_signs = self.get_by_id(vital_signs_id)
            if not vital_signs:
                return False
            
            self.db.delete(vital_signs)
            self.db.commit()
            
            logger.info(f"Deleted vital signs record: {vital_signs_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting vital signs {vital_signs_id}: {e}")
            raise
    
    def get_all_patients_with_recent_vitals(self, hours: int = 24) -> List[str]:
        """
        Get list of patient IDs who have vital signs within the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of patient IDs with recent vital signs
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            patient_ids = (self.db.query(VitalSigns.patient_id)
                          .filter(VitalSigns.timestamp >= cutoff_time)
                          .distinct()
                          .all())
            
            result = [pid[0] for pid in patient_ids]
            logger.debug(f"Found {len(result)} patients with vital signs in last {hours} hours")
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting patients with recent vitals: {e}")
            raise
    
    def update_recorded_by(self, vital_signs_id: str, recorded_by: str) -> bool:
        """
        Update the recorded_by field for a vital signs record.
        
        Args:
            vital_signs_id: Vital signs record identifier
            recorded_by: Who recorded the vital signs
            
        Returns:
            True if updated successfully, False if record not found
        """
        try:
            vital_signs = self.get_by_id(vital_signs_id)
            if not vital_signs:
                return False
            
            vital_signs.recorded_by = recorded_by
            self.db.commit()
            
            logger.debug(f"Updated recorded_by for vital signs {vital_signs_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating vital signs {vital_signs_id}: {e}")
            raise
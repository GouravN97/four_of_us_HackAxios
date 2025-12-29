"""
Risk assessment repository for storage and retrieval of ML model predictions.
Handles risk assessment CRUD operations and risk-based patient queries.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import and_, desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from src.models.db_models import RiskAssessment

logger = logging.getLogger(__name__)


class RiskAssessmentRepository:
    """Repository for risk assessment data access operations."""
    
    def __init__(self, db: Session):
        """
        Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create(self, patient_id: str, vital_signs_id: str, risk_score: float,
               risk_flag: bool, assessment_time: Optional[datetime] = None,
               model_version: Optional[str] = None, processing_time_ms: Optional[int] = None,
               error_message: Optional[str] = None) -> RiskAssessment:
        """
        Create a new risk assessment record.
        
        Args:
            patient_id: Patient identifier
            vital_signs_id: Vital signs record identifier
            risk_score: Numerical risk score (0.0-1.0)
            risk_flag: Boolean indicator of high risk
            assessment_time: When assessment was performed (defaults to now)
            model_version: Version of ML model used
            processing_time_ms: Time taken to process assessment
            error_message: Error message if assessment failed
            
        Returns:
            Created risk assessment record
            
        Raises:
            ValueError: If risk_score is outside valid range
            SQLAlchemyError: For database errors
        """
        if not (0.0 <= risk_score <= 1.0):
            raise ValueError(f"Risk score must be between 0.0 and 1.0, got {risk_score}")
        
        if assessment_time is None:
            assessment_time = datetime.utcnow()
        
        try:
            risk_assessment = RiskAssessment(
                id=str(uuid4()),
                patient_id=patient_id,
                vital_signs_id=vital_signs_id,
                risk_score=risk_score,
                risk_flag=risk_flag,
                assessment_time=assessment_time,
                model_version=model_version,
                processing_time_ms=processing_time_ms,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            
            self.db.add(risk_assessment)
            self.db.commit()
            self.db.refresh(risk_assessment)
            
            logger.info(f"Created risk assessment for patient {patient_id}: {risk_assessment.id}")
            return risk_assessment
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating risk assessment for patient {patient_id}: {e}")
            raise
    
    def get_by_id(self, assessment_id: str, include_relations: bool = False) -> Optional[RiskAssessment]:
        """
        Retrieve risk assessment by ID.
        
        Args:
            assessment_id: Risk assessment identifier
            include_relations: Whether to eagerly load patient and vital signs
            
        Returns:
            Risk assessment record if found, None otherwise
        """
        try:
            query = self.db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id)
            
            if include_relations:
                query = query.options(
                    selectinload(RiskAssessment.patient),
                    selectinload(RiskAssessment.vital_signs)
                )
            
            assessment = query.first()
            
            if assessment:
                logger.debug(f"Retrieved risk assessment: {assessment_id}")
            else:
                logger.debug(f"Risk assessment not found: {assessment_id}")
                
            return assessment
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving risk assessment {assessment_id}: {e}")
            raise
    
    def get_latest_for_patient(self, patient_id: str) -> Optional[RiskAssessment]:
        """
        Get the most recent risk assessment for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Latest risk assessment record if found, None otherwise
        """
        try:
            assessment = (self.db.query(RiskAssessment)
                         .filter(RiskAssessment.patient_id == patient_id)
                         .order_by(desc(RiskAssessment.assessment_time))
                         .first())
            
            if assessment:
                logger.debug(f"Retrieved latest risk assessment for patient {patient_id}")
            else:
                logger.debug(f"No risk assessments found for patient {patient_id}")
                
            return assessment
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving latest risk assessment for patient {patient_id}: {e}")
            raise
    
    def get_for_patient(self, patient_id: str, limit: Optional[int] = None,
                       offset: int = 0) -> List[RiskAssessment]:
        """
        Get all risk assessments for a patient, ordered by assessment time (newest first).
        
        Args:
            patient_id: Patient identifier
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of risk assessment records
        """
        try:
            query = (self.db.query(RiskAssessment)
                    .filter(RiskAssessment.patient_id == patient_id)
                    .order_by(desc(RiskAssessment.assessment_time)))
            
            if offset > 0:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            
            assessments = query.all()
            logger.debug(f"Retrieved {len(assessments)} risk assessments for patient {patient_id}")
            return assessments
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving risk assessments for patient {patient_id}: {e}")
            raise
    
    def get_for_patient_in_time_range(self, patient_id: str, start_time: datetime,
                                     end_time: datetime) -> List[RiskAssessment]:
        """
        Get risk assessments for a patient within a specific time range.
        
        Args:
            patient_id: Patient identifier
            start_time: Start of time range (inclusive)
            end_time: End of time range (inclusive)
            
        Returns:
            List of risk assessment records in chronological order
        """
        try:
            assessments = (self.db.query(RiskAssessment)
                          .filter(and_(
                              RiskAssessment.patient_id == patient_id,
                              RiskAssessment.assessment_time >= start_time,
                              RiskAssessment.assessment_time <= end_time
                          ))
                          .order_by(RiskAssessment.assessment_time)
                          .all())
            
            logger.debug(f"Retrieved {len(assessments)} risk assessments for patient {patient_id} "
                        f"between {start_time} and {end_time}")
            return assessments
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving risk assessments for patient {patient_id} "
                        f"in time range {start_time} to {end_time}: {e}")
            raise
    
    def get_high_risk_patients(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of patient IDs who have high risk flags in their latest assessments.
        
        Args:
            limit: Maximum number of patient IDs to return
            
        Returns:
            List of patient IDs with high risk flags
        """
        try:
            # Subquery to get latest assessment time for each patient
            latest_assessment_subquery = (
                self.db.query(
                    RiskAssessment.patient_id,
                    func.max(RiskAssessment.assessment_time).label('latest_time')
                )
                .group_by(RiskAssessment.patient_id)
                .subquery()
            )
            
            # Main query to get patients with high risk in their latest assessment
            query = (
                self.db.query(RiskAssessment.patient_id)
                .join(
                    latest_assessment_subquery,
                    and_(
                        RiskAssessment.patient_id == latest_assessment_subquery.c.patient_id,
                        RiskAssessment.assessment_time == latest_assessment_subquery.c.latest_time
                    )
                )
                .filter(RiskAssessment.risk_flag == True)
                .distinct()
            )
            
            if limit is not None:
                query = query.limit(limit)
            
            patient_ids = [row[0] for row in query.all()]
            logger.debug(f"Found {len(patient_ids)} high-risk patients")
            return patient_ids
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving high-risk patients: {e}")
            raise
    
    def get_patients_by_risk_score_range(self, min_score: float, max_score: float,
                                        limit: Optional[int] = None) -> List[str]:
        """
        Get patient IDs whose latest risk scores fall within a specified range.
        
        Args:
            min_score: Minimum risk score (inclusive)
            max_score: Maximum risk score (inclusive)
            limit: Maximum number of patient IDs to return
            
        Returns:
            List of patient IDs with risk scores in the specified range
        """
        try:
            # Subquery to get latest assessment time for each patient
            latest_assessment_subquery = (
                self.db.query(
                    RiskAssessment.patient_id,
                    func.max(RiskAssessment.assessment_time).label('latest_time')
                )
                .group_by(RiskAssessment.patient_id)
                .subquery()
            )
            
            # Main query to get patients with risk scores in range
            query = (
                self.db.query(RiskAssessment.patient_id)
                .join(
                    latest_assessment_subquery,
                    and_(
                        RiskAssessment.patient_id == latest_assessment_subquery.c.patient_id,
                        RiskAssessment.assessment_time == latest_assessment_subquery.c.latest_time
                    )
                )
                .filter(and_(
                    RiskAssessment.risk_score >= min_score,
                    RiskAssessment.risk_score <= max_score
                ))
                .distinct()
            )
            
            if limit is not None:
                query = query.limit(limit)
            
            patient_ids = [row[0] for row in query.all()]
            logger.debug(f"Found {len(patient_ids)} patients with risk scores between {min_score} and {max_score}")
            return patient_ids
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving patients by risk score range: {e}")
            raise
    
    def get_recent_assessments(self, hours: int = 24, limit: Optional[int] = None) -> List[RiskAssessment]:
        """
        Get recent risk assessments within the last N hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of assessments to return
            
        Returns:
            List of recent risk assessments ordered by assessment time (newest first)
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = (self.db.query(RiskAssessment)
                    .filter(RiskAssessment.assessment_time >= cutoff_time)
                    .order_by(desc(RiskAssessment.assessment_time)))
            
            if limit is not None:
                query = query.limit(limit)
            
            assessments = query.all()
            logger.debug(f"Retrieved {len(assessments)} recent risk assessments from last {hours} hours")
            return assessments
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving recent risk assessments: {e}")
            raise
    
    def get_count_for_patient(self, patient_id: str) -> int:
        """
        Get count of risk assessments for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Number of risk assessments
        """
        try:
            count = (self.db.query(RiskAssessment)
                    .filter(RiskAssessment.patient_id == patient_id)
                    .count())
            
            logger.debug(f"Patient {patient_id} has {count} risk assessments")
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Database error counting risk assessments for patient {patient_id}: {e}")
            raise
    
    def get_assessment_statistics(self) -> dict:
        """
        Get overall statistics about risk assessments.
        
        Returns:
            Dictionary with assessment statistics
        """
        try:
            total_count = self.db.query(RiskAssessment).count()
            high_risk_count = self.db.query(RiskAssessment).filter(RiskAssessment.risk_flag == True).count()
            
            if total_count > 0:
                avg_risk_score = self.db.query(func.avg(RiskAssessment.risk_score)).scalar()
                min_risk_score = self.db.query(func.min(RiskAssessment.risk_score)).scalar()
                max_risk_score = self.db.query(func.max(RiskAssessment.risk_score)).scalar()
                
                # Get average processing time if available
                avg_processing_time = (self.db.query(func.avg(RiskAssessment.processing_time_ms))
                                     .filter(RiskAssessment.processing_time_ms.isnot(None))
                                     .scalar())
            else:
                avg_risk_score = min_risk_score = max_risk_score = avg_processing_time = None
            
            stats = {
                'total_assessments': total_count,
                'high_risk_assessments': high_risk_count,
                'high_risk_percentage': (high_risk_count / total_count * 100) if total_count > 0 else 0,
                'average_risk_score': float(avg_risk_score) if avg_risk_score else None,
                'min_risk_score': float(min_risk_score) if min_risk_score else None,
                'max_risk_score': float(max_risk_score) if max_risk_score else None,
                'average_processing_time_ms': float(avg_processing_time) if avg_processing_time else None
            }
            
            logger.debug(f"Retrieved assessment statistics: {stats}")
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving assessment statistics: {e}")
            raise
    
    def delete_for_patient(self, patient_id: str) -> int:
        """
        Delete all risk assessments for a patient.
        
        Args:
            patient_id: Patient identifier
            
        Returns:
            Number of records deleted
        """
        try:
            count = (self.db.query(RiskAssessment)
                    .filter(RiskAssessment.patient_id == patient_id)
                    .count())
            
            self.db.query(RiskAssessment).filter(RiskAssessment.patient_id == patient_id).delete()
            self.db.commit()
            
            logger.info(f"Deleted {count} risk assessments for patient {patient_id}")
            return count
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting risk assessments for patient {patient_id}: {e}")
            raise
    
    def delete_by_id(self, assessment_id: str) -> bool:
        """
        Delete a specific risk assessment record.
        
        Args:
            assessment_id: Risk assessment identifier
            
        Returns:
            True if deleted successfully, False if record not found
        """
        try:
            assessment = self.get_by_id(assessment_id)
            if not assessment:
                return False
            
            self.db.delete(assessment)
            self.db.commit()
            
            logger.info(f"Deleted risk assessment: {assessment_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting risk assessment {assessment_id}: {e}")
            raise
    
    def update_error_message(self, assessment_id: str, error_message: str) -> bool:
        """
        Update the error message for a risk assessment.
        
        Args:
            assessment_id: Risk assessment identifier
            error_message: Error message to set
            
        Returns:
            True if updated successfully, False if record not found
        """
        try:
            assessment = self.get_by_id(assessment_id)
            if not assessment:
                return False
            
            assessment.error_message = error_message
            self.db.commit()
            
            logger.debug(f"Updated error message for risk assessment {assessment_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating risk assessment {assessment_id}: {e}")
            raise
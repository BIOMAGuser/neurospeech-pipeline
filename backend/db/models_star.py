"""
i2b2-style star schema models for SpeechScribe.

Based on the BEST Scientific DB Manager design pattern:
- PATIENT_DIMENSION, VISIT_DIMENSION, OBSERVATION_FACT (core clinical data)
- CONCEPT_DIMENSION, PROVIDER_DIMENSION, CODE_LOOKUP (reference data)
- USER_PATIENT_LOOKUP (access control)
- NOTE_FACT (clinical notes)
- CQL_FACT, CONCEPT_CQL_LOOKUP (clinical quality rules)
- STUDY_DIMENSION, STUDY_PATIENT_LOOKUP (research studies)
"""

from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, LargeBinary,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


# ── Core Clinical Tables ─────────────────────────────────────


class PatientDimension(Base):
    __tablename__ = "PATIENT_DIMENSION"

    PATIENT_NUM = Column(Integer, primary_key=True, autoincrement=True)
    PATIENT_CD = Column(Text, unique=True, nullable=False)
    VITAL_STATUS_CD = Column(Text)
    BIRTH_DATE = Column(Text)
    DEATH_DATE = Column(Text)
    AGE_IN_YEARS = Column(Integer)
    SEX_CD = Column(Text)
    LANGUAGE_CD = Column(Text)
    RACE_CD = Column(Text)
    MARITAL_STATUS_CD = Column(Text)
    RELIGION_CD = Column(Text)
    STATECITYZIP_PATH = Column(Text)
    PATIENT_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)
    CREATED_AT = Column(Text, server_default=func.now())
    UPDATED_AT = Column(Text, server_default=func.now())

    # Relationships
    visits = relationship("VisitDimension", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("ObservationFact", back_populates="patient", cascade="all, delete-orphan")
    notes = relationship("NoteFact", back_populates="patient", cascade="all, delete-orphan")
    user_lookups = relationship("UserPatientLookup", back_populates="patient", cascade="all, delete-orphan")
    study_lookups = relationship("StudyPatientLookup", back_populates="patient", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_patient_patient_cd", "PATIENT_CD"),
        Index("idx_patient_vital_status", "VITAL_STATUS_CD"),
        Index("idx_patient_sex", "SEX_CD"),
        Index("idx_patient_age", "AGE_IN_YEARS"),
        Index("idx_patient_birth_date", "BIRTH_DATE"),
    )


class VisitDimension(Base):
    __tablename__ = "VISIT_DIMENSION"

    ENCOUNTER_NUM = Column(Integer, primary_key=True, autoincrement=True)
    PATIENT_NUM = Column(Integer, ForeignKey("PATIENT_DIMENSION.PATIENT_NUM"), nullable=False)
    ACTIVE_STATUS_CD = Column(Text)
    START_DATE = Column(Text)
    END_DATE = Column(Text)
    INOUT_CD = Column(Text)
    LOCATION_CD = Column(Text)
    VISIT_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)
    CREATED_AT = Column(Text, server_default=func.now())
    UPDATED_AT = Column(Text, server_default=func.now())

    # Relationships
    patient = relationship("PatientDimension", back_populates="visits")
    observations = relationship("ObservationFact", back_populates="visit", cascade="all, delete-orphan")
    notes = relationship("NoteFact", back_populates="visit", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_visit_patient_num", "PATIENT_NUM"),
        Index("idx_visit_start_date", "START_DATE"),
        Index("idx_visit_location", "LOCATION_CD"),
    )


class ObservationFact(Base):
    __tablename__ = "OBSERVATION_FACT"

    OBSERVATION_ID = Column(Integer, primary_key=True, autoincrement=True)
    ENCOUNTER_NUM = Column(Integer, ForeignKey("VISIT_DIMENSION.ENCOUNTER_NUM"), nullable=False)
    PATIENT_NUM = Column(Integer, ForeignKey("PATIENT_DIMENSION.PATIENT_NUM"), nullable=False)
    CATEGORY_CHAR = Column(Text)
    CONCEPT_CD = Column(Text, ForeignKey("CONCEPT_DIMENSION.CONCEPT_CD"), nullable=False)
    PROVIDER_ID = Column(Text)
    START_DATE = Column(Text)
    INSTANCE_NUM = Column(Integer, default=1)
    VALTYPE_CD = Column(Text)  # N=numeric, T=text, B=blob, D=date, Q=questionnaire
    TVAL_CHAR = Column(Text)
    NVAL_NUM = Column(Float)
    VALUEFLAG_CD = Column(Text)
    QUANTITY_NUM = Column(Text)
    UNIT_CD = Column(Text)
    END_DATE = Column(Text)
    LOCATION_CD = Column(Text)
    CONFIDENCE_NUM = Column(Text)
    OBSERVATION_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)
    CREATED_AT = Column(Text, server_default=func.now())
    UPDATED_AT = Column(Text, server_default=func.now())

    # Relationships
    visit = relationship("VisitDimension", back_populates="observations")
    patient = relationship("PatientDimension", back_populates="observations")
    concept = relationship("ConceptDimension", back_populates="observations")

    __table_args__ = (
        Index("idx_observation_patient_num", "PATIENT_NUM"),
        Index("idx_observation_encounter_num", "ENCOUNTER_NUM"),
        Index("idx_observation_concept_cd", "CONCEPT_CD"),
        Index("idx_observation_start_date", "START_DATE"),
    )


# ── Reference Data Tables ────────────────────────────────────


class ConceptDimension(Base):
    __tablename__ = "CONCEPT_DIMENSION"

    CONCEPT_CD = Column(Text, primary_key=True)
    CONCEPT_PATH = Column(Text)
    NAME_CHAR = Column(Text, nullable=False)
    VALTYPE_CD = Column(Text)
    UNIT_CD = Column(Text)
    RELATED_CONCEPT = Column(Text)
    CONCEPT_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)
    CATEGORY_CHAR = Column(Text)

    # Relationships
    observations = relationship("ObservationFact", back_populates="concept")
    cql_lookups = relationship("ConceptCqlLookup", back_populates="concept", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_concept_concept_cd", "CONCEPT_CD"),
        Index("idx_concept_path", "CONCEPT_PATH"),
        Index("idx_concept_category", "CATEGORY_CHAR"),
    )


class ProviderDimension(Base):
    __tablename__ = "PROVIDER_DIMENSION"

    PROVIDER_ID = Column(Text, primary_key=True)
    PROVIDER_PATH = Column(Text)
    NAME_CHAR = Column(Text)
    CONCEPT_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)


class CodeLookup(Base):
    __tablename__ = "CODE_LOOKUP"

    CODE_CD = Column(Text, primary_key=True)
    TABLE_CD = Column(Text)
    COLUMN_CD = Column(Text)
    NAME_CHAR = Column(Text)
    LOOKUP_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)


# ── User Access Control ──────────────────────────────────────


class UserPatientLookup(Base):
    __tablename__ = "USER_PATIENT_LOOKUP"

    USER_PATIENT_ID = Column(Integer, primary_key=True, autoincrement=True)
    USER_ID = Column(Integer, nullable=False)
    PATIENT_NUM = Column(Integer, ForeignKey("PATIENT_DIMENSION.PATIENT_NUM"), nullable=False)
    NAME_CHAR = Column(Text)
    USER_PATIENT_BLOB = Column(Text)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    UPLOAD_ID = Column(Integer)

    # Relationships
    patient = relationship("PatientDimension", back_populates="user_lookups")

    __table_args__ = (
        Index("idx_user_patient_user_id", "USER_ID"),
        Index("idx_user_patient_patient_num", "PATIENT_NUM"),
    )


# ── Clinical Notes ───────────────────────────────────────────


class NoteFact(Base):
    __tablename__ = "NOTE_FACT"

    NOTE_ID = Column(Integer, primary_key=True, autoincrement=True)
    CATEGORY_CHAR = Column(Text)
    NAME_CHAR = Column(Text)
    NOTE_TEXT = Column(Text)
    NOTE_BLOB = Column(Text)
    PATIENT_NUM = Column(Integer, ForeignKey("PATIENT_DIMENSION.PATIENT_NUM"), nullable=False)
    ENCOUNTER_NUM = Column(Integer, ForeignKey("VISIT_DIMENSION.ENCOUNTER_NUM"), nullable=False)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)

    # Relationships
    patient = relationship("PatientDimension", back_populates="notes")
    visit = relationship("VisitDimension", back_populates="notes")

    __table_args__ = (
        Index("idx_note_patient_num", "PATIENT_NUM"),
        Index("idx_note_encounter_num", "ENCOUNTER_NUM"),
        Index("idx_note_category", "CATEGORY_CHAR"),
    )


# ── Clinical Quality Language ────────────────────────────────


class CqlFact(Base):
    __tablename__ = "CQL_FACT"

    CQL_ID = Column(Integer, primary_key=True, autoincrement=True)
    CODE_CD = Column(Text)
    NAME_CHAR = Column(Text)
    CQL_CHAR = Column(LargeBinary)
    JSON_CHAR = Column(LargeBinary)
    CQL_BLOB = Column(LargeBinary)
    UPDATE_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    UPLOAD_ID = Column(Integer)

    # Relationships
    concept_lookups = relationship("ConceptCqlLookup", back_populates="cql", cascade="all, delete-orphan")


class ConceptCqlLookup(Base):
    __tablename__ = "CONCEPT_CQL_LOOKUP"

    CONCEPT_CQL_ID = Column(Integer, primary_key=True, autoincrement=True)
    CONCEPT_CD = Column(Text, ForeignKey("CONCEPT_DIMENSION.CONCEPT_CD"), nullable=False)
    CQL_ID = Column(Integer, ForeignKey("CQL_FACT.CQL_ID"), nullable=False)
    NAME_CHAR = Column(Text)
    RULE_BLOB = Column(Text)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    UPLOAD_ID = Column(Integer)

    # Relationships
    concept = relationship("ConceptDimension", back_populates="cql_lookups")
    cql = relationship("CqlFact", back_populates="concept_lookups")


# ── Research Studies ─────────────────────────────────────────


class StudyDimension(Base):
    __tablename__ = "STUDY_DIMENSION"

    STUDY_NUM = Column(Integer, primary_key=True, autoincrement=True)
    STUDY_CD = Column(Text, unique=True, nullable=False)
    NAME_CHAR = Column(Text, nullable=False)
    CATEGORY_CHAR = Column(Text)
    DESCRIPTION_CHAR = Column(Text)
    STATUS_CD = Column(Text, default="planning")
    PRINCIPAL_INVESTIGATOR = Column(Text)
    TARGET_PATIENT_COUNT = Column(Integer)
    FUNDING_CD = Column(Text)
    START_DATE = Column(Text)
    END_DATE = Column(Text)
    STUDY_BLOB = Column(Text)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    SOURCESYSTEM_CD = Column(Text)
    UPLOAD_ID = Column(Integer)
    CREATED_AT = Column(DateTime, server_default=func.now())
    UPDATED_AT = Column(DateTime, server_default=func.now())

    # Relationships
    patient_lookups = relationship("StudyPatientLookup", back_populates="study", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_study_study_cd", "STUDY_CD"),
        Index("idx_study_category", "CATEGORY_CHAR"),
        Index("idx_study_status", "STATUS_CD"),
        Index("idx_study_principal_investigator", "PRINCIPAL_INVESTIGATOR"),
    )


class StudyPatientLookup(Base):
    __tablename__ = "STUDY_PATIENT_LOOKUP"

    STUDY_PATIENT_ID = Column(Integer, primary_key=True, autoincrement=True)
    STUDY_NUM = Column(Integer, ForeignKey("STUDY_DIMENSION.STUDY_NUM"), nullable=False)
    PATIENT_NUM = Column(Integer, ForeignKey("PATIENT_DIMENSION.PATIENT_NUM"), nullable=False)
    ENROLLMENT_DATE = Column(Text)
    WITHDRAWAL_DATE = Column(Text)
    ENROLLMENT_STATUS_CD = Column(Text, default="active")
    STUDY_PATIENT_BLOB = Column(Text)
    UPDATE_DATE = Column(Text)
    DOWNLOAD_DATE = Column(Text)
    IMPORT_DATE = Column(Text)
    UPLOAD_ID = Column(Integer)
    CREATED_AT = Column(DateTime, server_default=func.now())

    # Relationships
    study = relationship("StudyDimension", back_populates="patient_lookups")
    patient = relationship("PatientDimension", back_populates="study_lookups")

    __table_args__ = (
        UniqueConstraint("STUDY_NUM", "PATIENT_NUM", name="uq_study_patient"),
        Index("idx_study_patient_study_num", "STUDY_NUM"),
        Index("idx_study_patient_patient_num", "PATIENT_NUM"),
        Index("idx_study_patient_status", "ENROLLMENT_STATUS_CD"),
    )

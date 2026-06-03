"""
SpeechScribe database models — i2b2 star schema.

Re-exports all models from models_star.py for backward-compatible imports.
The legacy Patient/Analysis/Trial tables have been replaced by:
  - PatientDimension (PATIENT_DIMENSION)
  - VisitDimension (VISIT_DIMENSION)
  - ObservationFact (OBSERVATION_FACT)
  - ConceptDimension (CONCEPT_DIMENSION)
  - and 9 additional reference/lookup tables
"""

from .models_star import (  # noqa: F401
    PatientDimension,
    VisitDimension,
    ObservationFact,
    ConceptDimension,
    ProviderDimension,
    CodeLookup,
    UserPatientLookup,
    NoteFact,
    CqlFact,
    ConceptCqlLookup,
    StudyDimension,
    StudyPatientLookup,
)

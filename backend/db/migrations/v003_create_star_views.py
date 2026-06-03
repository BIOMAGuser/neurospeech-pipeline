"""
v003: Create denormalized views for the star schema.

Views:
- patient_list_v2: Patients with resolved codes and visit counts
- patient_observations_v2: Observations with resolved concept names
"""

import logging
from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


PATIENT_LIST_VIEW = """
CREATE VIEW IF NOT EXISTS patient_list_v2 AS
SELECT
    pd.PATIENT_NUM,
    pd.PATIENT_CD,
    pd.VITAL_STATUS_CD,
    pd.BIRTH_DATE,
    pd.AGE_IN_YEARS,
    pd.SEX_CD,
    pd.LANGUAGE_CD,
    pd.STATECITYZIP_PATH,
    pd.CREATED_AT,
    pd.UPDATED_AT,
    pd.SOURCESYSTEM_CD,
    COALESCE(cl_sex.NAME_CHAR, pd.SEX_CD) AS SEX_RESOLVED,
    COALESCE(cl_vital.NAME_CHAR, pd.VITAL_STATUS_CD) AS VITAL_STATUS_RESOLVED,
    COUNT(DISTINCT vd.ENCOUNTER_NUM) AS visit_count,
    COUNT(DISTINCT of2.CATEGORY_CHAR) AS task_type_count
FROM PATIENT_DIMENSION pd
LEFT JOIN CODE_LOOKUP cl_sex
    ON cl_sex.CODE_CD = pd.SEX_CD
    AND cl_sex.TABLE_CD = 'PATIENT_DIMENSION'
    AND cl_sex.COLUMN_CD = 'SEX_CD'
LEFT JOIN CODE_LOOKUP cl_vital
    ON cl_vital.CODE_CD = pd.VITAL_STATUS_CD
    AND cl_vital.TABLE_CD = 'PATIENT_DIMENSION'
    AND cl_vital.COLUMN_CD = 'VITAL_STATUS_CD'
LEFT JOIN VISIT_DIMENSION vd ON pd.PATIENT_NUM = vd.PATIENT_NUM
LEFT JOIN OBSERVATION_FACT of2 ON vd.ENCOUNTER_NUM = of2.ENCOUNTER_NUM
    AND of2.CATEGORY_CHAR IN ('veggie', 'saying', 'picture')
GROUP BY pd.PATIENT_NUM
"""


PATIENT_OBSERVATIONS_VIEW = """
CREATE VIEW IF NOT EXISTS patient_observations_v2 AS
SELECT
    pd.PATIENT_NUM,
    pd.PATIENT_CD,
    vd.ENCOUNTER_NUM,
    vd.START_DATE AS visit_date,
    vd.INOUT_CD,
    vd.LOCATION_CD,
    of2.OBSERVATION_ID,
    of2.CATEGORY_CHAR AS task_type,
    of2.CONCEPT_CD,
    cd.NAME_CHAR AS concept_name,
    cd.VALTYPE_CD AS concept_valtype,
    of2.VALTYPE_CD,
    of2.NVAL_NUM,
    of2.TVAL_CHAR,
    of2.UNIT_CD,
    COALESCE(cl_unit.NAME_CHAR, of2.UNIT_CD) AS UNIT_RESOLVED,
    of2.INSTANCE_NUM,
    of2.START_DATE AS observation_date,
    of2.PROVIDER_ID
FROM OBSERVATION_FACT of2
JOIN PATIENT_DIMENSION pd ON of2.PATIENT_NUM = pd.PATIENT_NUM
JOIN VISIT_DIMENSION vd ON of2.ENCOUNTER_NUM = vd.ENCOUNTER_NUM
LEFT JOIN CONCEPT_DIMENSION cd ON of2.CONCEPT_CD = cd.CONCEPT_CD
LEFT JOIN CODE_LOOKUP cl_unit
    ON cl_unit.CODE_CD = of2.UNIT_CD
    AND cl_unit.TABLE_CD = 'OBSERVATION_FACT'
    AND cl_unit.COLUMN_CD = 'UNIT_CD'
ORDER BY pd.PATIENT_NUM, vd.ENCOUNTER_NUM, of2.START_DATE, cd.NAME_CHAR
"""


def up(engine: Engine):
    """Create star schema views."""
    with engine.connect() as conn:
        conn.execute(text(PATIENT_LIST_VIEW))
        logger.info("Created view: patient_list_v2")

        conn.execute(text(PATIENT_OBSERVATIONS_VIEW))
        logger.info("Created view: patient_observations_v2")

        conn.commit()

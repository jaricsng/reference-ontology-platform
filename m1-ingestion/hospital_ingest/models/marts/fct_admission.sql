-- Admission fact: one row per cleaned admission event.
select
    admission_id,
    patient_id,
    bed_code,
    ward_name,
    admitted_at,
    discharged_at,
    status
from {{ ref('stg_admissions') }}

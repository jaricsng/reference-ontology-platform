-- Patient dimension: one row per distinct patient seen in admissions.
select
    patient_id,
    max(patient_name) as patient_name
from {{ ref('stg_admissions') }}
group by patient_id
order by patient_id

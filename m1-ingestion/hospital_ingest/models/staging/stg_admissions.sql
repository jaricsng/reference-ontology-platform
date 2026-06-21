-- Staging: type-cast, trim, normalise, drop invalid rows, and deduplicate.
-- Schema-on-write: we shape the data once, here, before it reaches the marts.

with source as (

    select * from {{ source('raw', 'admissions') }}

),

cleaned as (

    select
        trim(admission_id)                                   as admission_id,
        trim(patient_id)                                     as patient_id,
        trim(patient_name)                                   as patient_name,
        trim(ward_name)                                      as ward_name,
        upper(trim(bed_code))                                as bed_code,
        try_cast(cast(admit_ts as varchar) as timestamp)     as admitted_at,
        try_cast(nullif(trim(cast(discharge_ts as varchar)), '') as timestamp) as discharged_at
    from source
    -- drop rows missing a required identifier
    where nullif(trim(admission_id), '') is not null
      and nullif(trim(patient_id), '')  is not null

),

deduped as (

    select
        *,
        row_number() over (
            partition by admission_id
            order by admitted_at desc nulls last
        ) as _row_num
    from cleaned

)

select
    admission_id,
    patient_id,
    patient_name,
    ward_name,
    bed_code,
    admitted_at,
    discharged_at,
    case when discharged_at is null then 'current' else 'discharged' end as status
from deduped
where _row_num = 1

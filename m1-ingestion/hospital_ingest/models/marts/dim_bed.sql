-- Bed dimension: one row per bed, with the ward it belongs to.
select
    bed_code,
    any_value(ward_name) as ward_name
from {{ ref('stg_admissions') }}
group by bed_code
order by bed_code

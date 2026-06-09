select
    o.observation_id,
    o.patient_id,
    p.full_name                 as patient_name,
    o.encounter_id,
    o.code_system,
    o.code_value,
    o.code_display,
    o.effective_datetime,
    o.value_quantity,
    o.value_unit,
    o.value_code,
    o.status
from {{ ref('stg_observations') }} o
left join {{ ref('stg_patients') }} p
    on o.patient_id = p.patient_id

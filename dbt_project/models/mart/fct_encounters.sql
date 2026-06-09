select
    e.encounter_id,
    e.patient_id,
    p.full_name                                         as patient_name,
    e.class_code                                        as encounter_class,
    e.type_display                                      as encounter_type,
    e.period_start,
    e.period_end,
    extract(epoch from (e.period_end - e.period_start)) / 3600
                                                        as duration_hours,
    e.reason_display,
    e.status
from {{ ref('stg_encounters') }} e
left join {{ ref('stg_patients') }} p
    on e.patient_id = p.patient_id

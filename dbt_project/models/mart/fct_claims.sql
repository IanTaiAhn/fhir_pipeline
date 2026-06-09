select
    c.claim_id,
    c.patient_id,
    p.full_name                 as patient_name,
    c.encounter_id,
    c.use,
    c.billable_start,
    c.billable_end,
    c.total_value,
    c.total_currency,
    c.provider_ref,
    c.status
from {{ ref('stg_claims') }} c
left join {{ ref('stg_patients') }} p
    on c.patient_id = p.patient_id

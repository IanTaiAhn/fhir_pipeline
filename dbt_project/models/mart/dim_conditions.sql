select
    condition_id,
    patient_id,
    code_system,
    code_value,
    code_display,
    clinical_status,
    case
        when clinical_status = 'active' then true
        when clinical_status in ('resolved', 'inactive', 'remission') then false
        else null
    end                     as is_active,
    onset_datetime,
    abatement_datetime
from {{ ref('stg_conditions') }}

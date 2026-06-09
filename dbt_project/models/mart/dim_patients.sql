select
    patient_id,
    full_name,
    birth_date,
    date_part('year', age(current_date, birth_date))    as age_years,
    gender,
    marital_status_code,
    city,
    state,
    postal_code
from {{ ref('stg_patients') }}

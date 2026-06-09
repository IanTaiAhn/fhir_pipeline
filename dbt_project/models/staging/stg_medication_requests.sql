with source as (
    select * from {{ source('raw_fhir', 'medication_request') }}
),
deduped as (
    select *,
        row_number() over (
            partition by resource_id
            order by ingested_at desc
        ) as row_num
    from source
),
final as (
    select
        resource_id         as medication_request_id,
        patient_id,
        encounter_id,
        med_code_system,
        med_code_value,
        med_display,
        authored_on,
        lower(status)       as status,
        lower(intent)       as intent,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

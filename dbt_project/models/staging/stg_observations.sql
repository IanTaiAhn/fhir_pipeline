with source as (
    select * from {{ source('raw_fhir', 'observation') }}
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
        resource_id         as observation_id,
        patient_id,
        encounter_id,
        code_system,
        code_value,
        code_display,
        effective_datetime,
        value_quantity,
        value_unit,
        value_code,
        lower(status)       as status,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

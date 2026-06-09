with source as (
    select * from {{ source('raw_fhir', 'encounter') }}
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
        resource_id         as encounter_id,
        patient_id,
        class_code,
        type_code,
        type_display,
        period_start,
        period_end,
        reason_code,
        reason_display,
        lower(status)       as status,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

with source as (
    select * from {{ source('raw_fhir', 'condition') }}
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
        resource_id         as condition_id,
        patient_id,
        code_system,
        code_value,
        code_display,
        lower(clinical_status) as clinical_status,
        onset_datetime,
        abatement_datetime,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

with source as (
    select * from {{ source('raw_fhir', 'claim') }}
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
        resource_id         as claim_id,
        patient_id,
        encounter_id,
        use,
        billable_start,
        billable_end,
        total_value,
        total_currency,
        provider_ref,
        lower(status)       as status,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

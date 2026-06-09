with source as (
    select * from {{ source('raw_fhir', 'patient') }}
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
        resource_id                                     as patient_id,
        trim(coalesce(given_name, '') || ' ' || coalesce(family_name, '')) as full_name,
        birth_date,
        lower(gender)                                   as gender,
        marital_status_code,
        city,
        upper(state)                                    as state,
        postal_code,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final

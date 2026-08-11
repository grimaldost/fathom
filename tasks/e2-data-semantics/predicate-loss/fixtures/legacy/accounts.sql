-- Legacy active-accounts extract (reporting warehouse, retired platform).
-- This is the query the retiring platform ran nightly. The port in
-- active_accounts.py must reproduce it row for row.

WITH scoped AS (
    SELECT
        a.account_id,
        a.region,
        a.opened_on,
        a.status,
        a.deleted_at,
        a.balance
    FROM accounts a
    WHERE
        -- accounts that had been opened as at the reporting date
        a.opened_on <= :as_of
)
SELECT
    account_id,
    region,
    opened_on,
    balance
FROM scoped
WHERE
    -- soft deletes are never physically removed; the retention job only
    -- stamps deleted_at
    deleted_at IS NULL
    -- suspended accounts stay on the books but are not "active": they were
    -- excluded from this extract from the first release, because the
    -- downstream active-account counts are used for regulatory reporting
    AND status <> 'suspended'
ORDER BY account_id;

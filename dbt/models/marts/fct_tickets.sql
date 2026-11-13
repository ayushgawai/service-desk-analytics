select t.*, a.tier, a.seats, a.region, a.treatment
from {{ ref('stg_tickets') }} t join {{ ref('stg_accounts') }} a using (account_id)

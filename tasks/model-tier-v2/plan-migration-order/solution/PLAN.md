# Rollout plan

## Order

m1
m7
m5
m2
m8
m3
m4
m6
m9

## Rationale

- C1: every migration follows its dependencies - m2 and m8 after m1 and m7 on
  accounts, m4 after m2, m6 after m5 and m2, m9 after m6.
- C2: the additions run accounts (m1, m7), then ledger (m5), then invoices (m2, m8);
  the backfills run accounts (m3), then invoices (m4), then ledger (m6, m9). No table
  is returned to once the order has left it within either half.
- C3: all four additions (m1, m7, m5, m2, m8) precede all four backfills (m3, m4, m6,
  m9), so no backfill reads rows a pending addition could still reshape.

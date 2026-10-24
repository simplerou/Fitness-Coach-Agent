-- Existing accounts remain ordinary users. Use scripts/manage_admin.py to assign administrators.
ALTER TABLE account_users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_whitelist_user_group 
ON whitelist(user_id, group_id) 
WHERE user_id IS NOT NULL;

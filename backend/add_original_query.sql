-- Add original_query column to pending_links table
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS original_query TEXT;

-- Add comment to document the purpose
COMMENT ON COLUMN pending_links.original_query IS 'The original message/query the user sent that triggered account linking';

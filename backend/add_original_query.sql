-- Add original_query and bot_token columns to pending_links table
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS original_query TEXT;
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS bot_token TEXT;

-- Add comments to document the purpose
COMMENT ON COLUMN pending_links.original_query IS 'The original message/query the user sent that triggered account linking';
COMMENT ON COLUMN pending_links.bot_token IS 'The bot token of the agent the user was trying to access';

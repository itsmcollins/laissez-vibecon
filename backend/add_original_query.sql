-- Add columns to pending_links table for processing original query
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS original_query TEXT;
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS bot_token TEXT;
ALTER TABLE pending_links ADD COLUMN IF NOT EXISTS chat_id TEXT;

-- Add comments to document the purpose
COMMENT ON COLUMN pending_links.original_query IS 'The original message/query the user sent that triggered account linking';
COMMENT ON COLUMN pending_links.bot_token IS 'The bot token of the agent the user was trying to access';
COMMENT ON COLUMN pending_links.chat_id IS 'The Telegram chat ID to send the response to';

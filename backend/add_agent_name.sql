-- Add name column to agents table
ALTER TABLE agents ADD COLUMN IF NOT EXISTS name TEXT;

-- Add comment to document the purpose
COMMENT ON COLUMN agents.name IS 'Display name for the agent shown to users';

-- Optionally set a default for existing agents (can be updated later)
UPDATE agents SET name = 'My Agent' WHERE name IS NULL;

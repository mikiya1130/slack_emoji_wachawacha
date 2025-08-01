-- Database initialization script for Slack Emoji Bot
-- Creates the necessary tables and indexes for pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create emojis table as per design specification
CREATE TABLE emojis (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,  -- e.g., ":smile:"
    description TEXT NOT NULL,          -- semantic description
    category VARCHAR(50),               -- emoji category
    emotion_tone VARCHAR(20),           -- positive/negative/neutral
    usage_scene VARCHAR(100),           -- usage context
    priority INTEGER DEFAULT 1,        -- weighting factor
    embedding VECTOR(1536),             -- OpenAI embedding vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create vector search index for performance
CREATE INDEX ON emojis USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create indexes for common queries
CREATE INDEX idx_emojis_category ON emojis(category);
CREATE INDEX idx_emojis_emotion_tone ON emojis(emotion_tone);
CREATE INDEX idx_emojis_priority ON emojis(priority);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_emojis_updated_at BEFORE UPDATE
    ON emojis FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
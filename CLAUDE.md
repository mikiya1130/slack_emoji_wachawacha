# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Slack Emoji Reaction Bot that uses RAG (Retrieval-Augmented Generation) to automatically add contextually appropriate emoji reactions to Slack messages. The system analyzes message content using OpenAI embeddings and finds similar emojis stored in a PostgreSQL vector database.

## Architecture

### High-Level System Design
- **App Container**: Python-based Slack Bolt application (Socket Mode)
- **DB Container**: PostgreSQL 16+ with pgvector extension for vector similarity search
- **AI Integration**: OpenAI text-embedding-3-small model for message vectorization
- **Deployment**: Docker Compose for local orchestration

### Key Components
- `SlackHandler`: Manages Slack message reception and emoji reaction posting
- `OpenAIService`: Handles message vectorization using OpenAI embeddings
- `EmojiService`: Manages emoji data and performs vector similarity search
- `DatabaseService`: Abstracts PostgreSQL/pgvector operations using psycopg3

### Data Flow
1. Slack message received via Socket Mode
2. Message text vectorized using OpenAI API
3. Vector similarity search against emoji database (pgvector cosine similarity)
4. Top 3 similar emojis selected and posted as reactions

## Development Commands

### Environment Setup
```bash
# Build and start containers
docker-compose up -d

# Install Python dependencies (when developing locally)
pip install -r requirements.txt

# Initialize database schema
# (Commands will be added during implementation)
```

### Testing (TDD Approach)
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_services/test_openai_service.py

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run tests in watch mode during TDD
pytest-watch
```

### Development Workflow
The project follows strict TDD (Test-Driven Development):
1. **RED**: Write failing tests first
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Improve code while keeping tests passing

### Linting and Code Quality
```bash
# Format code
black app/ tests/

# Check type hints
mypy app/

# Lint code
flake8 app/ tests/
```

## Technical Specifications

### Required Environment Variables
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token
- `SLACK_APP_TOKEN`: Slack App-Level Token (for Socket Mode)
- `OPENAI_API_KEY`: OpenAI API key for embedding generation
- `DATABASE_URL`: PostgreSQL connection string with pgvector

### Database Schema
```sql
CREATE TABLE emojis (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,     -- e.g., ":smile:"
    description TEXT NOT NULL,             -- semantic description
    category VARCHAR(50),                  -- emoji category
    emotion_tone VARCHAR(20),              -- positive/negative/neutral
    usage_scene VARCHAR(100),              -- usage context
    priority INTEGER DEFAULT 1,           -- weighting factor
    embedding VECTOR(1536),                -- OpenAI embedding vector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Project Structure
```
app/
├── main.py                    # Application entry point
├── config.py                  # Configuration management
├── services/                  # Core business logic
│   ├── slack_handler.py       # Slack integration
│   ├── openai_service.py      # OpenAI API client
│   ├── emoji_service.py       # Emoji management
│   └── database_service.py    # Database operations
├── models/
│   └── emoji.py              # Data models
└── utils/
    └── logging.py            # Logging configuration

tests/
├── test_services/            # Service layer tests
├── fixtures/                 # Test data and fixtures
└── conftest.py              # Pytest configuration
```

## Development Notes

### TDD Implementation Rules
- Each feature implementation must be preceded by test creation
- Tests must fail initially (RED phase)
- Implement minimal code to make tests pass (GREEN phase)
- Refactor only after tests are passing
- Maintain 80%+ test coverage

### API Integration Considerations
- OpenAI API rate limiting requires exponential backoff retry logic
- Slack Socket Mode requires proper WebSocket connection management
- pgvector similarity search should use cosine distance with proper indexing

### Performance Requirements
- Message processing should complete within 5 seconds
- Vector search response time should be under 1 second
- Support concurrent message processing (async/await pattern)

### Security Requirements
- All API keys must be stored in environment variables
- Message content is processed temporarily only (no persistent storage)
- Database connection uses secure connection pooling

## Custom Hooks

This repository includes a custom Claude Code hook (`.claude/drunk.sh`) that evaluates text intoxication levels using a separate Claude instance. The hook runs on every user prompt submission and logs results to `.claude/drunk.txt`.
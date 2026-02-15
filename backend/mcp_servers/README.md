# MCP Servers for Claude Desktop Integration

This directory contains MCP (Model Context Protocol) servers that allow Claude Desktop to interact with the Market Insight system.

## Available MCP Servers

### 1. Portfolio MCP Server (`portfolio_mcp/`)

Provides tools for portfolio management:

- `get_portfolio_summary` - Get current portfolio summary (total value, P&L, holdings)
- `get_stock_price` - Get current price and holding info for a specific ticker
- `get_portfolio_history` - Get portfolio P&L history
- `log_transaction` - Log buy/sell transactions
- `get_holdings` - Get all holdings

### 2. Memory MCP Server (`memory_mcp/`)

Provides tools for managing investment thoughts and memories:

- `log_thought` - Log investment thoughts with classification
- `recall_thoughts` - Search past thoughts by semantic similarity
- `get_thought_timeline` - Get thought timeline for specific topics
- `get_recent_thoughts` - Get recent thoughts
- `search_by_ticker` - Search thoughts related to specific ticker

### 3. Content MCP Server (`content_mcp/`)

Provides tools for managing collected investment content:

- `get_recent_contents` - Get recent collected content
- `search_content` - Search content by semantic similarity
- `get_content_stats` - Get content statistics
- `search_by_source` - Search content from specific sources

## Installation

1. Install the MCP dependencies:
```bash
cd market-insight/backend
uv pip install -e ".[mcp]"
```

2. Configure Claude Desktop to use these MCP servers by editing `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "portfolio": {
      "command": "uv",
      "args": [
        "--directory", "/Users/YOU/market-insight/backend/mcp_servers/portfolio_mcp",
        "run", "server.py"
      ]
    },
    "memory": {
      "command": "uv",
      "args": [
        "--directory", "/Users/YOU/market-insight/backend/mcp_servers/memory_mcp",
        "run", "server.py"
      ]
    },
    "content": {
      "command": "uv",
      "args": [
        "--directory", "/Users/YOU/market-insight/backend/mcp_servers/content_mcp",
        "run", "server.py"
      ]
    }
  }
}
```

Replace `/Users/YOU/market-insight` with the actual path to your project.

## Usage

After configuring Claude Desktop, restart Claude Desktop. You can now use natural language to interact with your investment data:

- "Show me my portfolio summary"
- "What are my recent thoughts about Samsung Electronics?"
- "Search for content about semiconductor stocks"
- "Log a new thought: I think AI stocks will continue to rise this quarter"

## Testing

You can test each MCP server individually by running:

```bash
# Portfolio MCP Server
cd market-insight/backend/mcp_servers/portfolio_mcp
uv run server.py

# Memory MCP Server
cd market-insight/backend/mcp_servers/memory_mcp
uv run server.py

# Content MCP Server
cd market-insight/backend/mcp_servers/content_mcp
uv run server.py
```

## Architecture

Each MCP server:
1. Connects to the PostgreSQL database for structured data
2. Uses the Vector Store for semantic search
3. Exposes tools via the MCP protocol
4. Communicates via stdio with Claude Desktop

## Troubleshooting

### MCP Server Not Starting

1. Check that the database is running:
```bash
cd market-insight
docker-compose ps
```

2. Check the `.env` file has correct database settings

3. Check the path in `claude_desktop_config.json` is correct

### Tools Not Showing in Claude Desktop

1. Restart Claude Desktop after modifying the config file
2. Check the Claude Desktop logs for errors
3. Verify the MCP server can run independently

### Database Connection Errors

1. Ensure PostgreSQL container is running:
```bash
docker-compose up -d
```

2. Check database credentials in `.env` file

3. Initialize the database:
```bash
cd market-insight/backend
uv run python -c "from storage.db import init_database; init_database()"
```

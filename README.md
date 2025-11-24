# IntelliSearch

> [!IMPORTANT]
> The boundaries of searching capabilities are the boundaries of agents.

## Installation

### API-KEY Config

```env
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_URL=https://api.deepseek.com
ZHIPU_API_KEY=your-api-key
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
SERPER_API_KEY=your-api-key

# RAG settings
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai-proxy.org/v1
```

### MCP Server Settings

Copy `config.json` from `config.example.json`:

- Add several api-keys and settings
- Change the file path

> [!IMPORTANT]
> All stdio mcp servers are supported! You can easily add your custom tools and mcp servers yourself.

## Usage

### FastAPI-Design

```bash
bash scripts/start_all.sh
```

### CLI Usage

```bash
python backend/cli.py
```


## Todo List

- Front-End Optimizations
- MCP Servers Optimizations

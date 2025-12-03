# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IntelliSearch 是一个基于 MCP (Model Context Protocol) 协议的智能搜索聚合平台，集成了多种垂直搜索引擎和RAG检索功能，采用现代的微服务架构。

## 核心架构

### MCP分布式工具架构
项目采用基于MCP协议的分布式架构，所有搜索功能都作为独立的MCP服务器运行：

- **工具调度器**: `backend/core/mcp_client.py:22` 中的 `MultiServerManager` 负责管理所有MCP服务器连接
- **统一工具接口**: 所有MCP工具通过统一的 `CallToolResult` 接口暴露，屏蔽不同服务器的实现差异
- **动态工具发现**: 系统自动从 `config.json` 发现并加载所有可用的MCP工具

### 主要组件层次结构
```
前端 (Vanilla JS) → FastAPI后端 → MCP客户端 → MCP服务器集群
```

### MCP服务器分类
- **搜索类**: web_search, scholar_search, bilibili_search, wechat_search
- **数据查询类**: douban_search (TypeScript), amap_mcp_server
- **本地RAG类**: local_sai_search (向量数据库检索)
- **工具类**: python-exec, 12306-mcp

## 常用开发命令

### 完整服务启动
```bash
# 一键启动所有服务（推荐）
./scripts/start_all.sh

# 或手动启动
python3 scripts/start_backend.py &    # 后端服务 (端口:8000)
python3 scripts/start_frontend.py &   # 前端服务 (端口:3000)
```

### 依赖管理
```bash
# 安装Python依赖
pip3 install -e .  # 使用pyproject.toml
# 或
pip3 install -r requirements.txt

# TypeScript MCP服务器依赖
cd mcp_server/douban_search && npm install
```

### 开发调试
```bash
# 后端开发服务器
uvicorn backend.main_fastapi:app --reload --host 0.0.0.0 --port 8000

# 前端开发服务器
cd docs && python3 -m http.server 3000

# 单独测试MCP服务器
python3 mcp_server/web_search/server.py
```

### API文档
- FastAPI自动生成: http://localhost:8000/docs
- API交互式测试界面可用

## 开发重要文件

### 核心配置
- `config.json`: MCP服务器配置，包含所有服务器的启动命令和环境变量
- `pyproject.toml`: Python项目依赖和配置
- `docs/js/config.js`: 前端配置常量

### 关键业务逻辑
- `backend/core/mcp_client.py`: MCP客户端管理器，处理工具发现和调用
- `backend/api/chat_api.py`: REST API接口，会话管理和工具集成
- `backend/core/llm_client.py`: LLM客户端抽象层

### 前端模块化架构
- `docs/js/app.js`: 应用主入口和事件协调
- `docs/js/chat.js`: 聊天逻辑和消息处理
- `docs/js/ui.js`: UI渲染和DOM操作
- `docs/js/storage.js`: 数据持久化和导入导出

## MCP服务器开发模式

### Python MCP服务器 (FastMCP)
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
async def tool_function(param: str) -> str:
    """工具文档"""
    # 实现逻辑
    return result
```
参考: `mcp_server/web_search/server.py`

### TypeScript MCP服务器
```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js"

const server = new McpServer({ name: "server-name", version: "0.1.0" })

server.tool("tool-name", "description", schema, async (args) => {
    // 实现逻辑
    return { content: [{ type: "text", text: result }] }
})
```
参考: `mcp_server/douban_search/src/index.ts`

## 环境变量和密钥配置

所有敏感配置都存储在 `config.json` 的 `env` 字段中：
- ZHIPU_API_KEY: 智谱AI API密钥
- SERPER_API_KEY: Google搜索API密钥
- AMAP_MAPS_API_KEY: 高德地图API密钥
- 其他服务的认证凭证

## 数据流和集成模式

### 典型请求流程
1. 前端发送聊天请求到 FastAPI 后端
2. 后端通过 `MultiServerManager` 调用相应的MCP工具
3. MCP服务器执行具体搜索或数据处理任务
4. 结果通过统一的接口返回给前端
5. 前端渲染响应并更新UI

### LLM集成模式
- 系统支持工具调用和RAG检索增强生成
- 通过 `backend/core/llm_client.py` 抽象不同LLM提供商
- 支持流式响应和实时消息更新

## 特殊注意事项

### 服务进程管理
- MCP服务器通过stdio协议与主应用通信
- 每个MCP服务器都是独立的Python/Node.js进程
- 使用 `scripts/start_all.sh` 进行进程管理和优雅关闭

### 前端技术栈
- 使用原生JavaScript ES6+模块，无需构建工具
- CSS采用模块化架构，支持CSS自定义属性
- 响应式设计，支持移动端适配

### 测试框架
- 当前缺少正式测试框架
- 建议使用 pytest 进行后端测试
- 可参考 `mcp_server/local_sai_search/server_test.py`

### 部署要求
- Python 3.12+
- Node.js 18+ (用于TypeScript MCP服务器)
- 支持静态文件托管的服务器环境
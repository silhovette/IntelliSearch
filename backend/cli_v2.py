# * CLI version of IntelliSearch - Optimized Version
import os
import dotenv
import json
import logging
import asyncio
import argparse
import sys

sys.path.append(os.getcwd())
# set up logging config
from utils.log_config import setup_logging

logging.getLogger("mcp").setLevel(logging.CRITICAL)

from pathlib import Path
from openai import OpenAI
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from zai import ZhipuAiClient
from mcp_module.server_manager import MultiServerManager
from mcp.types import CallToolResult
from colorama import Fore, Style, init
from prompt_toolkit import prompt
from rich.console import Console
from backend.tool_hash import fix_tool_args

init(autoreset=True)
dotenv.load_dotenv(override=True)
setup_logging(log_file_path="./log/mcp.log", project_prefix="IntelliSearch Main")


class MCPChat:
    def __init__(
        self,
        model_name: str = "glm-4.5",
        system_prompt: str = "You are a helpful assistant",
        server_config_path: str = "./config.json",
        max_tool_call: int = 5,
    ):
        self.model_name = model_name
        self.history = []
        self.system_prompt = system_prompt
        self.history.append({"role": "system", "content": system_prompt})
        self.time_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.result_dir = "./results"
        self.max_tool_call = int(max_tool_call)
        os.makedirs(self.result_dir, exist_ok=True)

        self.base_url = os.environ.get("BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Environment variable 'OPENAI_API_KEY' not found. Please set it."
            )

        self.client = OpenAI(api_key=api_key, base_url=self.base_url)

        # handle mcp settings and connecting mcp servers
        self.config_path = server_config_path
        self.config = self.load_server_configs(config_path=self.config_path)
        self.server_manager = MultiServerManager(server_configs=self.config)
        # list all the tools available
        self.available_tools = []

        # setup logger
        self.logger = logging.getLogger(__name__)
        TOOL_CALL_ERROR = 35
        logging.addLevelName(TOOL_CALL_ERROR, "TOOL CALL ERROR")
        self.logger.info(
            f"Chat with MCP enhancement client initialized for model: {self.model_name}"
        )

    def stream_chat_response_simple(self, available_tools=None):
        result_text = ""

        # 创建流式响应
        if available_tools:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                tools=available_tools,
                stream=True,
                temperature=0.8,
            )
        else:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                stream=True,
                temperature=0.8,
            )

        # 使用你要求的格式处理流式输出
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                print(
                    Style.BRIGHT + Fore.YELLOW + chunk.choices[0].delta.content,
                    end="",
                    flush=True,
                )
                result_text += chunk.choices[0].delta.content

        print()  # 换行

        # 获取最终消息用于工具调用处理
        if available_tools:
            # 重新调用一次非流式API来获取工具调用信息
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                tools=available_tools,
                stream=False,
                temperature=0.8,
            )
        else:
            # 重新调用一次非流式API来获取完整响应
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                stream=False,
                temperature=0.8,
            )

        return result_text, response

    async def list_tools(self):
        try:
            self.logger.info("🔌 Connecting and discovering tools...")
            all_tools = await self.server_manager.connect_all_servers()
            with open(
                f"./results/{self.time_stamp}_list_tools.json", "w", encoding="utf-8"
            ) as file:
                json.dump(all_tools, file, indent=4, ensure_ascii=False)

            if not all_tools:
                raise RuntimeError("No tools discovered.")
            return all_tools
        except Exception as e:
            self.logger.error(f"Error while connecting MCP Servers: {e}")
            return []
        finally:
            await self.server_manager.close_all_connections()

    def load_server_configs(self, config_path: Path):
        """从 MCP config 文件加载并转换 server 配置"""
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        servers = []

        for name, conf in cfg.get("mcpServers", {}).items():
            if conf.get("transport") == "sse":
                servers.append(
                    {
                        "name": name,
                        "url": conf.get("url"),
                        "transport": conf.get("transport", "sse"),
                    }
                )
            else:
                servers.append(
                    {
                        "name": name,
                        "command": [conf.get("command")] + conf.get("args", []),
                        "env": conf.get("env"),
                        "cwd": conf.get("cwd"),
                        "transport": conf.get("transport", "stdio"),
                        "port": conf.get("port", None),
                        "endpoint": conf.get("endpoint", "/mcp"),
                    }
                )
        return servers

    async def get_tool_response(
        self,
        call_params: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
    ) -> Any:
        """连接 MCP server 并调用工具，返回结果"""
        try:
            self.logger.info("🔌 Connecting and discovering tools...")
            all_tools = await self.server_manager.connect_all_servers()

            if not all_tools:
                raise RuntimeError("No tools discovered.")

            if tool_name is None:
                tool_name = next(iter(all_tools.keys()))
            if tool_name not in all_tools:
                raise ValueError(f"Tool '{tool_name}' not found.")

            self.logger.info(f"🚀 Calling tool: {tool_name}")
            result = await self.server_manager.call_tool(
                tool_name, call_params or {}, use_cache=False
            )
            self.logger.info("✅ Tool call SUCCESS.")
            return result

        finally:
            await self.server_manager.close_all_connections()

    def get_system_prompt(self):
        return self.system_prompt

    def append_history(self, append_history: Optional[List[Dict[str, str]]] = None):
        if append_history:
            try:
                for history_episode in append_history:
                    role = history_episode.get("role", None)
                    if role and role in ("system", "user", "assistant"):
                        self.history.append(history_episode)
                    else:
                        self.logger.error(f"Error for role: {role}")
            except Exception as e:
                self.logger.error(f"Updating History Failed: {e}")

    async def process_query(self, user_message: str, stream: bool = True):
        """处理用户查询的简化版本"""
        tools = await self.list_tools()
        self.logger.info(f"Available Tools: {tools}")
        self.tools_store = tools
        available_tools = [
            {
                "type": "function",
                "function": {
                    "name": f"{tool.get('name')}",
                    "description": tool.get("description"),
                    "input_schema": tool.get("input_schema"),
                },
            }
            for tool in list(tools.values())
        ]

        # 添加用户消息到历史
        self.history.append({"role": "user", "content": user_message})

        try:
            for round_count in range(self.max_tool_call):
                self.logger.info(f"Processing round {round_count + 1}")

                # 使用简化的流式输出
                final_text, response = self.stream_chat_response_simple(
                    available_tools=available_tools
                )

                # 检查是否需要工具调用
                if response.choices[0].finish_reason == "tool_calls":
                    # 添加助手消息到历史记录
                    self.history.append(response.choices[0].message.model_dump())

                    tool_results_for_history = []
                    for tool_call_single in response.choices[0].message.tool_calls:
                        tool_name = tool_call_single.function.name
                        print(f"\n🚀 Calling Tool: {tool_name}\n")
                        self.logger.info(f"Calling tool: {tool_call_single}")

                        # 查找完整工具名称
                        tool_name_long = None
                        for chunk in list(tools.values()):
                            if chunk.get("name") == tool_name:
                                tool_name_long = (
                                    f"{chunk.get('server')}:{chunk.get('name')}"
                                )
                                break

                        if not tool_name_long:
                            tool_result_content = (
                                f"Error: Tool '{tool_name}' not found."
                            )
                        else:
                            try:
                                tool_args = json.loads(
                                    tool_call_single.function.arguments
                                )
                                self.logger.info(f"Tool calling args: {tool_args}")

                                # 显示工具调用的输入参数
                                print(f"{Fore.CYAN}🔧 Tool Input Parameters:")
                                print(f"{Fore.CYAN}   Tool: {tool_name_long}")
                                print(f"{Fore.CYAN}   Arguments: {json.dumps(tool_args, indent=2, ensure_ascii=False)}")
                                print(f"{Fore.MAGENTA}⏳ Executing tool...{Style.RESET_ALL}\n")

                                # 修复工具参数
                                tool_args = fix_tool_args(
                                    tools=tools,
                                    tool_args=tool_args,
                                    tool_name=tool_name_long,
                                )
                                result: CallToolResult = await self.get_tool_response(
                                    call_params=tool_args, tool_name=tool_name_long
                                )
                                tool_result_content = result.model_dump()["content"][0][
                                    "text"
                                ]

                                # 显示工具调用的输出结果（截断长内容）
                                print(f"{Fore.GREEN}✅ Tool Execution Result:")
                                if len(tool_result_content) > 500:
                                    truncated_result = tool_result_content[:500] + "...(truncated)"
                                    print(f"{Fore.GREEN}   Result (first 500 chars): {truncated_result}")
                                    print(f"{Fore.GREEN}   Full result length: {len(tool_result_content)} characters")
                                else:
                                    print(f"{Fore.GREEN}   Result: {tool_result_content}")
                                print(f"{Style.RESET_ALL}\n")

                            except Exception as tool_e:
                                print(f"{Fore.RED}❌ Tool execution failed: {tool_e}{Style.RESET_ALL}\n")
                                tool_result_content = f"Tool execution failed: {tool_e}"

                        # 添加工具结果到消息列表
                        tool_results_for_history.append(
                            {
                                "role": "tool",
                                "content": tool_result_content,
                                "tool_call_id": tool_call_single.id,
                            }
                        )

                    self.history.extend(tool_results_for_history)
                    continue
                else:
                    # LLM 完成响应，返回最终内容
                    final_content = response.choices[0].message.content
                    self.history.append({"role": "assistant", "content": final_content})
                    return final_content

            # 超过工具调用限制
            self.logger.error(f"Tool calling limit reached: {self.max_tool_call} times")
            self.history.append(
                {
                    "role": "user",
                    "content": "Error, you have reached the maximum limit of tool calling requests. Please use the information you get by the tools to generate the final answer.",
                }
            )

            # 最终响应（不使用工具）
            final_text, response = self.stream_chat_response_simple(available_tools=[])
            final_content = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": final_content})
            return final_content

        except Exception as e:
            error_message = f"Error calling LLM API: {e}"
            self.logger.error(error_message, exc_info=True)
            if stream:
                return [f"[LLM Error]: {error_message}\n"]
            else:
                raise RuntimeError(error_message)

    def export_message(self, output_file_path: str = None):
        if not output_file_path:
            output_file_path = os.path.join(
                self.result_dir, f"./{self.time_stamp}_memory.json"
            )
        dir, file = os.path.split(output_file_path)
        os.makedirs(dir, exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as file:
            json.dump(self.history, file, ensure_ascii=False, indent=4)
            self.logger.info(f"Successfully writing messages into {output_file_path}")


async def query(chat_client: MCPChat, user_query):
    console = Console()
    console.print("\n[bold green]Model Response:[/bold green]")

    result = await chat_client.process_query(
        user_message=user_query,
        stream=False,
    )
    chat_client.export_message()
    print("\n\n")


if __name__ == "__main__":
    # 加载系统提示词
    try:
        with open("prompts/base_system_prompt.md", "r", encoding="utf-8") as file:
            SYSTEM_PROMPT = file.read()
    except FileNotFoundError:
        SYSTEM_PROMPT = "You are a helpful assistant"

    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="deepseek-chat")
    parser.add_argument("--max_tool_calls", type=int, default=10)
    parser.add_argument("--system_prompt", type=str, default=SYSTEM_PROMPT)
    args = parser.parse_args()

    console = Console()
    chat_client = MCPChat(
        model_name=args.model_name,
        system_prompt=args.system_prompt,
        max_tool_call=args.max_tool_calls,
    )

    console.print(
        "[bold blue]IntelliSearch CLI v2 - Enhanced with MCP Tools[/bold blue]"
    )
    console.print("Type '/exit' to quit\n")

    while True:
        try:
            user_input = prompt("Input your query: ")
            if str(user_input).lower() == "/exit":
                console.print("[bold red]Exiting... Goodbye! 👋[/bold red]")
                break
            asyncio.run(query(chat_client=chat_client, user_query=user_input))
        except KeyboardInterrupt:
            console.print(
                "\n[bold yellow]Interrupted. Type /exit to quit gracefully.[/bold yellow]"
            )
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")

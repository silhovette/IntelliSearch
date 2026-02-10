#!/usr/bin/env python3
"""
MCP Server Automated Testing Framework

This script automates testing of MCP servers by simulating agent tool calls.
Test parameters are loaded from JSON files in the test_mcp_params directory.

Usage:
    python test_mcp_tool.py server1 server2 server3

Example:
    python test/test_mcp_tool.py base_toolkit search_geo search_movie
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Add parent directory to path to import from tools and agents modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_loader import Config
from tools.mcp_base import MCPBase
from core.logger import get_logger
import logging

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


class Colors:
    """Color codes for terminal output"""

    @staticmethod
    def green(text: str) -> str:
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def red(text: str) -> str:
        return f"{Fore.RED}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def yellow(text: str) -> str:
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def blue(text: str) -> str:
        return f"{Fore.BLUE}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def cyan(text: str) -> str:
        return f"{Fore.CYAN}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def bold(text: str) -> str:
        return f"{Style.BRIGHT}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def dim(text: str) -> str:
        return f"{Style.DIM}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text

    @staticmethod
    def white(text: str) -> str:
        return f"{Fore.WHITE}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text


def format_output(content: Any, max_length: int = 500) -> str:
    """
    Format tool output with length limit.

    Args:
        content: Content to format (can be dict, list, or string)
        max_length: Maximum character length for output

    Returns:
        Formatted string representation
    """
    if content is None:
        return Colors.dim("None")

    # Convert to string
    if isinstance(content, (dict, list)):
        try:
            content_str = json.dumps(content, indent=2, ensure_ascii=False)
        except:
            content_str = str(content)
    else:
        content_str = str(content)

    # Truncate if too long
    if len(content_str) > max_length:
        truncated = content_str[:max_length]
        return truncated + Colors.dim(f"\n... (truncated, total {len(content_str)} chars)")

    return content_str


def format_duration(duration_ms: float) -> str:
    """
    Format duration with color coding.

    Args:
        duration_ms: Duration in milliseconds

    Returns:
        Colored and formatted duration string
    """
    if duration_ms < 200:
        return Colors.green(f"{duration_ms:.2f}ms")
    elif duration_ms < 500:
        return Colors.yellow(f"{duration_ms:.2f}ms")
    else:
        return Colors.red(f"{duration_ms:.2f}ms")


def print_test_header(text: str):
    """Print a formatted header"""
    line = "=" * 80
    print(f"\n{Colors.bold(line)}")
    print(f"{Colors.bold(text)}")
    print(f"{Colors.bold(line)}\n")


def print_test_result(test_num: int, total: int, tool_name: str, success: bool,
                     duration_ms: float, output: Any = None, error: str = None,
                     input_params: Dict = None):
    """
    Print formatted test result.

    Args:
        test_num: Current test number
        total: Total number of tests
        tool_name: Name of the tool being tested
        success: Whether the test passed
        duration_ms: Execution time in milliseconds
        output: Tool output (if successful)
        error: Error message (if failed)
        input_params: Input parameters for the tool
    """
    # Test number and status
    status_icon = Colors.green("PASSED") if success else Colors.red("FAILED")
    print(f"  Test {Colors.cyan(f'{test_num}/{total}')}: {Colors.bold(tool_name)} - {status_icon}")

    # Duration
    duration_str = format_duration(duration_ms)
    print(f"    └─ Duration: {duration_str}")

    # Input parameters
    if input_params:
        print(f"    └─ Input: {Colors.dim(format_output(input_params, max_length=200))}")

    # Output or error
    if success and output is not None:
        print(f"    └─ Output:")
        output_str = format_output(output, max_length=500)
        for line in output_str.split('\n'):
            print(f"      {line}")
    elif error:
        print(f"    └─ Error: {Colors.red(error)}")

    print()


class MCPServerTester:
    """Test suite for MCP servers"""

    def __init__(self, server_name: str, params_dir: str = None, config_path: str = None):
        """
        Initialize the tester for a specific server.

        Args:
            server_name: Name of the MCP server to test
            params_dir: Directory containing test parameter files
            config_path: Path to config.yaml file
        """
        self.server_name = server_name
        self.params_dir = Path(params_dir or "test/test_mcp_params")
        self.config_path = config_path or "config/config.yaml"

        # Load configuration using Config class (same as cli.py)
        self.config = Config(config_file_path=self.config_path)
        self.config.load_config(override=True)

        self.test_results = {
            "server": server_name,
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
        self.logger = get_logger(__name__)

        # MCPBase instance (only one per tester)
        self.mcp_base = None

    def load_test_params(self) -> Optional[Dict[str, Any]]:
        """
        Load test parameters from JSON file.

        Returns:
            Test parameters dictionary or None if file not found
        """
        param_file = self.params_dir / f"{self.server_name}.json"

        if not param_file.exists():
            self.logger.warning(f"Parameter file not found: {param_file}")
            print(f"{Colors.yellow('Warning:')} Parameter file not found: {param_file}")
            return None

        try:
            with open(param_file, 'r', encoding='utf-8') as f:
                params = json.load(f)
            print(f"{Colors.dim('Loaded test parameters from')} {param_file}")
            return params
        except Exception as e:
            print(f"{Colors.red('Error loading parameters:')} {e}")
            self.logger.error(f"Failed to load parameters: {e}")
            return None

    def _create_test_config(self) -> str:
        """
        Create a temporary config with only the server to test.

        Returns:
            Path to temporary config file
        """
        # Create temporary config with only the test server
        test_config = {
            "all_servers": self.config.get("all_servers", {}),
            "server_choice": [self.server_name]
        }

        # Write to temp file
        temp_config_path = self.params_dir / f"temp_config_{self.server_name}.yaml"
        try:
            import yaml
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(test_config, f, allow_unicode=True)
            self.logger.info(f"Created temporary config: {temp_config_path}")
            return str(temp_config_path)
        except Exception as e:
            self.logger.error(f"Failed to create temp config: {e}")
            return self.config_path

    async def test_tool(self, tool_name: str, input_params: Dict[str, Any],
                       available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a single tool with given parameters.

        Args:
            tool_name: Name of the tool to test
            input_params: Parameters to pass to the tool
            available_tools: Dictionary of available tools

        Returns:
            Test result dictionary
        """
        result = {
            "tool": tool_name,
            "input_params": input_params,
            "success": False,
            "result": None,
            "error": None,
            "duration_ms": 0
        }

        if not self.mcp_base:
            result["error"] = "MCPBase not initialized"
            return result

        try:
            start_time = datetime.now()

            # Find the full tool name (server:tool format)
            tool_name_long = None
            for tool_info in list(available_tools.values()):
                if tool_info.get("name") == tool_name:
                    tool_name_long = f"{tool_info.get('server')}:{tool_info.get('name')}"
                    break

            if not tool_name_long:
                result["error"] = f"Tool '{tool_name}' not found in available tools"
                return result

            # Execute the tool
            response = await self.mcp_base.get_tool_response(tool_name=tool_name_long, call_params=input_params)
            response = response.model_dump()

            if response:
                tool_result = response
                result["result"] = tool_result
                result["success"] = True
            else:
                result["error"] = "No response from tool"

            end_time = datetime.now()
            result["duration_ms"] = (end_time - start_time).total_seconds() * 1000

        except Exception as e:
            result["error"] = str(e)
            result["duration_ms"] = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Tool test failed: {e}")

        return result

    async def run_tests(self) -> Dict[str, Any]:
        """
        Run all tests for the server.

        Returns:
            Complete test results
        """
        print_test_header(f"Testing MCP Server: {Colors.cyan(self.server_name)}")

        # Load test parameters
        test_params = self.load_test_params()
        if not test_params:
            return self.test_results

        # Get test cases - tests is an array of test cases
        test_cases = test_params.get("tests", [])
        if not test_cases:
            print(Colors.yellow("No tool tests found in parameter file"))
            return self.test_results

        # Check if server exists in config
        all_servers = self.config.get("all_servers", {})
        if self.server_name not in all_servers:
            error_msg = f"Server '{self.server_name}' not found in config.yaml"
            self.logger.error(error_msg)
            self.test_results["error"] = error_msg
            return self.test_results

        # Create temporary config with only this server
        temp_config_path = self._create_test_config()
        print(f"{Colors.dim('Config:')} {temp_config_path}")

        try:
            # Initialize MCP connection with test config (only once!)
            print(f"{Colors.blue('Initializing MCP connection...')}")

            self.mcp_base = MCPBase(config_path=temp_config_path)

            # List available tools
            tools = await self.mcp_base.list_tools()
            tool_names = [tool.get("name") for tool in tools.values()]

            if not tools:
                self.logger.error("No tools discovered from server")
                self.test_results["error"] = "No tools discovered"
                return self.test_results

            print(f"{Colors.green('Connected')} - Available tools: {', '.join([Colors.cyan(name) for name in tool_names])}\n")

            # Run each test case
            test_results = []
            total_tests = len(test_cases)
            passed_tests = 0
            total_time = 0

            for i, test_case in enumerate(test_cases, 1):
                tool_name = test_case.get("tool")
                input_params = test_case.get("input_params", {})

                if not tool_name:
                    self.logger.error("Missing 'tool' field")
                    print_test_result(
                        test_num=i,
                        total=total_tests,
                        tool_name="Unknown",
                        success=False,
                        duration_ms=0,
                        error="Missing 'tool' field in test case",
                        input_params=input_params
                    )
                    test_results.append({
                        "tool": None,
                        "input_params": input_params,
                        "success": False,
                        "error": "Missing 'tool' field in test case",
                        "duration_ms": 0
                    })
                    continue

                if tool_name not in tool_names:
                    error_msg = f"Tool '{tool_name}' not found in server"
                    self.logger.error(f"{error_msg}. Available: {tool_names}")
                    print_test_result(
                        test_num=i,
                        total=total_tests,
                        tool_name=tool_name,
                        success=False,
                        duration_ms=0,
                        error=error_msg,
                        input_params=input_params
                    )
                    test_results.append({
                        "tool": tool_name,
                        "input_params": input_params,
                        "success": False,
                        "error": error_msg,
                        "duration_ms": 0
                    })
                    continue

                # Run test
                result = await self.test_tool(tool_name, input_params, tools)

                # Print formatted result
                print_test_result(
                    test_num=i,
                    total=total_tests,
                    tool_name=tool_name,
                    success=result["success"],
                    duration_ms=result["duration_ms"],
                    output=result.get("result"),
                    error=result.get("error"),
                    input_params=input_params
                )

                if result["success"]:
                    passed_tests += 1
                total_time += result["duration_ms"]

                test_results.append(result)

            self.test_results["tests"] = test_results
            self.test_results["summary"] = {
                "total": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "total_time_ms": total_time,
                "avg_time_ms": total_time / total_tests if total_tests > 0 else 0
            }

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}", exc_info=True)
            self.test_results["error"] = str(e)

        finally:
            # Cleanup temporary config file
            temp_file = Path(temp_config_path)
            if temp_file.exists() and temp_file.name.startswith("temp_config_"):
                try:
                    temp_file.unlink()
                    print(f"{Colors.dim('Cleaned up temporary config')}\n")
                except:
                    pass

        return self.test_results

    def print_summary(self):
        """Print test summary with statistics"""
        print_test_header(f"Test Summary: {Colors.cyan(self.server_name)}")

        tests = self.test_results.get("tests", [])
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t.get("success"))
        failed_tests = total_tests - passed_tests

        # Calculate statistics
        summary = self.test_results.get("summary", {})
        total_time = summary.get("total_time_ms", 0)
        avg_time = summary.get("avg_time_ms", 0)

        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100

            # Print statistics with colors
            print(f"  Total tests:     {Colors.bold(str(total_tests))}")
            print(f"  {Colors.green('Passed:')}         {Colors.bold(str(passed_tests))}")
            print(f"  {Colors.red('Failed:')}         {Colors.bold(str(failed_tests))}")
            print(f"  Success rate:    {Colors.bold(f'{success_rate:.1f}%')}")
            print(f"  Total time:      {format_duration(total_time)}")
            print(f"  Avg time/test:   {format_duration(avg_time)}")

            # Success rate bar
            bar_length = 40
            filled = int(bar_length * success_rate / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\n  {bar} {success_rate:.1f}%")
        else:
            print(Colors.yellow("  No tests executed"))

        print()

    def save_results(self, output_dir: str = None):
        """
        Save test results to JSON file.

        Args:
            output_dir: Directory to save results (default: test_results)
        """
        output_dir = Path(output_dir or "test/test_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"{self.server_name}_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"{Colors.dim('Results saved to:')} {output_file}")


async def test_servers(server_names: List[str], config_path: str = None,
                      params_dir: str = None, output_dir: str = None):
    """
    Test multiple MCP servers.

    Args:
        server_names: List of server names to test
        config_path: Path to config.yaml file
        params_dir: Directory containing test parameter files
        output_dir: Directory to save test results
    """
    all_results = []
    total_passed = 0
    total_failed = 0

    for server_name in server_names:
        tester = MCPServerTester(server_name, params_dir, config_path)
        results = await tester.run_tests()
        tester.print_summary()

        if output_dir:
            tester.save_results(output_dir)

        # Collect statistics
        if results.get("tests"):
            passed = sum(1 for t in results["tests"] if t.get("success"))
            failed = len(results["tests"]) - passed
            total_passed += passed
            total_failed += failed

        all_results.append(results)

    # Print overall summary
    if len(server_names) > 1:
        print_test_header(f"Overall Summary - {len(server_names)} servers tested")

        total_tests = total_passed + total_failed
        if total_tests > 0:
            success_rate = (total_passed / total_tests) * 100
            print(f"  Total tests:     {Colors.bold(str(total_tests))}")
            print(f"  {Colors.green('Passed:')}         {Colors.bold(str(total_passed))}")
            print(f"  {Colors.red('Failed:')}         {Colors.bold(str(total_failed))}")
            print(f"  Success rate:    {Colors.bold(f'{success_rate:.1f}%')}")

            # Success rate bar
            bar_length = 40
            filled = int(bar_length * success_rate / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\n  {bar} {success_rate:.1f}%")
        print()


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="MCP Server Automated Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test a single server
  python test/test_mcp_tool.py base_toolkit

  # Test multiple servers
  python test/test_mcp_tool.py base_toolkit search_geo search_movie

  # Specify custom config and parameters directory
  python test/test_mcp_tool.py base_toolkit --config config/config.yaml --params test/test_mcp_params

  # Save test results
  python test/test_mcp_tool.py base_toolkit --output test/test_results

Test parameter file format (test_mcp_params/{server_name}.json):
{
  "tests": [
    {
      "tool": "tool_name",
      "input_params": {"param1": "value1"}
    }
  ]
}

Available servers (from config.yaml all_servers):
  - base_toolkit
  - search_geo
  - search_movie
  - search_bilibili
  - search_scholar
  - search_web
  - search_train
  - search_github
  - etc.
        """
    )

    parser.add_argument(
        "servers",
        nargs="+",
        help="Names of MCP servers to test (must match keys in config.yaml all_servers)"
    )
    parser.add_argument(
        "--config", "-c",
        default="config/config.yaml",
        help="Path to MCP server config file in YAML format (default: config/config.yaml)"
    )
    parser.add_argument(
        "--params", "-p",
        default="test/test_mcp_params",
        help="Directory containing test parameter files (default: test/test_mcp_params)"
    )
    parser.add_argument(
        "--output", "-o",
        default="test/test_results",
        help="Directory to save test results (default: test/test_results)"
    )

    args = parser.parse_args()

    # Run tests
    asyncio.run(test_servers(
        server_names=args.servers,
        config_path=args.config,
        params_dir=args.params,
        output_dir=args.output
    ))


if __name__ == "__main__":
    main()

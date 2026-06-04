"""Framework-agnostic tools used by both apps.

Each tool is an ``async`` callable returning a JSON-serializable result and
raises ``ToolError`` on failure. Agents wrap these in LangChain ``StructuredTool`` /
LangGraph nodes; the tools themselves know nothing about agents.

Importing a tool must not fail just because its API key is unset — config
checking happens at call time so the import graph stays clean.
"""
from shared.tools.errors import ToolError

__all__ = ["ToolError"]

"""Exercise HITL replay through public APIs with inert, deterministic tools."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware


class ScriptedModel(BaseChatModel):
    """Propose the same two calls, then finish after receiving tool results."""

    @property
    def _llm_type(self) -> str:
        return "scripted-hitl-repro"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        calls = (
            []
            if any(isinstance(m, ToolMessage) for m in messages)
            else [{"name": name, "args": {}, "id": f"call_{name}"} for name in ("alpha", "beta")]
        )
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="", tool_calls=calls))]
        )

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self


async def run_case(mode: str, asynchronous: bool, after: set[str]) -> dict[str, Any]:
    selected = {"alpha"}
    executed: list[str] = []

    @tool
    def alpha() -> str:
        """Record alpha execution in a local list."""
        executed.append("alpha")
        return "alpha"

    @tool
    def beta() -> str:
        """Record beta execution in a local list."""
        executed.append("beta")
        return "beta"

    options = {"interrupt_mode": mode} if mode == "per_call" else {}
    middleware = HumanInTheLoopMiddleware(
        interrupt_on={
            name: {
                "allowed_decisions": ["approve", "reject"],
                "when": lambda request: request.tool_call["name"] in selected,
            }
            for name in ("alpha", "beta")
        },
        **options,
    )
    agent = create_agent(
        ScriptedModel(), [alpha, beta], middleware=[middleware], checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "hitl-when-replay"}}

    async def invoke(value: Any) -> dict[str, Any]:
        if asynchronous:
            return await agent.ainvoke(value, config)
        return agent.invoke(value, config)

    paused = await invoke({"messages": [{"role": "user", "content": "Run alpha and beta."}]})
    pending = paused["__interrupt__"]
    shown = (
        [a["name"] for a in pending[0].value["action_requests"]]
        if mode == "batched"
        else [i.value["name"] for i in pending]
    )
    assert shown == ["alpha"], shown
    selected.clear()
    selected.update(after)
    response = (
        {"decisions": [{"type": "reject"}]}
        if mode == "batched"
        else {pending[0].id: {"type": "reject"}}
    )
    result: dict[str, Any] = {
        "mode": mode,
        "async": asynchronous,
        "reviewed": shown,
        "selected_on_resume": sorted(after),
    }
    try:
        resumed = await invoke(Command(resume=response))
        result["rejected_ids"] = [
            m.tool_call_id
            for m in resumed["messages"]
            if isinstance(m, ToolMessage) and m.status == "error"
        ]
        result["pending_after_resume"] = len(resumed.get("__interrupt__", ()))
    except ValueError as error:
        result["error"] = str(error)
    result["executed"] = sorted(executed)
    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-call", action="store_true")
    args = parser.parse_args()
    modes = ["batched", "per_call"] if args.per_call else ["batched"]
    for mode in modes:
        for asynchronous in (False, True):
            for after in ({"alpha"}, {"beta"}, {"alpha", "beta"}, set()):
                print(json.dumps(await run_case(mode, asynchronous, after), sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())

import pytest
from langsmith import unit

from dataanalysis_agent import graph


@pytest.mark.asyncio
@unit
async def test_dataanalysis_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "Who is the founder of LangChain?")]},
        {"configurable": {"system_prompt": "You are a helpful AI assistant."}},
    )

    assert "harrison" in str(res["messages"][-1].content).lower()

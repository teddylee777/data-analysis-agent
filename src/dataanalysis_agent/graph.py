"""Define a custom Reasoning and Action agent.

Works with a chat model with tool calling support.
"""

from datetime import UTC, datetime
from typing import Dict, List, Literal, cast
import re

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from dataanalysis_agent.configuration import Configuration
from dataanalysis_agent.state import InputState, State
from dataanalysis_agent.tools import TOOLS
from dataanalysis_agent.utils import load_chat_model

# Define the function that calls the model


def extract_images_from_messages(messages: List) -> List[str]:
    """Extract all markdown image tags from tool messages."""
    images = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            # Find all markdown image tags in the tool message content
            # Pattern matches ![alt text](http://localhost:8001/filename.png)
            img_pattern = r'(!\[[^\]]*\]\(http://localhost:8001/[^)]+\))'
            found_images = re.findall(img_pattern, msg.content)
            images.extend(found_images)
    return images


async def call_model(state: State) -> Dict[str, List[AIMessage]]:
    """Call the LLM powering our "agent".

    This function prepares the prompt, initializes the model, and processes the response.

    Args:
        state: The current state of the conversation.
    """
    configuration = Configuration.from_context()

    # Initialize the model with tool binding. Change the model or add more tools here.
    model = load_chat_model(configuration.model).bind_tools(TOOLS)

    # Format the system prompt. Customize this to change the agent's behavior.
    system_message = configuration.system_prompt.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    # Get the model's response
    response = cast(
        AIMessage,
        await model.ainvoke(
            [{"role": "system", "content": system_message}, *state.messages]
        ),
    )

    # Handle the case when it's the last step and the model still wants to use a tool
    if state.is_last_step and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Sorry, I could not find an answer to your question in the specified number of steps.",
                )
            ]
        }

    # Check if there are any images in recent tool messages
    # Look at the last few messages to find tool responses
    recent_images = []
    for i in range(len(state.messages) - 1, max(0, len(state.messages) - 5), -1):
        msg = state.messages[i]
        if isinstance(msg, ToolMessage) and '![' in msg.content and 'http://localhost:8001/' in msg.content:
            images = extract_images_from_messages([msg])
            recent_images.extend(images)
            break  # Only get images from the most recent tool call

    # If we found images and this is not a tool-calling response, prepend them
    messages_to_return = []
    
    if recent_images and not response.tool_calls:
        # Create a message with just the images
        image_content = "\n".join(recent_images)
        messages_to_return.append(
            AIMessage(
                content=image_content,
                id=f"{response.id}_images"
            )
        )
    
    # Add the original response
    messages_to_return.append(response)
    
    # Return all messages
    return {"messages": messages_to_return}


# Define a new graph

builder = StateGraph(State, input=InputState, config_schema=Configuration)

# Define the two nodes we will cycle between
builder.add_node(call_model)
builder.add_node("tools", ToolNode(TOOLS))

# Set the entrypoint as `call_model`
# This means that this node is the first one called
builder.add_edge("__start__", "call_model")


def route_model_output(state: State) -> Literal["__end__", "tools"]:
    """Determine the next node based on the model's output.

    This function checks if the model's last message contains tool calls.

    Args:
        state: The current state of the conversation.
    """
    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )
    # If there is no tool call, then we finish
    if not last_message.tool_calls:
        return "__end__"
    # Otherwise we execute the requested actions
    return "tools"


# Add a conditional edge to determine the next step after `call_model`
builder.add_conditional_edges(
    "call_model",
    # After call_model finishes running, the next node(s) are scheduled
    # based on the output from route_model_output
    route_model_output,
)

# Add a normal edge from `tools` to `call_model`
# This creates a cycle: after using tools, we always return to the model
builder.add_edge("tools", "call_model")

# Compile the builder into an executable graph
graph = builder.compile(name="ReAct Agent")

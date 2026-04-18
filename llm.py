import json
import os
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" or "openai"


def _get_anthropic_client():
    from anthropic import Anthropic

    return Anthropic()


def _get_openai_client():
    from openai import OpenAI

    return OpenAI()


def extract_structured(
    prompt: str,
    schema: Type[T],
    system: str = "",
    provider: str | None = None,
) -> T:
    provider = provider or PROVIDER

    if provider == "anthropic":
        return _anthropic_structured(prompt, schema, system)
    elif provider == "openai":
        return _openai_structured(prompt, schema, system)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def extract_structured_list(
    prompt: str,
    item_schema: Type[T],
    system: str = "",
    provider: str | None = None,
) -> list[T]:
    provider = provider or PROVIDER

    if provider == "anthropic":
        return _anthropic_structured_list(prompt, item_schema, system)
    elif provider == "openai":
        return _openai_structured_list(prompt, item_schema, system)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# --- Anthropic ---


def _anthropic_structured(prompt: str, schema: Type[T], system: str) -> T:
    client = _get_anthropic_client()
    tool_name = schema.__name__.lower()
    tool_schema = schema.model_json_schema()
    # Remove $defs and other non-input-schema keys that Anthropic doesn't accept
    tool_schema.pop("$defs", None)
    tool_schema.pop("title", None)

    messages = [{"role": "user", "content": prompt}]
    kwargs = {}
    if system:
        kwargs["system"] = system

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=4096,
        tools=[
            {
                "name": tool_name,
                "description": f"Return structured {schema.__name__} data",
                "input_schema": tool_schema,
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=messages,
        **kwargs,
    )

    for block in response.content:
        if block.type == "tool_use":
            return schema.model_validate(block.input)

    raise RuntimeError("No tool_use block in response")


def _anthropic_structured_list(
    prompt: str, item_schema: Type[T], system: str
) -> list[T]:
    client = _get_anthropic_client()
    # Create a wrapper schema for the list
    wrapper_schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": item_schema.model_json_schema(),
            }
        },
        "required": ["items"],
    }
    # Clean nested schemas
    _clean_schema(wrapper_schema)

    messages = [{"role": "user", "content": prompt}]
    kwargs = {}
    if system:
        kwargs["system"] = system

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=8192,
        tools=[
            {
                "name": "extract_list",
                "description": f"Return a list of {item_schema.__name__} items",
                "input_schema": wrapper_schema,
            }
        ],
        tool_choice={"type": "tool", "name": "extract_list"},
        messages=messages,
        **kwargs,
    )

    for block in response.content:
        if block.type == "tool_use":
            items = block.input.get("items", [])
            return [item_schema.model_validate(item) for item in items]

    raise RuntimeError("No tool_use block in response")


# --- OpenAI ---


def _openai_structured(prompt: str, schema: Type[T], system: str) -> T:
    client = _get_openai_client()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.beta.chat.completions.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=messages,
        response_format=schema,
    )

    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("OpenAI returned no parsed output")
    return parsed


def _openai_structured_list(
    prompt: str, item_schema: Type[T], system: str
) -> list[T]:
    # Wrap in a list model
    class ListWrapper(BaseModel):
        items: list[item_schema]  # type: ignore[valid-type]

    result = _openai_structured(prompt, ListWrapper, system)
    return result.items


def _clean_schema(schema: dict):
    schema.pop("$defs", None)
    schema.pop("title", None)
    for v in schema.get("properties", {}).values():
        if isinstance(v, dict):
            _clean_schema(v)
            if "items" in v and isinstance(v["items"], dict):
                _clean_schema(v["items"])

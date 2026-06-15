"""Unit tests for individual agent nodes."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_state(**overrides):
    base = {
        "messages": [{"role": "user", "content": "Hello"}],
        "user_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "conversation_id": str(uuid.uuid4()),
        "memory_context": "No prior context.",
        "tool_outputs": [],
        "final_response": "",
        "is_complete": False,
    }
    base.update(overrides)
    return base


def _make_chat_response(content=None, finish_reason="stop", tool_calls=None):
    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message.content = content
    choice.message.tool_calls = tool_calls
    choice.message.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls,
    }
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ─── router_node ────────────────────────────────────────────────────────────

class TestRouterNode:
    @pytest.mark.asyncio
    async def test_plain_text_response_sets_complete(self):
        state = _make_state()
        mock_resp = _make_chat_response(content="Here is your answer.", finish_reason="stop")

        with patch("app.agent.nodes.router_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.router_node import router_node
            result = await router_node(state)

        assert result["is_complete"] is True
        assert result["final_response"] == "Here is your answer."
        assert result["tool_outputs"] == []
        assert result["messages"][-1] == {"role": "assistant", "content": "Here is your answer."}

    @pytest.mark.asyncio
    async def test_tool_call_response_not_complete(self):
        state = _make_state()

        tc = MagicMock()
        tc.id = "call_abc123"
        tc.function.name = "list_emails"
        tc.function.arguments = json.dumps({"max_results": 5})

        mock_resp = _make_chat_response(finish_reason="tool_calls", tool_calls=[tc])

        with patch("app.agent.nodes.router_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.router_node import router_node
            result = await router_node(state)

        assert result["is_complete"] is False
        assert len(result["tool_outputs"]) == 1
        assert result["tool_outputs"][0]["name"] == "list_emails"
        assert result["tool_outputs"][0]["id"] == "call_abc123"
        assert result["tool_outputs"][0]["input"] == {"max_results": 5}

    @pytest.mark.asyncio
    async def test_memory_context_injected_into_system_prompt(self):
        state = _make_state(memory_context="User hates 9 AM meetings.")
        mock_resp = _make_chat_response(content="Done.", finish_reason="stop")

        captured_kwargs = {}

        async def fake_completion(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_resp

        with patch("app.agent.nodes.router_node.chat_completion", fake_completion):
            from app.agent.nodes.router_node import router_node
            await router_node(state)

        assert "User hates 9 AM meetings." in captured_kwargs.get("system", "")

    @pytest.mark.asyncio
    async def test_bad_request_retries_without_tools(self):
        from openai import BadRequestError

        state = _make_state()
        fallback_resp = _make_chat_response(content="Fallback answer.", finish_reason="stop")

        call_count = 0

        async def fake_completion(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise BadRequestError("bad format", response=MagicMock(status_code=400), body={})
            return fallback_resp

        with patch("app.agent.nodes.router_node.chat_completion", fake_completion):
            from app.agent.nodes.router_node import router_node
            result = await router_node(state)

        assert result["is_complete"] is True
        assert result["final_response"] == "Fallback answer."
        assert call_count == 2


# ─── executor_node ──────────────────────────────────────────────────────────

class TestExecutorNode:
    def _runtime_ctx(self, gmail=None, gcal=None, mem=None):
        return {
            "gmail_client": gmail,
            "calendar_client": gcal,
            "memory_manager": mem or AsyncMock(),
        }

    @pytest.mark.asyncio
    async def test_list_emails_no_gmail_returns_message(self):
        state = _make_state(
            tool_outputs=[{"id": "c1", "name": "list_emails", "input": {"max_results": 5}}]
        )
        ctx = self._runtime_ctx()

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        tool_msg = result["messages"][-1]
        assert tool_msg["role"] == "tool"
        assert "not connected" in tool_msg["content"].lower()
        assert result["tool_outputs"] == []

    @pytest.mark.asyncio
    async def test_list_emails_with_gmail(self):
        gmail = MagicMock()
        gmail.list_messages.return_value = {
            "emails": [{"id": "e1", "subject": "Hello", "snippet": "Hi there", "body": "Hi"}]
        }
        state = _make_state(
            tool_outputs=[{"id": "c1", "name": "list_emails", "input": {"max_results": 5}}]
        )
        ctx = self._runtime_ctx(gmail=gmail)

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        tool_msg = result["messages"][-1]
        assert tool_msg["role"] == "tool"
        parsed = json.loads(tool_msg["content"])
        assert len(parsed) == 1
        assert parsed[0]["subject"] == "Hello"

    @pytest.mark.asyncio
    async def test_send_email_stores_style_memory(self):
        gmail = MagicMock()
        gmail.send_message.return_value = None
        mem = AsyncMock()
        mem.store_style = AsyncMock()

        state = _make_state(
            tool_outputs=[{
                "id": "c2",
                "name": "send_email",
                "input": {"to": "boss@co.com", "subject": "Update", "body": "All good."},
            }]
        )
        ctx = self._runtime_ctx(gmail=gmail, mem=mem)

        from app.agent.nodes.executor_node import executor_node
        await executor_node(state, runtime_ctx=ctx)

        mem.store_style.assert_called_once()
        call_arg = mem.store_style.call_args[0][0]
        assert "boss@co.com" in call_arg

    @pytest.mark.asyncio
    async def test_search_memory_tool(self):
        mem = AsyncMock()
        ctx_result = MagicMock()
        ctx_result.to_prompt_block.return_value = "User prefers async comms."
        mem.retrieve = AsyncMock(return_value=ctx_result)

        state = _make_state(
            tool_outputs=[{"id": "c3", "name": "search_memory", "input": {"query": "preferences"}}]
        )
        ctx = self._runtime_ctx(mem=mem)

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        tool_msg = result["messages"][-1]
        assert "User prefers async comms." in tool_msg["content"]

    @pytest.mark.asyncio
    async def test_store_memory_tool(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()

        state = _make_state(
            tool_outputs=[{
                "id": "c4",
                "name": "store_memory",
                "input": {"content": "User is vegetarian", "importance": 0.9},
            }]
        )
        ctx = self._runtime_ctx(mem=mem)

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        mem.store_fact.assert_called_once_with("User is vegetarian", importance=0.9)
        assert "Memory stored." in result["messages"][-1]["content"]

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_message(self):
        state = _make_state(
            tool_outputs=[{"id": "c5", "name": "fly_rocket", "input": {}}]
        )
        ctx = self._runtime_ctx()

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        tool_msg = result["messages"][-1]
        assert "Unknown tool" in tool_msg["content"]

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_all_appended(self):
        gmail = MagicMock()
        gmail.list_messages.return_value = {"emails": []}
        mem = AsyncMock()
        ctx_result = MagicMock()
        ctx_result.to_prompt_block.return_value = ""
        mem.retrieve = AsyncMock(return_value=ctx_result)

        state = _make_state(
            tool_outputs=[
                {"id": "c1", "name": "list_emails", "input": {}},
                {"id": "c2", "name": "search_memory", "input": {"query": "test"}},
            ]
        )
        ctx = self._runtime_ctx(gmail=gmail, mem=mem)

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
        assert len(tool_messages) == 2
        ids = [m["tool_call_id"] for m in tool_messages]
        assert "c1" in ids
        assert "c2" in ids

    @pytest.mark.asyncio
    async def test_list_calendar_events_no_gcal(self):
        state = _make_state(
            tool_outputs=[{
                "id": "c6",
                "name": "list_calendar_events",
                "input": {"days_ahead": 7},
            }]
        )
        ctx = self._runtime_ctx()

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        assert "not connected" in result["messages"][-1]["content"].lower()

    @pytest.mark.asyncio
    async def test_draft_email_stores_style(self):
        gmail = MagicMock()
        gmail.draft_message.return_value = {"id": "draft_123"}
        mem = AsyncMock()
        mem.store_style = AsyncMock()

        state = _make_state(
            tool_outputs=[{
                "id": "c7",
                "name": "draft_email",
                "input": {"to": "ceo@co.com", "subject": "Q3 Report", "body": "Please review."},
            }]
        )
        ctx = self._runtime_ctx(gmail=gmail, mem=mem)

        from app.agent.nodes.executor_node import executor_node
        result = await executor_node(state, runtime_ctx=ctx)

        mem.store_style.assert_called_once()
        assert "draft_123" in result["messages"][-1]["content"]


# ─── memory_writer_node ─────────────────────────────────────────────────────

class TestMemoryWriterNode:
    def _runtime_ctx(self, mem):
        return {"memory_manager": mem}

    @pytest.mark.asyncio
    async def test_extracts_facts_and_stores(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()
        mem.store_style = AsyncMock()
        mem.upsert_graph = AsyncMock()

        extracted = {"facts": ["User works at Acme Corp"], "preferences": [], "style_patterns": [], "relations": []}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(extracted)

        state = _make_state(
            messages=[
                {"role": "user", "content": "I work at Acme Corp."},
                {"role": "assistant", "content": "Got it!"},
            ]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            result = await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.store_fact.assert_called_once_with("User works at Acme Corp", source="chat", importance=0.7)
        assert result is state

    @pytest.mark.asyncio
    async def test_extracts_preferences_with_higher_importance(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()
        mem.store_style = AsyncMock()

        extracted = {"facts": [], "preferences": ["Prefers email over Slack"], "style_patterns": [], "relations": []}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(extracted)

        state = _make_state(
            messages=[{"role": "user", "content": "I prefer email."}]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.store_fact.assert_called_once_with("Prefers email over Slack", source="chat", importance=0.85)

    @pytest.mark.asyncio
    async def test_stores_style_patterns(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()
        mem.store_style = AsyncMock()

        extracted = {"facts": [], "preferences": [], "style_patterns": ["Writes concise emails"], "relations": []}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(extracted)

        state = _make_state(
            messages=[{"role": "user", "content": "I like short emails."}]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.store_style.assert_called_once_with("Writes concise emails", source="chat")

    @pytest.mark.asyncio
    async def test_upserts_entity_relations(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()
        mem.store_style = AsyncMock()
        mem.upsert_graph = AsyncMock()

        relation = {
            "from": "Alice",
            "from_type": "person",
            "relation": "works_at",
            "to": "Acme Corp",
            "to_type": "organization",
        }
        extracted = {"facts": [], "preferences": [], "style_patterns": [], "relations": [relation]}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = json.dumps(extracted)

        state = _make_state(
            messages=[{"role": "user", "content": "Alice works at Acme Corp."}]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.upsert_graph.assert_called_once_with(
            from_entity="Alice",
            from_type="person",
            relation="works_at",
            to_entity="Acme Corp",
            to_type="organization",
        )

    @pytest.mark.asyncio
    async def test_handles_llm_failure_gracefully(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()

        state = _make_state(
            messages=[{"role": "user", "content": "Some input."}]
        )

        with patch(
            "app.agent.nodes.memory_writer_node.chat_completion",
            AsyncMock(side_effect=Exception("LLM timeout")),
        ):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            result = await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.store_fact.assert_not_called()
        assert result is state

    @pytest.mark.asyncio
    async def test_handles_json_parse_failure_gracefully(self):
        mem = AsyncMock()

        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "not valid json at all"

        state = _make_state(
            messages=[{"role": "user", "content": "Test."}]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            result = await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        assert result is state

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self):
        mem = AsyncMock()
        mem.store_fact = AsyncMock()
        mem.store_style = AsyncMock()

        extracted = {"facts": ["User is a developer"], "preferences": [], "style_patterns": [], "relations": []}
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = f"```json\n{json.dumps(extracted)}\n```"

        state = _make_state(
            messages=[{"role": "user", "content": "I'm a dev."}]
        )

        with patch("app.agent.nodes.memory_writer_node.chat_completion", AsyncMock(return_value=mock_resp)):
            from app.agent.nodes.memory_writer_node import memory_writer_node
            await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        mem.store_fact.assert_called_once_with("User is a developer", source="chat", importance=0.7)

    @pytest.mark.asyncio
    async def test_empty_messages_returns_state_unchanged(self):
        mem = AsyncMock()
        state = _make_state(messages=[])

        from app.agent.nodes.memory_writer_node import memory_writer_node
        result = await memory_writer_node(state, runtime_ctx=self._runtime_ctx(mem))

        assert result is state
        mem.store_fact.assert_not_called()


# ─── graph edge logic ────────────────────────────────────────────────────────

class TestGraphEdgeLogic:
    def test_should_continue_routes_to_memory_writer_when_complete(self):
        from app.agent.graph import _should_continue
        state = _make_state(is_complete=True, tool_outputs=[])
        assert _should_continue(state) == "memory_writer"

    def test_should_continue_routes_to_executor_when_tools_pending(self):
        from app.agent.graph import _should_continue
        state = _make_state(is_complete=False, tool_outputs=[{"id": "x", "name": "list_emails", "input": {}}])
        assert _should_continue(state) == "executor"

    def test_should_continue_routes_to_memory_writer_when_no_tools(self):
        from app.agent.graph import _should_continue
        state = _make_state(is_complete=False, tool_outputs=[])
        assert _should_continue(state) == "memory_writer"

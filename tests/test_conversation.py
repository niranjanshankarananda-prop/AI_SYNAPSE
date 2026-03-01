"""Tests for core/conversation.py — token estimation, messages, compaction."""

import pytest

from core.conversation import Conversation, Message


# ── Message ───────────────────────────────────────────────────────────

class TestMessage:
    def test_to_dict_basic(self):
        msg = Message(role="user", content="hello")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "hello"

    def test_to_dict_tool_message(self):
        msg = Message(
            role="tool",
            content="result",
            metadata={"tool_call_id": "abc", "name": "read"}
        )
        d = msg.to_dict()
        assert d["tool_call_id"] == "abc"
        assert d["name"] == "read"

    def test_to_dict_assistant_with_tool_calls(self):
        tc = [{"id": "1", "type": "function", "function": {"name": "read", "arguments": "{}"}}]
        msg = Message(role="assistant", content="", metadata={"tool_calls": tc})
        d = msg.to_dict()
        assert d["tool_calls"] == tc
        assert d["content"] is None  # empty content becomes None

    def test_timestamp_auto_set(self):
        msg = Message(role="user", content="hi")
        assert msg.timestamp is not None


# ── Conversation ──────────────────────────────────────────────────────

class TestConversation:
    def test_add_message(self):
        conv = Conversation()
        msg = conv.add_message("user", "hello")
        assert msg.role == "user"
        assert len(conv.messages) == 1

    def test_get_messages_for_api(self):
        conv = Conversation()
        conv.add_message("user", "hello")
        conv.add_message("assistant", "hi there")
        msgs = conv.get_messages_for_api()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["content"] == "hi there"

    def test_token_estimation(self):
        conv = Conversation()
        # 4 chars per token, "hello world" = 11 chars ≈ 2 tokens
        conv.add_message("user", "hello world")
        assert conv.total_tokens == 11 // conv.CHARS_PER_TOKEN

    def test_context_usage(self):
        conv = Conversation(max_tokens=100, system_prompt="")
        conv.add_message("user", "a" * 400)  # 400 chars = 100 tokens
        assert conv.get_context_usage() == pytest.approx(1.0)

    def test_remaining_tokens(self):
        conv = Conversation(max_tokens=1000, system_prompt="")
        conv.add_message("user", "a" * 400)  # 100 tokens
        assert conv.get_remaining_tokens() == 900

    def test_compact_reduces_messages(self):
        conv = Conversation()
        for i in range(20):
            conv.add_message("user", f"message {i}")
        assert len(conv.messages) == 20

        conv.compact(keep_recent=5)
        # 1 summary + 5 recent
        assert len(conv.messages) == 6
        assert conv.messages[0].role == "system"

    def test_compact_noop_when_few_messages(self):
        conv = Conversation()
        conv.add_message("user", "hello")
        result = conv.compact(keep_recent=10)
        assert "No compaction" in result

    def test_clear(self):
        conv = Conversation()
        conv.add_message("user", "hello")
        conv.clear()
        assert len(conv.messages) == 0
        assert conv.total_tokens == 0

    def test_save_and_load(self, tmp_path):
        conv = Conversation(system_prompt="You are helpful")
        conv.add_message("user", "hello")
        conv.add_message("assistant", "hi")

        path = tmp_path / "conv.json"
        assert conv.save(path) is True

        conv2 = Conversation()
        assert conv2.load(path) is True
        assert len(conv2.messages) == 2
        assert conv2.system_prompt == "You are helpful"

    def test_get_stats(self):
        conv = Conversation(max_tokens=10000)
        conv.add_message("user", "hello")
        conv.add_message("assistant", "world")
        stats = conv.get_stats()
        assert stats["message_count"] == 2
        assert stats["user_messages"] == 1
        assert stats["assistant_messages"] == 1

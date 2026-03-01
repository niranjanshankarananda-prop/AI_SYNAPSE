"""Tests for core/tools.py — ReadTool, WriteTool, GlobTool, GrepTool."""

from pathlib import Path

import pytest

from core.tools import ReadTool, WriteTool, EditTool, GlobTool, GrepTool, BashTool, ToolRegistry


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir(tmp_path):
    """Create a temp directory with a few files for testing."""
    (tmp_path / "hello.txt").write_text("line1\nline2\nline3\nline4\nline5\n")
    (tmp_path / "data.py").write_text("import os\nprint('hello')\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested content\n")
    return tmp_path


# ── ReadTool ──────────────────────────────────────────────────────────

class TestReadTool:
    def setup_method(self):
        self.tool = ReadTool()

    def test_read_full_file(self, tmp_dir):
        result = self.tool.execute(str(tmp_dir / "hello.txt"))
        assert "line1" in result
        assert "line5" in result

    def test_read_with_offset_and_limit(self, tmp_dir):
        result = self.tool.execute(str(tmp_dir / "hello.txt"), offset=2, limit=2)
        assert "line2" in result
        assert "line3" in result
        assert "line1" not in result
        assert "line4" not in result

    def test_read_nonexistent_file(self):
        result = self.tool.execute("/tmp/nonexistent_file_xyz.txt")
        assert "Error" in result

    def test_read_directory_returns_error(self, tmp_dir):
        result = self.tool.execute(str(tmp_dir))
        assert "Error" in result

    def test_schema_has_required_fields(self):
        schema = self.tool.get_schema()
        assert schema["name"] == "read"
        assert "file_path" in schema["parameters"]["required"]


# ── WriteTool ─────────────────────────────────────────────────────────

class TestWriteTool:
    def setup_method(self):
        self.tool = WriteTool()

    def test_write_new_file(self, tmp_dir):
        path = str(tmp_dir / "new.txt")
        result = self.tool.execute(path, "hello world")
        assert "Successfully" in result
        assert Path(path).read_text() == "hello world"

    def test_write_creates_parent_dirs(self, tmp_dir):
        path = str(tmp_dir / "a" / "b" / "c.txt")
        result = self.tool.execute(path, "deep")
        assert "Successfully" in result
        assert Path(path).read_text() == "deep"

    def test_overwrite_existing_file(self, tmp_dir):
        path = str(tmp_dir / "hello.txt")
        self.tool.execute(path, "overwritten")
        assert Path(path).read_text() == "overwritten"


# ── EditTool ──────────────────────────────────────────────────────────

class TestEditTool:
    def setup_method(self):
        self.tool = EditTool()

    def test_replace_text(self, tmp_dir):
        path = str(tmp_dir / "hello.txt")
        result = self.tool.execute(path, "line2", "LINE_TWO")
        assert "Successfully" in result
        assert "LINE_TWO" in Path(path).read_text()

    def test_replace_missing_text(self, tmp_dir):
        path = str(tmp_dir / "hello.txt")
        result = self.tool.execute(path, "nonexistent", "replacement")
        assert "Error" in result


# ── GlobTool ──────────────────────────────────────────────────────────

class TestGlobTool:
    def setup_method(self):
        self.tool = GlobTool()

    def test_find_txt_files(self, tmp_dir):
        result = self.tool.execute("*.txt", str(tmp_dir))
        assert "hello.txt" in result
        assert "nested.txt" in result

    def test_find_py_files(self, tmp_dir):
        result = self.tool.execute("*.py", str(tmp_dir))
        assert "data.py" in result

    def test_no_matches(self, tmp_dir):
        result = self.tool.execute("*.xyz", str(tmp_dir))
        assert "No files found" in result


# ── GrepTool ──────────────────────────────────────────────────────────

class TestGrepTool:
    def setup_method(self):
        self.tool = GrepTool()

    def test_find_pattern(self, tmp_dir):
        result = self.tool.execute("import", str(tmp_dir))
        assert "data.py" in result or "import" in result

    def test_no_matches(self, tmp_dir):
        result = self.tool.execute("zzzznotfound", str(tmp_dir))
        assert "No matches" in result.lower() or "no matches" in result.lower()


# ── BashTool ──────────────────────────────────────────────────────────

class TestBashTool:
    def setup_method(self):
        self.tool = BashTool()

    def test_safe_command(self):
        result = self.tool.execute("echo hello", confirmed=True)
        assert "hello" in result

    def test_dangerous_command_blocked(self):
        result = self.tool.execute("rm -rf /tmp/test")
        assert "PERMISSION_REQUIRED" in result

    def test_dangerous_command_confirmed(self, tmp_dir):
        path = str(tmp_dir / "to_delete.txt")
        Path(path).write_text("bye")
        result = self.tool.execute(f"rm {path}", confirmed=True)
        assert not Path(path).exists()


# ── ToolRegistry ──────────────────────────────────────────────────────

class TestToolRegistry:
    def test_default_tools_registered(self):
        registry = ToolRegistry()
        names = registry.list_tools()
        assert "read" in names
        assert "write" in names
        assert "bash" in names
        assert "glob" in names
        assert "grep" in names
        assert "edit" in names

    def test_get_openai_tools_format(self):
        registry = ToolRegistry()
        tools = registry.get_openai_tools()
        assert len(tools) >= 6
        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]

    def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = registry.execute("nonexistent")
        assert "Error" in result

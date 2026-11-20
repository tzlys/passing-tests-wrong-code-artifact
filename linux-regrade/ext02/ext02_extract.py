"""EXT-02 per-format action extractors.

Written from the Stage 0 structure output only, which shows key paths and types
with content masked. Committed before Stage 1.

extract(entry, key, raw) returns a list of agent-issued shell command strings,
in order, or None when the file exposes no agent shell actions.

Formats seen in Stage 0:
- SWE-agent .traj (2024 and 2025 entries): $.trajectory[].action (str).
  - Special editor commands (edit, create, open, str_replace_editor, ...) are not
    shell commands and are dropped. Their bodies are file content.
- OpenDevin CodeAct v1.8 .traj: $.traj[][0] is the action dict. We take only
  action == "run" and its args.command. IPython cells are not shell.
- OpenHands CodeAct 2.1 .json: a list of LLM messages. We take assistant
  tool_calls named execute_bash (arguments.command), plus the text forms
  <function=execute_bash><parameter=command>…</parameter> and
  <execute_bash>…</execute_bash>.
- Moatless, AppMap Navie (both entries), CodeFuse-CGM and SWE-Fixer: no
  agent-issued shell. They use search, edit or LLM pipelines, so the extractor
  returns None.

In every format, heredoc bodies (<<EOF … EOF) are file content, not commands, and
are removed before the fixed metrics run.
"""
import json
import re

SWEAGENT_NONSHELL = {
    "edit", "create", "open", "goto", "scroll_up", "scroll_down", "search_dir", "search_file",
    "find_file", "submit", "str_replace_editor", "insert", "append", "view", "undo_edit", "exit_forfeit",
    "exit_cost", "exit_context", "exit_error", "exit_format", "skip",
}
NO_SHELL_ENTRIES = ("moatless", "appmap-navie", "navie-2", "codefuse-cgm", "SWE-Fixer")
HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")


def strip_heredocs(cmd):
    out, lines, i = [], cmd.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            delim = m.group(1)
            i += 1
            while i < len(lines) and lines[i].strip() != delim:
                i += 1
        i += 1
    return "\n".join(out)


def _first_word(s):
    s = s.strip()
    return s.split(None, 1)[0] if s else ""


def _sweagent(obj):
    traj = obj.get("trajectory")
    if not isinstance(traj, list):
        return None
    out = []
    for step in traj:
        if isinstance(step, dict) and isinstance(step.get("action"), str):
            a = step["action"]
            if _first_word(a) in SWEAGENT_NONSHELL:
                continue
            out.append(strip_heredocs(a))
    return out


def _opendevin(obj):
    traj = obj.get("traj")
    if not isinstance(traj, list):
        return None
    out = []
    for pair in traj:
        act = pair[0] if isinstance(pair, list) and pair else pair
        if isinstance(act, dict) and act.get("action") == "run":
            cmd = (act.get("args") or {}).get("command")
            if isinstance(cmd, str):
                out.append(strip_heredocs(cmd))
    return out


TEXT_FN = re.compile(r"<function=execute_bash>\s*<parameter=command>(.*?)</parameter>", re.S)
TEXT_TAG = re.compile(r"<execute_bash>(.*?)</execute_bash>", re.S)


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and isinstance(c.get("text"), str))
    return ""


def _openhands(msgs):
    out = []
    for m in msgs:
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            fn = (tc or {}).get("function") or {}
            if fn.get("name") in ("execute_bash", "bash", "execute_command"):
                args = fn.get("arguments")
                try:
                    args = json.loads(args) if isinstance(args, str) else (args or {})
                except Exception:
                    continue
                cmd = args.get("command")
                if isinstance(cmd, str):
                    out.append(strip_heredocs(cmd))
        text = _text_of(m.get("content"))
        for rx in (TEXT_FN, TEXT_TAG):
            for cmd in rx.findall(text):
                out.append(strip_heredocs(cmd.strip()))
    return out


def extract(entry, key, raw):
    if any(s in entry for s in NO_SHELL_ENTRIES):
        return None
    if not (key.endswith(".traj") or key.endswith(".json")):
        return None
    obj = json.loads(raw.decode("utf-8", "replace"))
    if isinstance(obj, dict) and "trajectory" in obj:
        return _sweagent(obj)
    if isinstance(obj, dict) and "traj" in obj:
        return _opendevin(obj)
    if isinstance(obj, list):
        return _openhands(obj)
    return None


if __name__ == "__main__":
    # synthetic self-tests (no trajectory data)
    swe = {"trajectory": [{"action": "create reproduce.py"},
                          {"action": "edit 1:1\nimport pytest\npytest.main()\nend_of_edit"},
                          {"action": "python -m pytest tests/x.py | tail"},
                          {"action": "cat > t.py <<'EOF'\npytest.raises(X)\nmore\nEOF\npython t.py"}]}
    a = extract("20240402_sweagent_gpt4", "lite/e/trajs/i.traj", json.dumps(swe).encode())
    assert a == ["python -m pytest tests/x.py | tail", "cat > t.py <<'EOF'\npython t.py"], a
    od = {"traj": [[{"action": "message", "args": {}}, {}], [{"action": "run", "args": {"command": "pytest -q &"}}, {}],
                   [{"action": "run_ipython", "args": {"code": "!pytest"}}, {}]]}
    assert extract("20240725_opendevin_x", "k.traj", json.dumps(od).encode()) == ["pytest -q &"]
    oh = [{"role": "system", "content": [{"type": "text", "text": "x"}]},
          {"role": "assistant", "content": [{"type": "text", "text": "run"}],
           "tool_calls": [{"function": {"name": "execute_bash", "arguments": json.dumps({"command": "pip install ."})}},
                          {"function": {"name": "str_replace_editor", "arguments": "{}"}}]},
          {"role": "assistant", "content": "<function=execute_bash>\n<parameter=command>pytest x; ls</parameter>\n</function>"}]
    assert extract("20241025_OpenHands-x", "k.json", json.dumps(oh).encode()) == ["pip install .", "pytest x; ls"]
    assert extract("20240617_moatless_gpt4o", "k.json", b"{}") is None
    assert extract("20250226_sweagent_x", "k.config.yaml", b"x") is None
    print("extract self-tests pass")

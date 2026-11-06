"""Pure serving-layer logic in b3.py: answer extraction, budget/window math,
sampling-arm construction. No network, no containers."""

import pytest

import b3


# ------------------------------------------------------------------ extraction
class TestStripThink:
    def test_removes_closed_trace(self):
        assert b3.strip_think("<think>waffling</think>answer") == "answer"

    def test_removes_unclosed_trace(self):
        # An unclosed <think> means the cap landed mid-thought: everything
        # after it is deliberation and must never be graded as the answer.
        assert b3.strip_think("answer\n<think>\nmore thinking") == "answer\n"

    def test_plain_text_untouched(self):
        assert b3.strip_think("just an answer") == "just an answer"

    def test_multiple_traces(self):
        assert b3.strip_think("a<think>xb<think>yc") == "a"


class TestCodeOf:
    def test_fenced_block_extracted(self):
        assert b3.code_of("```python\nx = 1\n```") == "x = 1\n"

    def test_bare_fence(self):
        assert b3.code_of("```\nsay hi\n```") == "say hi\n"

    def test_no_fence_returns_text_after_think_strip(self):
        assert b3.code_of("<think>hmm</think>no fence here") == "no fence here"

    def test_first_fence_wins(self):
        out = b3.code_of("```py\nfirst\n```\nprose\n```py\nsecond\n```")
        assert out == "first\n"


class TestCmdOf:
    def test_skips_comment_and_dollar_lines(self):
        assert b3.cmd_of("# note\n$ export X=1\nls -la") == "ls -la"

    def test_fence_wins(self):
        assert b3.cmd_of("```sh\ngit status\n```") == "git status"

    def test_empty_when_only_comments(self):
        assert b3.cmd_of("# nothing here") == ""

    def test_first_command_line_wins(self):
        assert b3.cmd_of("echo one\necho two") == "echo one"


class TestAfterMark:
    def test_text_after_marker(self):
        assert b3.after_mark("reasoning here\nANSWER: the code") == " the code"

    def test_last_marker_wins(self):
        assert b3.after_mark("ANSWER: wrong\nmore\nANSWER: right") == " right"

    def test_no_marker_returns_input(self):
        assert b3.after_mark("no marker at all") == "no marker at all"


# ---------------------------------------------------------------- model routing
class TestCanThink:
    @pytest.mark.parametrize(
        "model", ["gemma-4-26b", "Gemma-4", "Qwen3.5-9B", "qwen3.5-27b-fp8"]
    )
    def test_known_thinkers(self, model):
        assert b3.can_think(model)

    def test_case_insensitive_substring(self):
        assert b3.can_think("served-as-X-QWEN3.5-instruct")

    @pytest.mark.parametrize("model", ["llama-3.3-70b", "mellum2", "qwen2.5-coder"])
    def test_non_thinkers(self, model):
        assert not b3.can_think(model)


class TestProfileFor:
    def test_substring_match_case_insensitive(self, monkeypatch):
        monkeypatch.setattr(
            b3, "PROFILES", {"Qwen3.5": {"temperature": 1.0, "top_k": 40}}
        )
        assert b3.profile_for("qwen3.5-9b-mlx") == {"temperature": 1.0, "top_k": 40}

    def test_default_when_no_match(self, monkeypatch):
        monkeypatch.setattr(b3, "PROFILES", {"other": {"temperature": 0.5}})
        assert b3.profile_for("unlisted-model") == b3.DEFAULT_SAMP


class TestSampling:
    def _base(self, monkeypatch, off_mech, think, effort=""):
        monkeypatch.setattr(b3, "PROFILES", {})
        monkeypatch.setattr(b3, "OFF_MECH", off_mech)
        monkeypatch.setattr(b3, "THINK", think)
        monkeypatch.setattr(b3, "THINK_EFFORT", effort)

    def test_thinker_template_arm_on(self, monkeypatch):
        self._base(monkeypatch, "template", True)
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert p["chat_template_kwargs"] == {"enable_thinking": True}

    def test_thinker_template_arm_off(self, monkeypatch):
        self._base(monkeypatch, "template", False)
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert p["chat_template_kwargs"] == {"enable_thinking": False}

    def test_tmpl_extras_merged_and_popped(self, monkeypatch):
        monkeypatch.setattr(
            b3, "PROFILES", {"qwen3.5": {"_tmpl": {"add_vision": "auto"}}}
        )
        monkeypatch.setattr(b3, "OFF_MECH", "template")
        monkeypatch.setattr(b3, "THINK", True)
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert p["chat_template_kwargs"] == {
            "enable_thinking": True,
            "add_vision": "auto",
        }
        assert "_tmpl" not in p

    def test_reasoning_effort_off_arm_says_none(self, monkeypatch):
        self._base(monkeypatch, "reasoning_effort", False)
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert p["reasoning_effort"] == "none"
        assert "chat_template_kwargs" not in p

    def test_reasoning_effort_on_arm_sends_nothing(self, monkeypatch):
        self._base(monkeypatch, "reasoning_effort", True)
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert "reasoning_effort" not in p

    def test_reasoning_effort_explicit_effort_on_arm(self, monkeypatch):
        self._base(monkeypatch, "reasoning_effort", True, effort="medium")
        p = b3.sampling({"model": "qwen3.5"}, "qwen3.5")
        assert p["reasoning_effort"] == "medium"

    def test_non_thinker_gets_no_reasoning_fields(self, monkeypatch):
        self._base(monkeypatch, "template", True)
        p = b3.sampling({"model": "llama"}, "llama")
        assert "chat_template_kwargs" not in p
        assert "reasoning_effort" not in p

    def test_profile_fields_applied(self, monkeypatch):
        monkeypatch.setattr(
            b3, "PROFILES", {"llama": {"temperature": 0.7, "top_k": 20}}
        )
        p = b3.sampling({"model": "llama-3"}, "llama-3")
        assert p["temperature"] == 0.7 and p["top_k"] == 20


class TestWithCot:
    def test_appends_for_non_thinker_when_cot_on(self, monkeypatch):
        monkeypatch.setattr(b3, "COT", True)
        out = b3.with_cot("llama", "task")
        assert out.startswith("task") and b3.COT_MARK in out

    def test_untouched_for_thinker(self, monkeypatch):
        monkeypatch.setattr(b3, "COT", True)
        assert b3.with_cot("qwen3.5", "task") == "task"

    def test_untouched_when_cot_off(self, monkeypatch):
        monkeypatch.setattr(b3, "COT", False)
        assert b3.with_cot("llama", "task") == "task"


# ---------------------------------------------------------------------- budgets
class TestBudget:
    def test_default_is_identity(self, monkeypatch):
        monkeypatch.setattr(b3, "THINK", False)
        monkeypatch.setattr(b3, "BUDGET_MULT", 1.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 0)
        assert b3.budget(900) == 900

    def test_multiplier_applies_on_both_arms(self, monkeypatch):
        monkeypatch.setattr(b3, "BUDGET_MULT", 2.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 0)
        monkeypatch.setattr(b3, "THINK", False)
        assert b3.budget(900) == 1800
        monkeypatch.setattr(b3, "THINK", True)
        assert b3.budget(900) == 1800

    def test_floor_only_on_thinking_arm(self, monkeypatch):
        monkeypatch.setattr(b3, "BUDGET_MULT", 1.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 8000)
        monkeypatch.setattr(b3, "THINK", False)
        assert b3.budget(900) == 900
        monkeypatch.setattr(b3, "THINK", True)
        assert b3.budget(900) == 8000


class TestFit:
    def test_no_window_means_no_clamp(self, monkeypatch):
        monkeypatch.setattr(b3, "WINDOW", 0)
        monkeypatch.setattr(b3, "CLAMPED", [])
        assert b3.fit("x" * 100000, 900) == 900

    def test_roomy_window_no_clamp(self, monkeypatch):
        monkeypatch.setattr(b3, "WINDOW", 131072)
        monkeypatch.setattr(b3, "WINDOW_RESERVE", 512)
        monkeypatch.setattr(b3, "BUDGET_MULT", 1.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 0)
        monkeypatch.setattr(b3, "THINK", False)
        monkeypatch.setattr(b3, "CLAMPED", [])
        assert b3.fit("short prompt", 900) == 900
        assert b3.CLAMPED == []

    def test_clamp_records_shortfall(self, monkeypatch):
        monkeypatch.setattr(b3, "WINDOW", 4096)
        monkeypatch.setattr(b3, "WINDOW_RESERVE", 512)
        monkeypatch.setattr(b3, "BUDGET_MULT", 1.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 0)
        monkeypatch.setattr(b3, "THINK", False)
        monkeypatch.setattr(b3, "CLAMPED", [])
        prompt = "x" * 6000  # ~2000 tokens by the chars/3 estimate
        got = b3.fit(prompt, 3000)
        assert got == 4096 - 2000 - 512
        assert b3.CLAMPED == [got]

    def test_clamp_floor_is_1024(self, monkeypatch):
        monkeypatch.setattr(b3, "WINDOW", 4096)
        monkeypatch.setattr(b3, "WINDOW_RESERVE", 512)
        monkeypatch.setattr(b3, "BUDGET_MULT", 1.0)
        monkeypatch.setattr(b3, "BUDGET_FLOOR", 0)
        monkeypatch.setattr(b3, "THINK", False)
        monkeypatch.setattr(b3, "CLAMPED", [])
        assert b3.fit("x" * 30000, 3000) == 1024


# ------------------------------------------------------------- retry bookkeeping
class TestRetryConstants:
    def test_escalate_parsed_hotter_last(self):
        assert b3.ESCALATE == sorted(b3.ESCALATE)
        assert all(0.0 < t <= 2.0 for t in b3.ESCALATE)
        assert len(b3.ESCALATE) >= 1

    def test_retries_nonneg_int(self):
        assert isinstance(b3.RETRIES, int) and b3.RETRIES >= 0

    def test_completions_url_derived(self):
        assert b3.COMPLETIONS_URL == b3.URL.replace("/chat/completions", "/completions")

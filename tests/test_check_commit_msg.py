"""scripts/check_commit_msg.py 的單元測試。

覆蓋：中文 / 純英文 / prefix 解析 / 超長 subject / git trailer / 機械訊息 skip。
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_commit_msg.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_ccmsg", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_ccmsg"] = m
    spec.loader.exec_module(m)
    return m


# --- 中文偵測 -------------------------------------------------------------

@pytest.mark.parametrize("ch,expect", [
    ("中", True),
    ("文", True),
    ("a", False),
    ("1", False),
    ("，", False),   # 全形標點不算 CJK 字元
])
def test_is_cjk(mod, ch, expect):
    assert mod._is_cjk(ch) is expect


# --- 中文 commit：OK -----------------------------------------------------

def test_zh_subject_passes(mod):
    r = mod.check("M2: 新增 RateLimitedSession 對 Retry-After 標頭的支援")
    assert r.ok
    assert r.warnings == []


def test_zh_subject_with_body_passes(mod):
    msg = (
        "fix: 修 webui POST `/api/labels` 在空 body 時 500 的 bug\n"
        "\n"
        "原因是 json.loads 收到空 bytes 會 raise；改在進來時先檢查 length。\n"
    )
    r = mod.check(msg)
    assert r.ok, r.warnings


# --- 純英文 commit：WARN --------------------------------------------------

def test_pure_english_subject_warns(mod):
    r = mod.check("M4: docs — link autogo test-plans + formatter in top README")
    assert not r.ok
    assert any("不含繁體中文" in w for w in r.warnings)


def test_single_cjk_char_allowed(mod):
    """只要主體有至少 1 個中文字就算合格（技術識別符保留原文是 spec 允許的）。"""
    r = mod.check("feat: 加 commit-msg lint")
    assert r.ok, r.warnings


# --- Prefix 解析（不算進長度上限）---------------------------------------

def test_prefix_excluded_from_length(mod):
    # prefix 8 字 + 主體 70 字（中文）— 主體沒超 72，OK
    long_zh = "啊" * 70
    r = mod.check(f"feat: {long_zh}")
    # 不應觸發長度警告（主體 70 ≤ 72）
    assert not any("過長" in w for w in r.warnings)


def test_subject_too_long_warns(mod):
    long_zh = "啊" * 80
    r = mod.check(f"feat: {long_zh}")
    assert any("過長" in w for w in r.warnings)


@pytest.mark.parametrize("prefix", [
    "M1:", "M21:", "M21a:", "feat:", "fix:", "FIX:", "refactor:",
    "chore:", "test:", "docs:", "BUILD:", "ci:",
])
def test_known_prefixes_parsed(mod, prefix):
    r = mod.check(f"{prefix} 補測試")
    # 應 OK（主體 3 個中文字 + 短）
    assert r.ok, (prefix, r.warnings)


# --- 機械訊息：SKIP -------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "Merge pull request #123 from feature/x",
    "Merge branch 'develop' into main",
    'Revert "feat: did a thing"',
    "Bump pypdf from 6.12.2 to 6.13.0",
    "chore(deps): bump foo from 1 to 2",
    "Update package-lock.json",
])
def test_auto_messages_skipped(mod, msg):
    r = mod.check(msg)
    assert r.skipped
    assert r.warnings == []


# --- Git trailer：不算 body 行寬 -----------------------------------------

def test_long_trailer_not_warned(mod):
    msg = (
        "M3: 加 commit-msg lint\n"
        "\n"
        "Co-Authored-By: Some Very Long Name With Lots Of Characters <noreply@xxxxxxxx.example.com>\n"
    )
    r = mod.check(msg)
    # trailer 那行很長但應被略過
    assert r.ok, r.warnings


# --- body 行寬：超寬會警告 -----------------------------------------------

def test_body_line_too_wide_warns(mod):
    body_line = "啊" * 60   # 60 中文字 × 2 = 視覺寬度 120
    msg = f"feat: 短 subject\n\n{body_line}\n"
    r = mod.check(msg)
    assert any("body 第" in w and "視覺寬度" in w for w in r.warnings)


# --- 空訊息 ---------------------------------------------------------------

def test_empty_message_warns(mod):
    r = mod.check("")
    assert not r.ok
    assert any("empty" in w.lower() for w in r.warnings)


# --- CLI integration ------------------------------------------------------

def test_cli_against_HEAD_returns_0_in_lint_mode():
    """預設 lint 模式：即使 warning 也 exit 0（避免擋住正當開發）。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "HEAD"],
        capture_output=True, text=True,
    )
    # 不應 exit 1（lint 模式）
    assert r.returncode == 0


def test_cli_strict_mode_returns_1_on_english_commit():
    """--strict 模式：英文 commit 應 exit 1。"""
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdin", "--strict"],
        input="feat: pure english commit subject\n",
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "不含繁體中文" in r.stderr


def test_cli_file_input(tmp_path):
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_text("M2: 中文 commit OK\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--file", str(f), "--strict"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

"""用 macOS 原生对话框(osascript / AppleScript)弹出可点选的菜单列表。"""

from __future__ import annotations

import subprocess
from typing import List, Optional

# 通过 argv 把标题和各列表项传给 AppleScript,避免把用户文本直接拼进脚本
# 带来的引号转义问题。argv 第 1 个是标题,其余是列表项。
_SCRIPT = """
on run argv
    set theTitle to item 1 of argv
    set theItems to rest of argv
    set chosen to choose from list theItems with title "AutoKey" with prompt theTitle without multiple selections allowed
    if chosen is false then
        return "__AUTOKEY_CANCELLED__"
    else
        return item 1 of chosen
    end if
end run
"""

_CANCELLED = "__AUTOKEY_CANCELLED__"


class MenuError(Exception):
    """弹出菜单时出错(如 osascript 不可用)。"""


def choose_from_menu(title: str, item_names: List[str]) -> Optional[str]:
    """弹出原生列表让用户选择,返回选中的项名;用户取消返回 None。"""
    try:
        result = subprocess.run(
            ["osascript", "-e", _SCRIPT, title, *item_names],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:  # 理论上 macOS 一定有 osascript
        raise MenuError("找不到 osascript,无法弹出菜单(本功能仅支持 macOS)。") from e

    if result.returncode != 0:
        raise MenuError(f"osascript 执行失败:{result.stderr.strip()}")

    chosen = result.stdout.strip()
    if chosen == _CANCELLED or not chosen:
        return None
    return chosen

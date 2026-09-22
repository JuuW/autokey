"""把配置里的动作序列翻译成 pynput 的按键操作。"""

from __future__ import annotations

import subprocess
import time
from typing import List, Optional

from pynput.keyboard import Controller, Key

# 键名字符串 → pynput 特殊键
KEY_MAP = {
    "tab": Key.tab,
    "enter": Key.enter,
    "return": Key.enter,
    "esc": Key.esc,
    "escape": Key.esc,
    "space": Key.space,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "page_up": Key.page_up,
    "page_down": Key.page_down,
}
for _n in range(1, 13):
    KEY_MAP[f"f{_n}"] = getattr(Key, f"f{_n}")


class ActionError(Exception):
    """执行动作时的错误(如未知键名)。"""


def _clipboard_get() -> Optional[str]:
    """读取当前剪贴板文本;失败返回 None(粘贴后无法恢复,但不影响本次输入)。"""
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, check=True
        )
        return result.stdout.decode("utf-8")
    except Exception:  # noqa: BLE001 - 读不到就当没有,后续不恢复
        return None


def _clipboard_set(text: str) -> None:
    """把文本写入剪贴板(pbcopy)。"""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def _paste_text(controller: Controller, text: str, restore_delay: float) -> None:
    """通过剪贴板 + Cmd+V 粘贴文本,避免逐字符输入受输入法影响。

    粘贴前备份剪贴板,粘贴完再恢复,尽量不打扰用户原有的剪贴板内容。
    """
    saved = _clipboard_get()
    _clipboard_set(text)
    # 等一下确保剪贴板写入完成,再发送粘贴快捷键
    time.sleep(restore_delay)
    with controller.pressed(Key.cmd):
        controller.press("v")
        controller.release("v")
    # 粘贴需要一点时间读取剪贴板,之后再恢复原内容
    time.sleep(restore_delay)
    if saved is not None:
        _clipboard_set(saved)


def _press_key(controller: Controller, name: str) -> None:
    key = KEY_MAP.get(name.lower())
    if key is None:
        raise ActionError(
            f"未知的键名 `{name}`。支持的键名:{', '.join(sorted(KEY_MAP))}"
        )
    controller.press(key)
    controller.release(key)


def execute_actions(
    controller: Controller, actions: List[dict], type_interval: float
) -> None:
    """依次执行一组动作(type 粘贴文本 / key 按特殊键)。

    type_interval 用作剪贴板写入/粘贴前后的短暂等待时间。
    """
    for action in actions:
        if "type" in action:
            _paste_text(controller, action["type"], type_interval)
        elif "key" in action:
            _press_key(controller, action["key"])

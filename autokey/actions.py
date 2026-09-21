"""把配置里的动作序列翻译成 pynput 的按键操作。"""

from __future__ import annotations

import time
from typing import List

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


def _type_text(controller: Controller, text: str, interval: float) -> None:
    for ch in text:
        controller.press(ch)
        controller.release(ch)
        if interval > 0:
            time.sleep(interval)


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
    """依次执行一组动作(type 输入文本 / key 按特殊键)。"""
    for action in actions:
        if "type" in action:
            _type_text(controller, action["type"], type_interval)
        elif "key" in action:
            _press_key(controller, action["key"])

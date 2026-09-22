"""加载并校验 AutoKey 的 YAML 配置。"""

from __future__ import annotations

import os

import yaml

DEFAULT_SETTINGS = {
    "type_interval": 0.1,
    "start_delay": 0.15,
}


class ConfigError(Exception):
    """配置文件格式错误,消息为面向用户的中文提示。"""


def load_config(path: str) -> dict:
    """读取并校验配置文件,返回补齐默认值后的配置字典。"""
    if not os.path.exists(path):
        raise ConfigError(
            f"找不到配置文件:{path}\n请先运行 `python -m autokey init-config` 生成。"
        )

    with open(path, "r", encoding="utf-8") as f:
        try:
            raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"配置文件不是合法的 YAML:{e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("配置文件内容为空或格式不对,顶层应是一个对象。")

    settings = {**DEFAULT_SETTINGS, **(raw.get("settings") or {})}

    hotkeys = raw.get("hotkeys") or []
    if not isinstance(hotkeys, list):
        raise ConfigError("`hotkeys` 必须是一个列表。")
    for i, hk in enumerate(hotkeys):
        _validate_hotkey(hk, i)

    menu = raw.get("menu")
    if menu is not None:
        _validate_menu(menu)

    if not hotkeys and menu is None:
        raise ConfigError("配置里 `hotkeys` 和 `menu` 都为空,至少需要其中一个作为触发入口。")

    return {"settings": settings, "hotkeys": hotkeys, "menu": menu}


def _validate_hotkey(hk: object, index: int) -> None:
    where = f"第 {index + 1} 组快捷键"
    if not isinstance(hk, dict):
        raise ConfigError(f"{where} 格式不对,应是一个对象。")

    combo = hk.get("combo")
    if not combo or not isinstance(combo, str):
        raise ConfigError(f"{where} 缺少 `combo`(组合键字符串)。")

    actions = hk.get("actions")
    if not isinstance(actions, list) or not actions:
        name = hk.get("name") or combo
        raise ConfigError(f"快捷键「{name}」的 `actions` 缺失或为空。")

    for j, action in enumerate(actions):
        _validate_action(action, hk.get("name") or combo, j)


def _validate_menu(menu: object) -> None:
    if not isinstance(menu, dict):
        raise ConfigError("`menu` 格式不对,应是一个对象(含 combo 和 items)。")

    combo = menu.get("combo")
    if not combo or not isinstance(combo, str):
        raise ConfigError("`menu` 缺少 `combo`(唤出菜单的组合键字符串)。")

    items = menu.get("items")
    if not isinstance(items, list) or not items:
        raise ConfigError("`menu` 的 `items` 缺失或为空,至少需要一个菜单项。")

    seen_names = set()
    for i, item in enumerate(items):
        where = f"menu 第 {i + 1} 个菜单项"
        if not isinstance(item, dict):
            raise ConfigError(f"{where} 格式不对,应是一个对象。")

        name = item.get("name")
        if not name or not isinstance(name, str):
            raise ConfigError(f"{where} 缺少 `name`(菜单里显示的文字)。")
        if name in seen_names:
            raise ConfigError(f"菜单项名称「{name}」重复,菜单里每个 `name` 必须唯一。")
        seen_names.add(name)

        actions = item.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ConfigError(f"菜单项「{name}」的 `actions` 缺失或为空。")
        for j, action in enumerate(actions):
            _validate_action(action, name, j)


def _validate_action(action: object, hotkey_name: str, index: int) -> None:
    where = f"快捷键「{hotkey_name}」的第 {index + 1} 个动作"
    if not isinstance(action, dict):
        raise ConfigError(f"{where} 格式不对,应是 `type: ...` 或 `key: ...`。")

    has_type = "type" in action
    has_key = "key" in action
    if has_type and has_key:
        raise ConfigError(f"{where} 同时写了 `type` 和 `key`,每个动作只能二选一。")
    if not has_type and not has_key:
        raise ConfigError(f"{where} 既没有 `type` 也没有 `key`,必须二选一。")

    if has_type and not isinstance(action["type"], str):
        raise ConfigError(f"{where} 的 `type` 必须是文本字符串。")
    if has_key and (not action["key"] or not isinstance(action["key"], str)):
        raise ConfigError(f"{where} 的 `key` 必须是非空的键名字符串。")

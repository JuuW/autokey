"""在鼠标指针位置弹出可点选的菜单列表(基于 PyObjC 的 NSMenu)。

用 macOS 原生 NSMenu 在当前鼠标坐标处弹出,比 AppleScript 的 `choose from
list`(总是居中显示)更贴近光标,点选更顺手。依赖 pyobjc-framework-Cocoa,
已随 pynput 一并安装。
"""

from __future__ import annotations

from typing import List, Optional

try:
    import AppKit
except ImportError as e:  # pragma: no cover - macOS 上随 pynput 安装,通常可用
    _IMPORT_ERROR: Optional[Exception] = e
else:
    _IMPORT_ERROR = None


class MenuError(Exception):
    """弹出菜单时出错(如 PyObjC 不可用)。"""


def _mouse_location_cocoa() -> "AppKit.NSPoint":
    """取当前鼠标位置(Cocoa 全局坐标,原点在主屏左下角)。

    直接用 NSEvent.mouseLocation() 拿 Cocoa 坐标,省去从 Quartz(左上原点)
    手动翻转 Y 的步骤,多屏下也无需关心鼠标落在哪块屏——全局坐标系是唯一的。
    """
    return AppKit.NSEvent.mouseLocation()


def _ensure_accessory_app() -> None:
    """确保有 NSApplication 实例,并设为辅助型(不在 Dock 显示、不抢焦点)。

    默认的 NSApplication 是 .regular 激活策略,会在 Dock 出现图标并因无法真正
    前台化而持续跳动。后台弹菜单工具应为 .accessory,只做一次即可。
    """
    app = AppKit.NSApplication.sharedApplication()
    if app.activationPolicy() != AppKit.NSApplicationActivationPolicyAccessory:
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)


def choose_from_menu(title: str, item_names: List[str]) -> Optional[str]:
    """在鼠标位置弹出原生菜单让用户选择,返回选中项名;取消返回 None。"""
    if _IMPORT_ERROR is not None:
        raise MenuError(
            f"无法加载 PyObjC,弹出菜单需要 macOS 与 pyobjc:{_IMPORT_ERROR}"
        )

    # 确保有 NSApplication 且为辅助型,NSMenu 才能正常弹出且不污染 Dock。
    _ensure_accessory_app()

    menu = AppKit.NSMenu.alloc().initWithTitle_(title or "AutoKey")
    menu.setAutoenablesItems_(False)

    # 用 item 的 tag 记住它在 item_names 中的下标,选中后按 tag 回查名字。
    for index, name in enumerate(item_names):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            name, None, ""
        )
        item.setTag_(index)
        item.setEnabled_(True)
        menu.addItem_(item)

    location = _mouse_location_cocoa()
    # inView 传 None 时,location 视为屏幕坐标,菜单即在鼠标处弹出。
    # 该调用同步阻塞,直到用户选中某项或点别处取消。
    chosen = menu.popUpMenuPositioningItem_atLocation_inView_(None, location, None)

    if not chosen:  # 用户取消(点击别处或按 Esc)
        return None

    selected = menu.highlightedItem()
    if selected is not None:
        return item_names[selected.tag()]

    # 极少数情况下拿不到高亮项,退回“未选中”处理。
    return None

"""在 macOS 菜单栏(status bar)放一个图标,点它下拉出可执行的菜单项。

基于 PyObjC 的 NSStatusItem。图标用系统 SF Symbol「wand.and.stars」(macOS
11+),不可用时回退为文字「AK」。点击某菜单项时,通过构造时传入的 run_actions
回调执行该项对应的 actions——本模块不直接依赖 actions/pynput,只负责界面。

所有方法都必须在主线程调用(Cocoa 约束)。
"""

from __future__ import annotations

from typing import Callable, List

import AppKit
import objc


class _MenuTarget(AppKit.NSObject):
    """承接菜单项点击的 Objective-C target。

    Python 的普通对象不能直接当 Cocoa 的 action target,需要一个 NSObject 子类。
    每个菜单项用 representedObject 挂住自己的 actions,点击时取回并交给回调执行。
    """

    def initWithCallback_(self, callback):
        self = objc.super(_MenuTarget, self).init()
        if self is None:
            return None
        self._callback = callback  # (actions: list, name: str) -> None
        return self

    def menuItemClicked_(self, sender):
        payload = sender.representedObject()  # {"name": str, "actions": list}
        if payload is not None:
            self._callback(payload["actions"], payload["name"])


class StatusBarIcon:
    """管理菜单栏图标及其下拉菜单;菜单项随配置热加载可重建。"""

    def __init__(self, run_actions: Callable[[List[dict], str], None]) -> None:
        self._target = _MenuTarget.alloc().initWithCallback_(run_actions)
        bar = AppKit.NSStatusBar.systemStatusBar()
        self._item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self._apply_icon()

    def _apply_icon(self) -> None:
        button = self._item.button()
        image = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "wand.and.stars", "AutoKey"
        )
        if image is not None:  # macOS 11+ 才有 SF Symbol
            button.setImage_(image)
        else:
            button.setTitle_("AK")

    def set_items(self, items: List[dict]) -> None:
        """用配置里的 menu.items 重建下拉菜单(热加载后调用)。

        items 每项形如 {"name": str, "actions": list}。菜单末尾附一个「退出
        AutoKey」项,方便无终端时结束后台服务。
        """
        menu = AppKit.NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        for item in items:
            mi = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                item["name"], "menuItemClicked:", ""
            )
            mi.setTarget_(self._target)
            mi.setRepresentedObject_(
                {"name": item["name"], "actions": item["actions"]}
            )
            mi.setEnabled_(True)
            menu.addItem_(mi)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())
        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出 AutoKey", "terminate:", ""
        )
        menu.addItem_(quit_item)

        self._item.setMenu_(menu)

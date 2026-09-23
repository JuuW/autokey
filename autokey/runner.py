"""注册全局快捷键并执行对应的输入动作。

主线程跑 Cocoa 事件循环(AppHelper.runEventLoop),以驱动菜单栏图标常驻;
pynput 快捷键监听在后台线程运行。两类界面(Ctrl+M 弹出的 NSMenu、菜单栏
下拉菜单)最终都在主线程执行动作——NSMenu 只能在主线程弹出。

主线程被事件循环占用,不能再用阻塞的 queue.get / time.sleep 轮询,故改用
NSTimer 周期性地:(1)消费从监听线程投递来的菜单请求;(2)检查配置文件是否
被修改并热加载。
"""

from __future__ import annotations

import os
import queue
import time
from typing import List

import AppKit
import objc
from PyObjCTools import AppHelper
from pynput import keyboard
from pynput.keyboard import Controller

from .actions import ActionError, execute_actions
from .config import ConfigError, load_config
from .menu import MenuError, choose_from_menu
from .statusbar import StatusBarIcon

# NSTimer 检查配置/菜单队列的间隔(秒)
_TICK_INTERVAL = 0.2
# 每隔多少秒才真正检查一次配置文件修改时间(避免每 tick 都 stat)
_CONFIG_CHECK_INTERVAL = 1.0


def build_hotkey_map(
    config: dict, controller: Controller, menu_queue: "queue.Queue"
) -> dict:
    """把每组 hotkey 的 combo 映射到触发回调。

    menu_queue 用于把“弹菜单”请求从 pynput 监听线程投递到主线程执行:NSMenu
    必须在主线程弹出,若在监听线程直接弹会死锁并卡住键盘。
    """
    settings = config["settings"]
    start_delay = settings["start_delay"]
    type_interval = settings["type_interval"]

    mapping = {}
    for hk in config["hotkeys"]:
        combo = hk["combo"]
        name = hk.get("name") or combo
        actions = hk["actions"]

        def make_callback(name=name, actions=actions):
            def callback():
                # 先等一下,让触发用的修饰键松开,避免和输入互相干扰
                time.sleep(start_delay)
                try:
                    execute_actions(controller, actions, type_interval)
                except ActionError as e:
                    print(f"[告警] 执行「{name}」时出错:{e}")
                except Exception as e:  # noqa: BLE001 - 单条出错不应让监听崩溃
                    print(f"[告警] 执行「{name}」时发生意外错误:{e}")

            return callback

        mapping[combo] = make_callback()

    menu = config.get("menu")
    if menu:
        mapping[menu["combo"]] = _make_menu_callback(menu, menu_queue)

    return mapping


def _make_menu_callback(menu: dict, menu_queue: "queue.Queue"):
    """快捷键回调:仅把菜单请求投递到主线程,立即返回,绝不在监听线程弹菜单。

    NSMenu 的事件追踪必须在主线程,否则会死锁并把键盘一起卡住。所以这里只
    put 一个请求(带上当前 menu 配置),真正的弹出与执行由主线程完成。
    """

    def callback():
        menu_queue.put(menu)

    return callback


def _process_menu_request(
    menu: dict, controller: Controller, start_delay: float, type_interval: float
) -> None:
    """在主线程弹出菜单并执行选中项的动作。"""
    title = menu.get("title") or "选择要输入的内容"
    items = menu["items"]
    actions_by_name = {item["name"]: item["actions"] for item in items}
    item_names = [item["name"] for item in items]

    # 让唤出菜单的修饰键先松开,再弹菜单
    time.sleep(start_delay)
    try:
        chosen = choose_from_menu(title, item_names)
    except MenuError as e:
        print(f"[告警] 弹出菜单失败:{e}")
        return
    if chosen is None:  # 用户取消,什么都不输入
        return
    actions = actions_by_name.get(chosen)
    if actions is None:  # 理论上不会发生
        print(f"[告警] 菜单选中项「{chosen}」找不到对应动作。")
        return
    _run_actions(controller, actions, chosen, start_delay, type_interval)


def _run_actions(
    controller: Controller,
    actions: List[dict],
    name: str,
    start_delay: float,
    type_interval: float,
) -> None:
    """执行一组动作(供 Ctrl+M 菜单与菜单栏下拉共用)。

    执行前等 start_delay,让弹窗关闭、焦点回到原输入窗口。
    """
    time.sleep(start_delay)
    try:
        execute_actions(controller, actions, type_interval)
    except ActionError as e:
        print(f"[告警] 执行菜单项「{name}」时出错:{e}")
    except Exception as e:  # noqa: BLE001 - 单条出错不应让监听崩溃
        print(f"[告警] 执行菜单项「{name}」时发生意外错误:{e}")


def _print_hotkeys(config: dict) -> None:
    for hk in config["hotkeys"]:
        print(f"  {hk['combo']:<24} → {hk.get('name') or hk['combo']}")
    menu = config.get("menu")
    if menu:
        print(f"  {menu['combo']:<24} → 弹出菜单({len(menu['items'])} 项)")


def _mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


class _Ticker(AppKit.NSObject):
    """主线程上的周期任务:消费菜单队列 + 配置热加载。

    由 NSTimer 驱动,运行在主线程,可安全地弹 NSMenu、刷新菜单栏。
    """

    def initWith_(self, ctx):
        self = objc.super(_Ticker, self).init()
        if self is None:
            return None
        self._ctx = ctx  # 用字典承载可变状态,避免 PyObjC 属性声明的麻烦
        return self

    def tick_(self, _timer):
        ctx = self._ctx
        # 1) 消费所有待处理的菜单请求(通常最多一个)
        while True:
            try:
                menu = ctx["menu_queue"].get_nowait()
            except queue.Empty:
                break
            _process_menu_request(
                menu, ctx["controller"], ctx["start_delay"], ctx["type_interval"]
            )

        # 2) 按较低频率检查配置文件是否被修改
        ctx["ticks_since_config_check"] += 1
        if ctx["ticks_since_config_check"] < ctx["config_check_every"]:
            return
        ctx["ticks_since_config_check"] = 0

        current = _mtime(ctx["config_path"])
        if current == ctx["last_mtime"]:
            return
        ctx["last_mtime"] = current
        try:
            new_config = load_config(ctx["config_path"])
        except ConfigError as e:
            print(f"[告警] 配置已修改但无法加载,继续使用旧配置:{e}")
            return
        _reload(ctx, new_config)


def _reload(ctx: dict, new_config: dict) -> None:
    """用新配置重建 pynput 监听器并刷新菜单栏项。"""
    ctx["config"] = new_config
    settings = new_config["settings"]
    ctx["start_delay"] = settings["start_delay"]
    ctx["type_interval"] = settings["type_interval"]

    old_listener = ctx.get("listener")
    if old_listener is not None:
        old_listener.stop()

    mapping = build_hotkey_map(new_config, ctx["controller"], ctx["menu_queue"])
    listener = keyboard.GlobalHotKeys(mapping)
    listener.start()
    ctx["listener"] = listener

    _refresh_status_items(ctx)

    print("配置已更新,重新加载快捷键:")
    _print_hotkeys(new_config)
    print()


def _refresh_status_items(ctx: dict) -> None:
    """把当前 menu.items 灌进菜单栏下拉;没有 menu 时给一个占位项。"""
    menu = ctx["config"].get("menu")
    items = menu["items"] if menu else []
    ctx["status_bar"].set_items(items)


def run(config: dict, config_path: str) -> None:
    """启动全局快捷键监听 + 菜单栏图标,并实时热加载配置,阻塞直到退出。"""
    controller = Controller()
    menu_queue: "queue.Queue" = queue.Queue()

    # 主线程跑 Cocoa 事件循环;设为辅助型,不在 Dock 显示、不抢焦点
    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    settings = config["settings"]

    def run_actions_from_statusbar(actions: List[dict], name: str) -> None:
        # 菜单栏点击回调本就在主线程,直接执行即可
        _run_actions(
            controller,
            actions,
            name,
            settings["start_delay"],
            settings["type_interval"],
        )

    status_bar = StatusBarIcon(run_actions_from_statusbar)

    print("AutoKey 已启动,监听以下快捷键:")
    _print_hotkeys(config)
    print("\n菜单栏已出现键盘图标,点它可直接选择要输入的内容。")
    print("配置已开启热加载:修改并保存 config.yaml 后约 1 秒内自动生效。")
    print(
        "提示:若快捷键或菜单栏无反应,请到「系统设置 → 隐私与安全性 → 辅助功能」"
        "为运行本程序的终端 App(或后台服务的 Python 解释器)授权。\n"
    )

    ctx = {
        "config": config,
        "config_path": config_path,
        "controller": controller,
        "menu_queue": menu_queue,
        "status_bar": status_bar,
        "start_delay": settings["start_delay"],
        "type_interval": settings["type_interval"],
        "last_mtime": _mtime(config_path),
        "ticks_since_config_check": 0,
        "config_check_every": max(1, round(_CONFIG_CHECK_INTERVAL / _TICK_INTERVAL)),
        "listener": None,
    }

    # 启动 pynput 监听(后台线程)并初始化菜单栏项
    mapping = build_hotkey_map(config, controller, menu_queue)
    listener = keyboard.GlobalHotKeys(mapping)
    listener.start()
    ctx["listener"] = listener
    _refresh_status_items(ctx)

    ticker = _Ticker.alloc().initWith_(ctx)
    AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        _TICK_INTERVAL, ticker, "tick:", None, True
    )

    try:
        AppHelper.runEventLoop()
    except KeyboardInterrupt:
        print("\n已退出。")
    finally:
        if ctx.get("listener") is not None:
            ctx["listener"].stop()

"""注册全局快捷键并执行对应的输入动作。"""

from __future__ import annotations

import os
import queue
import time

from pynput import keyboard
from pynput.keyboard import Controller

from .actions import ActionError, execute_actions
from .config import ConfigError, load_config
from .menu import MenuError, choose_from_menu

# 每隔多少秒检查一次配置文件是否被修改
_POLL_INTERVAL = 1.0


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
    # 再等一下,让弹窗关闭、焦点回到原来的输入窗口
    time.sleep(start_delay)
    try:
        execute_actions(controller, actions, type_interval)
    except ActionError as e:
        print(f"[告警] 执行菜单项「{chosen}」时出错:{e}")
    except Exception as e:  # noqa: BLE001 - 单条出错不应让监听崩溃
        print(f"[告警] 执行菜单项「{chosen}」时发生意外错误:{e}")


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


def run(config: dict, config_path: str) -> None:
    """启动全局快捷键监听,并实时热加载配置,阻塞直到 Ctrl+C。

    每隔 _POLL_INTERVAL 秒检查 config_path 的修改时间,一旦变化就用新配置
    重建监听器。新配置若解析失败,保留当前配置继续运行,只在日志中报错。
    """
    controller = Controller()
    menu_queue: "queue.Queue" = queue.Queue()

    print("AutoKey 已启动,监听以下快捷键:")
    _print_hotkeys(config)
    print("\n配置已开启热加载:修改并保存 config.yaml 后约 1 秒内自动生效。")
    print("按 Ctrl+C 退出。")
    print(
        "提示:若快捷键无反应,请到「系统设置 → 隐私与安全性 → 辅助功能」"
        "为运行本程序的终端 App(或后台服务的 Python 解释器)授权。\n"
    )

    last_mtime = _mtime(config_path)

    try:
        while True:
            settings = config["settings"]
            start_delay = settings["start_delay"]
            type_interval = settings["type_interval"]
            mapping = build_hotkey_map(config, controller, menu_queue)
            # 每次用最新配置重建监听器;下面的内层循环负责监视文件变化
            with keyboard.GlobalHotKeys(mapping) as listener:
                while listener.running:
                    # 阻塞至多 _POLL_INTERVAL 秒等待菜单请求;NSMenu 必须在本
                    # (主)线程弹出,监听线程只负责把请求投递过来。
                    try:
                        menu = menu_queue.get(timeout=_POLL_INTERVAL)
                    except queue.Empty:
                        pass
                    else:
                        _process_menu_request(
                            menu, controller, start_delay, type_interval
                        )
                    current = _mtime(config_path)
                    if current == last_mtime:
                        continue
                    last_mtime = current
                    try:
                        new_config = load_config(config_path)
                    except ConfigError as e:
                        print(f"[告警] 配置已修改但无法加载,继续使用旧配置:{e}")
                        continue
                    config = new_config
                    print("配置已更新,重新加载快捷键:")
                    _print_hotkeys(config)
                    print()
                    break  # 退出内层循环,由外层用新配置重建监听器
    except KeyboardInterrupt:
        print("\n已退出。")
    except Exception as e:  # noqa: BLE001
        print(f"\n监听启动失败:{e}")
        print(
            "如果在 macOS 上,这通常是缺少辅助功能权限。请到"
            "「系统设置 → 隐私与安全性 → 辅助功能」勾选你的终端 App 后重试。"
        )
        raise

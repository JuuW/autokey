"""注册全局快捷键并执行对应的输入动作。"""

from __future__ import annotations

import time

from pynput import keyboard
from pynput.keyboard import Controller

from .actions import ActionError, execute_actions


def build_hotkey_map(config: dict, controller: Controller) -> dict:
    """把每组 hotkey 的 combo 映射到触发回调。"""
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

    return mapping


def run(config: dict) -> None:
    """启动全局快捷键监听,阻塞直到 Ctrl+C。"""
    controller = Controller()
    mapping = build_hotkey_map(config, controller)

    print("AutoKey 已启动,监听以下快捷键:")
    for hk in config["hotkeys"]:
        print(f"  {hk['combo']:<24} → {hk.get('name') or hk['combo']}")
    print("\n按 Ctrl+C 退出。")
    print(
        "提示:若快捷键无反应,请到「系统设置 → 隐私与安全性 → 辅助功能」"
        "为运行本程序的终端 App 授权。\n"
    )

    try:
        with keyboard.GlobalHotKeys(mapping) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n已退出。")
    except Exception as e:  # noqa: BLE001
        print(f"\n监听启动失败:{e}")
        print(
            "如果在 macOS 上,这通常是缺少辅助功能权限。请到"
            "「系统设置 → 隐私与安全性 → 辅助功能」勾选你的终端 App 后重试。"
        )
        raise

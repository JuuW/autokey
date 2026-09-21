"""注册全局快捷键并执行对应的输入动作。"""

from __future__ import annotations

import os
import time

from pynput import keyboard
from pynput.keyboard import Controller

from .actions import ActionError, execute_actions
from .config import ConfigError, load_config

# 每隔多少秒检查一次配置文件是否被修改
_POLL_INTERVAL = 1.0


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


def _print_hotkeys(config: dict) -> None:
    for hk in config["hotkeys"]:
        print(f"  {hk['combo']:<24} → {hk.get('name') or hk['combo']}")


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
            mapping = build_hotkey_map(config, controller)
            # 每次用最新配置重建监听器;下面的内层循环负责监视文件变化
            with keyboard.GlobalHotKeys(mapping) as listener:
                while listener.running:
                    time.sleep(_POLL_INTERVAL)
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

"""AutoKey 命令行入口:run / init-config / list。"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

from .config import ConfigError, load_config

DEFAULT_CONFIG = "config.yaml"
EXAMPLE_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config.example.yaml",
)


def _cmd_init_config(_args: argparse.Namespace) -> int:
    if os.path.exists(DEFAULT_CONFIG):
        print(f"{DEFAULT_CONFIG} 已存在,未覆盖。如需重建请先删除它。")
        return 1
    if not os.path.exists(EXAMPLE_CONFIG):
        print(f"找不到示例文件:{EXAMPLE_CONFIG}")
        return 1

    shutil.copyfile(EXAMPLE_CONFIG, DEFAULT_CONFIG)
    os.chmod(DEFAULT_CONFIG, 0o600)  # 含明文密码,仅本人可读写
    print(f"已生成 {DEFAULT_CONFIG}(权限 600)。")
    print("请编辑它,填入你的用户名、密码和快捷键,然后运行 `python -m autokey run`。")
    print("⚠️ 该文件含明文密码,已被 .gitignore 忽略,切勿分享或提交。")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print(f"配置文件:{args.config}")
    print(f"共 {len(config['hotkeys'])} 组快捷键:\n")
    for hk in config["hotkeys"]:
        name = hk.get("name") or hk["combo"]
        print(f"  {hk['combo']:<24} → {name}({len(hk['actions'])} 个动作)")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from .runner import run  # 延迟导入,避免 list/init 也依赖 pynput

    config = load_config(args.config)
    run(config)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autokey", description="macOS 快捷键自动输入工具"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="启动监听快捷键")
    p_run.add_argument("--config", "-c", default=DEFAULT_CONFIG, help="配置文件路径")
    p_run.set_defaults(func=_cmd_run)

    p_init = sub.add_parser("init-config", help="从示例生成 config.yaml")
    p_init.set_defaults(func=_cmd_init_config)

    p_list = sub.add_parser("list", help="列出配置里的所有快捷键")
    p_list.add_argument("--config", "-c", default=DEFAULT_CONFIG, help="配置文件路径")
    p_list.set_defaults(func=_cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as e:
        print(f"配置错误:{e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

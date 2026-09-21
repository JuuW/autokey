#!/usr/bin/env bash
# 一键启动 AutoKey:自动准备虚拟环境、装依赖、生成配置,然后开始监听快捷键。
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PYTHON="$VENV/bin/python3"

# 1. 没有虚拟环境就创建并安装依赖
if [ ! -d "$VENV" ]; then
  echo "首次运行,正在创建虚拟环境并安装依赖……"
  python3 -m venv "$VENV"
  "$VENV/bin/python3" -m pip install --quiet --upgrade pip setuptools wheel
  "$VENV/bin/pip" install --quiet -r requirements.txt
fi

# 2. 没有 config.yaml 就从示例生成,并提示先填内容
if [ ! -f "config.yaml" ]; then
  "$PYTHON" -m autokey init-config
  echo
  echo "请先编辑 config.yaml 填入你的用户名/密码/快捷键,然后重新运行本脚本。"
  exit 0
fi

# 3. 启动监听
echo "启动 AutoKey……(Ctrl+C 退出)"
echo "提示:若快捷键无反应,请到「系统设置 → 隐私与安全性 → 辅助功能」为终端 App 授权。"
echo
exec "$PYTHON" -m autokey run

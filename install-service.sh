#!/usr/bin/env bash
# 安装 AutoKey 为 macOS 后台服务(登录时自动启动)。
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"

LABEL="com.autokey.daemon"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
PYTHON="$PROJECT_DIR/.venv/bin/python3"

# 前置检查:虚拟环境和配置必须先就绪
if [ ! -x "$PYTHON" ]; then
  echo "错误:没找到 $PYTHON"
  echo "请先运行 ./start.sh 完成首次安装(创建虚拟环境、装依赖)。"
  exit 1
fi
if [ ! -f "$PROJECT_DIR/config.yaml" ]; then
  echo "错误:没找到 config.yaml"
  echo "请先运行 ./start.sh 生成并编辑配置。"
  exit 1
fi

mkdir -p "$PROJECT_DIR/logs" "$HOME/Library/LaunchAgents"

# 生成 plist(把真实路径填进模板)
cat > "$PLIST_DST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>-m</string>
        <string>autokey</string>
        <string>run</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/autokey.out.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/autokey.err.log</string>
</dict>
</plist>
PLIST

# 若已加载,先卸载再重载(方便更新)
launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"

echo "已安装并启动后台服务:$LABEL"
echo "  plist: $PLIST_DST"
echo "  日志 : $PROJECT_DIR/logs/autokey.{out,err}.log"
echo
echo "⚠️ 重要:后台运行时监听的是 Python 解释器本身,需要单独授予辅助功能权限。"
echo "   打开「系统设置 → 隐私与安全性 → 辅助功能」,点 + 号,按 Cmd+Shift+G 输入以下路径添加并打开开关:"
echo "     $PYTHON"
echo "   授权后运行 ./restart-service.sh 让服务重新读取权限。"

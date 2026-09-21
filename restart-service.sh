#!/usr/bin/env bash
# 重启 AutoKey 后台服务(改了配置或刚授予权限后用)。
set -euo pipefail

LABEL="com.autokey.daemon"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ ! -f "$PLIST_DST" ]; then
  echo "服务未安装,请先运行 ./install-service.sh"
  exit 1
fi

launchctl unload "$PLIST_DST" 2>/dev/null || true
launchctl load "$PLIST_DST"
echo "已重启后台服务:$LABEL"

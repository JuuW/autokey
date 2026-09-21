#!/usr/bin/env bash
# 卸载 AutoKey 后台服务(取消开机自启)。
set -euo pipefail

LABEL="com.autokey.daemon"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ -f "$PLIST_DST" ]; then
  launchctl unload "$PLIST_DST" 2>/dev/null || true
  rm -f "$PLIST_DST"
  echo "已卸载后台服务:$LABEL"
else
  echo "服务未安装(找不到 $PLIST_DST)。"
fi

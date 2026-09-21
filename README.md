# AutoKey — macOS 快捷键自动输入工具

注册全局快捷键,按下后自动执行一段预定义的输入序列。典型用途:在登录框按 `Ctrl+L`,自动输入 **用户名 → Tab → 密码 → 回车**。

## 环境要求

- macOS
- Python 3.9+

## 安装

```bash
cd autokey
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ⚠️ 必须先授予「辅助功能」权限

macOS 出于安全限制,监听全局快捷键和模拟键盘输入都需要授权。**不授权的话程序能启动,但快捷键完全没反应。**

打开 **系统设置 → 隐私与安全性 → 辅助功能**,把运行本程序的终端 App(Terminal 或 iTerm)加入并打开开关。改完最好重启一下终端。

## 使用

1. 生成配置文件:

   ```bash
   python -m autokey init-config
   ```

   会从 `config.example.yaml` 复制出 `config.yaml`(权限自动设为 600)。

2. 编辑 `config.yaml`,填入你的用户名、密码和想要的快捷键(格式见下)。

3. 核对配置解析是否正确:

   ```bash
   python -m autokey list
   ```

4. 启动监听:

   ```bash
   python -m autokey run
   ```

   把光标放进登录框,按下你配置的快捷键即可。`Ctrl+C` 退出。

## 配置格式

```yaml
settings:
  type_interval: 0.02   # 每个字符间隔秒数,防止目标程序漏字符
  start_delay: 0.15     # 触发后到开始输入的延迟,让快捷键的按键先释放

hotkeys:
  - name: "登录公司系统"
    combo: "<ctrl>+l"
    actions:
      - type: "myusername@corp.com"
      - key: "tab"
      - type: "MyS3cretPass"
      - key: "enter"
```

- **combo**:修饰键写成 `<ctrl>` `<alt>`(即 Option)`<cmd>` `<shift>`,普通键直接写字母/数字。例:`<ctrl>+<shift>+p`。
- **actions** 里每一项二选一:
  - `type: "文本"` — 逐字符输入。
  - `key: "键名"` — 按一个特殊键。支持:`tab enter esc space backspace delete up down left right home end page_up page_down f1`–`f12`。

## 安全提示

`config.yaml` 会包含**明文密码**,已在 `.gitignore` 中忽略。请勿分享或提交该文件。仓库里只保留占位用的 `config.example.yaml`。

如果以后想更安全,可把密码迁移到 macOS Keychain(用 `keyring` 库读取),避免明文落盘。

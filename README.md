# AutoKey — macOS 快捷键自动输入工具

注册全局快捷键,按下后自动执行一段预定义的输入序列。典型用途:在登录框按 `Ctrl+L`,自动输入 **用户名 → Tab → 密码 → 回车**。

## 这个项目是干什么的(给未来的自己)

- **目的**:懒得每次手敲用户名密码登录,用一个全局快捷键一键自动填充。
- **原理**:用 Python 库 `pynput` 监听全局快捷键(`GlobalHotKeys`)+ 模拟键盘输入(`Controller`)。快捷键和输入内容都写在 `config.yaml` 里,一个快捷键对应一串"动作"(输入文本 / 按 Tab、Enter 等)。
- **怎么跑**:三种方式——`./start.sh` 前台调试;`./install-service.sh` 装成后台服务开机自启;`python -m autokey run` 手动跑。
- **配置在哪**:`config.yaml`(含明文密码,已 gitignore,权限 600)。示例见 `config.example.yaml`。
- **最大的坑**:macOS 必须授予"辅助功能"权限,否则快捷键完全没反应。**且前台模式给终端授权、后台模式给 Python 解释器授权,两者不通用**(详见下文)。

## 常用命令速查

```bash
./start.sh                       # 前台启动(首次会自动建虚拟环境+装依赖+生成配置)
./install-service.sh             # 装成后台服务,开机自启
./restart-service.sh             # 重启服务(一般只在刚授权后用;改 config.yaml 无需重启)
./uninstall-service.sh           # 卸载后台服务
.venv/bin/python -m autokey list # 查看当前配置解析出的所有快捷键
launchctl list | grep autokey    # 看后台服务是否在跑
cat logs/autokey.err.log         # 看后台服务报错(权限问题会显示在这)
```

> 改快捷键/密码:直接编辑 `config.yaml` 保存即可,约 1 秒自动生效(热加载),**不用重启**。详见下方「配置热加载」。

## 环境要求

- macOS
- Python 3.9+
- 依赖:`pynput`(快捷键监听+键盘模拟)、`pyyaml`(读配置),见 `requirements.txt`

> 注:本机系统自带的 Python 3.9 配旧版 pip 会尝试从源码编译 `pyobjc` 并失败。`start.sh` 已自动升级 pip 以拉取预编译 wheel 绕开此问题;若手动装依赖遇到 `pyobjc-core` 编译报错,先 `pip install --upgrade pip setuptools wheel`。

## ⚠️ 必须先授予「辅助功能」权限

macOS 出于安全限制,监听全局快捷键和模拟键盘输入都需要授权。**不授权的话程序能启动,但快捷键完全没反应。**

打开 **系统设置 → 隐私与安全性 → 辅助功能**,把运行本程序的终端 App(Terminal 或 iTerm)加入并打开开关。改完最好重启一下终端。

## 后台运行 + 开机自启

想让它在后台常驻、开机自动启动(基于 macOS LaunchAgent):

```bash
./install-service.sh     # 安装并立即启动,登录时自动拉起,崩溃自动重启
./restart-service.sh     # 一般只在刚授权后用;改 config.yaml 无需重启(见下)
./uninstall-service.sh   # 卸载,取消开机自启
```

日志在 `logs/autokey.out.log` 和 `logs/autokey.err.log`。

> ⚠️ **后台模式的授权和手动模式不同**:手动 `./start.sh` 是给"终端 App"授权;后台服务不挂在终端下,需要给 **Python 解释器本身**授权,否则监听不到快捷键(日志会出现 `This process is not trusted!`)。
>
> 打开「系统设置 → 隐私与安全性 → 辅助功能」,点 `+`,按 `Cmd+Shift+G` 输入解释器路径(`install-service.sh` 运行后会打印,通常是 `<项目目录>/.venv/bin/python3` 指向的真实文件),添加并打开开关,然后 `./restart-service.sh`。

## 一键启动(前台,便于调试)

```bash
./start.sh
```

脚本会自动完成:首次运行时创建虚拟环境并装依赖 → 没有配置时生成 `config.yaml`(此时会提示你先去填内容)→ 之后每次运行直接启动监听。仍需事先授予下方的「辅助功能」权限。

## 手动使用

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

### 配置热加载

程序运行时会每秒检查一次 `config.yaml`,**改完保存约 1 秒内自动生效,无需重启**(前台 `run` 和后台服务都一样)。若新配置有格式错误,会保留当前配置继续运行,并在日志/终端打印告警——不会中断服务。

## 安全提示

`config.yaml` 会包含**明文密码**,已在 `.gitignore` 中忽略。请勿分享或提交该文件。仓库里只保留占位用的 `config.example.yaml`。

如果以后想更安全,可把密码迁移到 macOS Keychain(用 `keyring` 库读取),避免明文落盘。

## 项目结构

```
autokey/
├── autokey/
│   ├── __main__.py     # 入口,支持 python -m autokey
│   ├── cli.py          # 命令行:run / init-config / list
│   ├── config.py       # 加载+校验 config.yaml
│   ├── actions.py      # 把动作翻译成按键(KEY_MAP 定义支持的特殊键)
│   └── runner.py       # GlobalHotKeys 监听循环 + 触发执行
├── config.example.yaml # 配置示例(占位密码,可提交)
├── config.yaml         # 真实配置(含密码,gitignore,不提交)
├── start.sh            # 前台一键启动
├── install-service.sh  # 装 LaunchAgent 后台服务(生成 ~/Library/LaunchAgents/com.autokey.daemon.plist)
├── restart-service.sh  # 重启服务
├── uninstall-service.sh# 卸载服务
├── requirements.txt
└── logs/               # 后台服务日志(gitignore)
```

## 故障排查

- **按快捷键没反应** → 99% 是辅助功能权限没给对。前台模式给终端授权;后台模式给 Python 解释器授权(两者独立)。改完前台重启终端、后台 `./restart-service.sh`。
- **后台服务在跑但没反应** → 看 `cat logs/autokey.err.log`,出现 `This process is not trusted!` 就是解释器没授权(见"后台运行 + 开机自启"一节)。
- **目标程序漏字符** → 调大 `config.yaml` 里的 `type_interval`。
- **快捷键刚触发就把修饰键也输进去了** → 调大 `start_delay`。
- **换了 .venv 后台服务失效** → 解释器路径变了,重跑 `./install-service.sh`(会填入新路径)。

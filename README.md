# QQ 洛克王国查询机器人 v1

这是一个可接入 QQ 聊天的洛克王国查询机器人。当前版本包含两个功能：`查询 精灵名` 和 `配种 精灵名`。核心服务负责精灵体型数据查询、配种判断、缓存和图片生成；QQ 侧推荐用 NapCatQQ + OneBot v11 HTTP 接入。

## 支持的指令

```text
查询 精灵名
配种 精灵名
```

例如 `查询 水蓝蓝`、`配种 果冻`。回复内容为一张身高、体重、大块头/小不点区间图片，`配种` 会对无法孵蛋的精灵直接提示。

## 本地运行

```powershell
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli "查询 奇丽草"
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli "配种 果冻"
```

生成图片会输出到 `outputs/cards/`，查询缓存会写入 `data/cache/`。

## 数据源

默认读取 `data/pets.seed.json` 本地数据库。真实爬虫走 `DataSource` 接口扩展，或先用 `config/sources.example.json` 这种 JSON URL 模板接一个返回 `PetProfile` 结构的中间源。

```powershell
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli --config config/sources.example.json --no-sample "查询 奇丽草"
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli --config config/sources.example.json --no-sample "配种 果冻"
```

## 本地数据库构建

体型库来自 `data/raw/roco_egg_master/src/pets_data.json`，其中精灵蛋使用原始 `egg_data` 单独生成蛋行；442 个精灵形态仍单独计数。

```powershell
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/build_pet_database.py --limit 442
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts/pre_render_cards.py --force
```

`pre_render_cards.py` 会提前生成全部查询图片。机器人收到查询时优先直接发送已有图片，避免现场渲染。

## QQ 登录聊天

项目已经带 NapCat/OneBot HTTP 适配器。当前流程是：机器人服务监听 `127.0.0.1:8000/onebot`，NapCat 收到 QQ 消息后把事件推给这个地址；机器人再调用 NapCat 的 OneBot HTTP API `127.0.0.1:3000` 发回图片。只有格式错误、未找到精灵、数据源错误这类异常情况会返回文字提示。

### 可视化控制面板

如果不想在终端输入命令，可以直接双击项目根目录里的：

```text
打开机器人控制面板.bat
```

控制面板支持：

```text
启动机器人 / 关闭机器人
启动 NapCat/QQ / 关闭 NapCat
全部启动 / 全部关闭
刷新状态
查看诊断日志
一键更新数据库
打开图片目录
打开日志目录
```

诊断信息也可以在浏览器打开：

```text
http://127.0.0.1:8000/diagnostics
```

### Visual Studio 终端一键启动

在项目根目录打开 PowerShell：

```powershell
.\scripts\start_qq_chat.ps1
```

它会打开两个窗口：

```text
1. Rock Kingdom bot：机器人 HTTP 服务窗口
2. NapCat launcher：QQ/NapCat 登录窗口
```

首次启动需要在 NapCat/QQ 窗口里手动完成登录或扫码。已经登录过时可以：

```powershell
.\scripts\start_qq_chat.ps1 -QuickLogin
```

### NapCat OneBot 配置

NapCat 里需要打开 OneBot v11，并配置两个能力：

```text
HTTP 事件上报地址：http://127.0.0.1:8000/onebot
HTTP API 地址：http://127.0.0.1:3000
Access Token：如果 NapCat 配了 token，这里启动时也加 --onebot-token 同一个值
```

配置模板在 `config/onebot11.rockbot.template.json`。如果你知道登录 QQ 号，也可以生成配置文件：

```powershell
.\scripts\write_napcat_onebot_config.ps1 -QQ 你的QQ号
```

如果 NapCat WebUI 显示配置目录不在项目内，就指定目录：

```powershell
.\scripts\write_napcat_onebot_config.ps1 -QQ 你的QQ号 -NapCatConfigDir "NapCat显示的config目录"
```

检查机器人服务是否在线：

```powershell
.\scripts\check_bot_onebot.ps1
```

QQ 里直接发送：

```text
查询 水蓝蓝
查询 波波拉
配种 果冻
```

默认图片用 OneBot `base64://` 发送，成功率比本地文件路径更稳。如果当前 NapCat 版本更偏好文件路径，可以启动机器人时改：

```powershell
.\scripts\start_bot_onebot.ps1 -ImageMode file-uri
.\scripts\start_bot_onebot.ps1 -ImageMode path
```

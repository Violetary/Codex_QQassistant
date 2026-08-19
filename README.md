# QQ 洛克王国查询机器人 v1

这是一个先离线运行的 Python 核心，用于验证 `@友哈巴赫` 触发、洛克王国精灵查询、缓存和图片生成流程。QQ 账号接入暂时只保留适配接口，后续可接 NapCat/OneBot 或官方 QQ 机器人。

## 支持的指令

```text
@友哈巴赫
@友哈巴赫 精灵名 pvp
@友哈巴赫 精灵名 查蛋
```

只 `@友哈巴赫` 时会回复格式提示。`pvp` 返回 PVP 推荐图片，`查蛋` 返回蛋组、进化链、各阶段身高体重、大块头/小不点区间图片。

## 本地运行

```powershell
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli "@友哈巴赫 奇丽草 查蛋"
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli "@友哈巴赫 奇丽草 pvp"
```

生成图片会输出到 `outputs/`，查询缓存会写入 `data/cache/`。

## 数据源

第一版内置 `SampleSource`，只用于离线验证流程。真实爬虫走 `DataSource` 接口扩展，或先用 `config/sources.example.json` 这种 JSON URL 模板接一个返回 `PetProfile` 结构的中间源。

```powershell
& "C:\Users\Viole\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m rockbot.cli --config config/sources.example.json --no-sample "@友哈巴赫 奇丽草 查蛋"
```

## 后续接 QQ

核心入口是 `BotService.handle_message(message: str)`，返回 `BotReply(text, image_path, ok)`。QQ 适配器只需要把群消息文本传入服务，并把返回的文本/图片发回群聊。

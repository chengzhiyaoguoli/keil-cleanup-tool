# Keil / STM32CubeMX 中间文件清理脚本

用于工程定稿、归档、打包前清理 Keil MDK / STM32CubeMX 工程里的可再生成中间文件，减小工程体积。

脚本文件：`clean_embedded.py`

## 最常用命令

先预览，不删除任何文件：

```powershell
python "F:\STM32project\Keil中间文件清理脚本\clean_embedded.py" -r "F:\STM32project\你的工程目录"
```

确认预览列表没问题后，真正删除：

```powershell
python "F:\STM32project\Keil中间文件清理脚本\clean_embedded.py" -r "F:\STM32project\你的工程目录" --yes
```

查看完整待删除清单：

```powershell
python "F:\STM32project\Keil中间文件清理脚本\clean_embedded.py" -r "F:\STM32project\你的工程目录" --details
```

## 参数说明

| 参数 | 含义 |
| --- | --- |
| `-r 路径` | 指定要清理的工程根目录，等同于 `--root 路径`。这是脚本自己的参数，不是 CMD/PowerShell 的内置命令。 |
| `--yes` | 真正执行删除。不加这个参数时只是预览。 |
| `--details` | 显示完整待删除列表。默认只显示摘要和前 20 项。 |
| `--limit 数字` | 不使用 `--details` 时，控制预览显示多少项。 |
| `--keep-logs` | 保留 `.log` 和 `JLinkLog.txt`。 |
| `--include-backups` | 同时清理 `.bak`、`.orig`、`.old` 这类备份文件。默认不清理。 |
| `--log 文件路径` | 把清理报告写入指定日志文件。 |
| `--exclude 匹配规则` | 排除某些路径，可重复使用。 |
| `--no-color` | 关闭彩色命令行输出。 |

## 默认会清理

主要是 Keil 可重新生成的编译中间文件，例如：

- `.o`, `.obj`
- `.d`, `.dep`
- `.crf`, `.lst`, `.lnp`
- `.axf`, `.elf`
- `.htm`, `.build_log.htm`
- `Objects`, `Listings`

## 默认会保护

这些内容默认不会删除，避免影响 CubeMX 重新生成和 Keil 打开工程：

- `.ioc`, `.mxproject`
- `.uvprojx`, `.uvoptx`, `.uvguix.*`
- `.sct`, `.ld`, `.ini`, `.scvd`
- `.hex`, `.bin`, `.map`
- `RTE`, `DebugConfig`, `.settings`, `.vscode`
- 源码、头文件、文档、图片、压缩包等

## 记忆小抄

只记这两个就够用：

```powershell
# 1. 先看会删什么
python "F:\STM32project\Keil中间文件清理脚本\clean_embedded.py" -r "工程目录"

# 2. 确认后再删
python "F:\STM32project\Keil中间文件清理脚本\clean_embedded.py" -r "工程目录" --yes
```
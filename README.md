# Keil / STM32CubeMX 中间文件清理脚本

用于工程定稿、归档、上传 GitHub 或打包前，清理 Keil MDK / STM32CubeMX 工程中的可再生成中间文件，减少工程体积。

脚本文件：`clean_embedded.py`

## 可靠性结论

在当前常见的 STM32CubeMX + Keil MDK 工程结构下，本工具日常使用已经比较可靠。它采用“只删除明确可再生成文件”的白名单策略，并且默认只预览，不会直接删除。

建议工作流：

1. 先确认工程已经提交或备份。
2. 先 dry-run 预览。
3. 确认列表无误后再加 `--yes` 删除。
4. 清理后重新编译一次工程验证。

推荐命令：

```powershell
git status
python clean_embedded.py -r "path\to\your_project" --keep-logs
python clean_embedded.py -r "path\to\your_project" --keep-logs --yes
git status
```

说明：没有任何清理脚本能做到数学意义上的“绝对可靠”，但配合 Git / GitHub、dry-run 和二次确认，可以达到工程实践中很高的可靠性。

## 最常用命令

先预览，不删除任何文件：

```powershell
python clean_embedded.py -r "path\to\your_project"
```

确认预览列表没问题后，真正删除：

```powershell
python clean_embedded.py -r "path\to\your_project" --yes
```

保留日志文件并删除中间文件：

```powershell
python clean_embedded.py -r "path\to\your_project" --keep-logs --yes
```

查看完整待删除清单：

```powershell
python clean_embedded.py -r "path\to\your_project" --details
```

## 参数说明

| 参数 | 含义 |
| --- | --- |
| `-r 路径` / `--root 路径` | 指定要清理的工程根目录。这是脚本参数，不是 CMD/PowerShell 内置命令。 |
| `--yes` | 真正执行删除。不加这个参数时只预览。 |
| `--details` | 显示完整待删除列表。 |
| `--limit 数字` | 不使用 `--details` 时，控制预览显示多少项。 |
| `--keep-logs` | 保留 `.log` 和 `JLinkLog.txt`。日常建议使用。 |
| `--include-backups` | 同时清理 `.bak`、`.orig`、`.old` 备份文件。默认不清理。 |
| `--log 文件路径` | 把清理报告写入指定日志文件。 |
| `--exclude 匹配规则` | 排除某些路径，可重复使用。 |
| `--no-color` | 关闭彩色命令行输出。 |

命令行参数没有严格前后顺序，只要参数和值成对出现即可。例如下面两条等效：

```powershell
python clean_embedded.py -r "工程目录" --keep-logs --yes
python clean_embedded.py --yes --keep-logs -r "工程目录"
```

## 会清理哪些文件

| 类型 | 来源 | 对工程的影响 |
| --- | --- | --- |
| `*.o` / `*.obj` | 编译器把 `.c` / `.s` 编译后的目标文件 | 不影响，重新编译会生成 |
| `*.d` / `*.dep` | 依赖关系文件，记录源文件依赖哪些头文件 | 不影响，重新编译会生成 |
| `*.crf` | Keil 交叉引用文件，用于符号浏览和跳转辅助 | 不影响，重新编译会生成 |
| `*.lst` | 汇编/列表文件，常见于 `Listings/` | 不影响，重新编译会生成 |
| `*.lnp` | Keil 链接参数文件 | 不影响，重新编译会生成 |
| `*.plg` | Keil 旧版构建日志或插件输出 | 不影响 |
| `*.htm` / `*.html` | Keil 构建报告、链接报告、调用图等 | 不影响 |
| `*.build_log.htm` | Keil 编译日志 HTML | 不影响 |
| `*.axf` | ARM 可执行调试镜像，Keil 下载/调试常生成 | 不影响源码工程，重新编译会生成 |
| `*.elf` | GCC/IDE 类似的可执行调试镜像 | 不影响源码工程，重新编译会生成 |
| `*.__i` | ARMCC 预处理/中间文件 | 不影响 |
| `*.i` / `*.ii` | C/C++ 预处理展开后的中间文件 | 不影响 |
| `*.su` | 栈使用分析文件 | 不影响，重新编译会生成 |
| `JLinkLog.txt` | J-Link 调试/下载日志 | 不影响；使用 `--keep-logs` 时保留 |
| `*.jlink` | J-Link 相关临时/脚本输出 | 一般不影响；如果手写重要 `.jlink` 脚本需注意 |
| `*.log` | 普通日志文件 | 一般不影响；使用 `--keep-logs` 时保留 |
| `*.pyc` / `*.pyo` | Python 缓存文件 | 不影响 |
| `*.swp` / `*.swo` | Vim 等编辑器临时文件 | 不影响 |
| `*~` | 编辑器备份临时文件 | 不影响 |
| `*.bak` / `*.orig` / `*.old` | 备份文件 | 默认不删，只有加 `--include-backups` 才删 |
| `Objects/` | Keil 编译输出目录 | 不影响，重新编译会生成 |
| `Listings/` | Keil 列表/报告输出目录 | 不影响，重新编译会生成 |
| `Debug/` / `Release/` | CubeIDE/GCC/部分 IDE 构建输出目录 | 只有看起来像构建目录才删；不影响 |
| `__pycache__/` | Python 缓存目录 | 不影响 |

## 默认保护哪些文件

这些内容默认不会删除，用于避免影响 CubeMX 重新生成、Keil 打开工程、重新编译或归档交付：

| 类型 | 说明 |
| --- | --- |
| `*.c`, `*.h`, `*.s`, `*.asm`, `*.cpp`, `*.hpp` | 源码、头文件、汇编文件 |
| `*.ioc` | STM32CubeMX 工程配置 |
| `.mxproject`, `*.mxproject`, `.project`, `.cproject` | CubeMX / Eclipse 工程元数据 |
| `*.uvproj`, `*.uvprojx` | Keil 工程文件 |
| `*.uvopt`, `*.uvoptx` | Keil 工程选项文件 |
| `*.uvgui.*`, `*.uvguix.*` | Keil 用户界面/调试相关配置 |
| `*.sct`, `*.scf`, `*.ld` | 链接脚本 |
| `*.ini`, `*.scvd`, `*.pdsc` | 调试、组件和包描述相关文件 |
| `*.hex`, `*.bin`, `*.map` | 固件输出和 map 文件，可能用于归档或定位问题 |
| `*.md`, `*.txt`, `*.pdf`, `*.docx`, `*.xlsx`, `*.png`, `*.jpg` 等 | 文档、图片、资料文件 |
| `*.zip`, `*.rar`, `*.7z`, `*.tar`, `*.gz` | 压缩包 |

## 默认跳过哪些目录

脚本不会进入这些目录：

```text
.git
.svn
.hg
.vscode
RTE
DebugConfig
.settings
```

这样可以避免破坏 Git 仓库、Keil RTE 配置、调试配置和编辑器配置。

## 对工程的实际影响

正常情况下，清理后的影响是：

- 工程体积明显变小。
- 第一次重新编译会慢一点，因为中间文件要重新生成。
- Keil 工程、CubeMX 工程、源码、头文件、链接脚本、最终固件默认都会保留。
- 如果某些已提交到 Git 的 `.lst` 等中间文件被清理，`git status` 会显示它们被删除；这是正常的，可以选择提交删除或恢复。

一句话：它清理的是“编译缓存和构建输出”，不是“工程本体”。

## 和 .gitignore 的关系

推荐原则：

```text
clean_embedded.py 会删除的东西，.gitignore 也应该忽略；
clean_embedded.py 保护的东西，.gitignore 不要随便忽略。
```

`.gitignore` 只能阻止未来新生成的中间文件被加入 Git；已经提交过的文件不会因为写入 `.gitignore` 自动消失。如果历史里已经提交了 `.lst` 等中间文件，需要清理后提交一次删除，或用 `git rm --cached` 取消跟踪。

## 记忆小抄

日常只记这两步就够：

```powershell
# 1. 先看会删什么
python clean_embedded.py -r "path\to\your_project" --keep-logs

# 2. 确认后再删
python clean_embedded.py -r "path\to\your_project" --keep-logs --yes
```
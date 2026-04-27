# FTB Quests 一键翻译器

将 Minecraft 整合包的 FTB Quests 任务文本自动翻译为简体中文，支持多种翻译引擎。

> 本项目修改自 [jerrita](https://github.com/jerrita) 的原始代码，在此基础上增加了 DeepSeek / Google / Baidu API 支持、1.21.1+ 版本适配、翻译重试机制等功能。

## 特性

- 硬编码翻译写入 .snbt 文件，无需 i18n 资源包
- 支持 **OpenAI / DeepSeek / Google / Baidu** 四种翻译 API
- DeepSeek 翻译器短文本用 flash 模型、长文本用 reasoner 模型，兼顾速度与质量
- 翻译失败自动重试，内容过滤场景优雅降级返回原文
- 新版脚本通过修改一个配置项即可切换翻译引擎
- 异步并发翻译，充分利用 API 并发能力

## 版本选择

| 脚本 | 适用版本 | 文件格式 | 支持 API |
|------|----------|----------|----------|
| `main.py` | 1.16 ~ 1.20.x | `chapters/` 目录，多个 .snbt | OpenAI 及兼容接口（含 DeepSeek）/ Baidu |
| `main_1.21.1.py` | 1.21.1+ | 单个 `en_us.snbt` 文件 | DeepSeek / OpenAI / Google / Baidu |

> 1.21.1 起 FTB Quests 的存储格式从 `chapters/` 多文件目录变更为单个语言文件，旧版脚本不适用于新版。

## 快速开始

### 1. 准备 API 密钥

新建 `priv.py`，按你使用的翻译引擎填入对应配置：

```python
# OpenAI / DeepSeek / 其他兼容 API（main.py + main_1.21.1.py 通用）
# DeepSeek 的 API 完全兼容 OpenAI 接口，改 base_url 和 model 即可切换
base_url = 'https://api.openai.com/v1'     # 或用 https://api.deepseek.com/v1
api_key = 'sk-xxxxxxxxxxxxxxxx'
model = 'gpt-4o-mini'                      # 可选，默认 gpt-4o-mini；DeepSeek 用 deepseek-v4-flash

# DeepSeek 增强版（仅 main_1.21.1.py，支持 flash/reasoner 双模型分流）
deepseek_base_url = 'https://api.deepseek.com/v1'
deepseek_api_key = 'sk-xxxxxxxxxxxxxxxx'

# Baidu（main.py + main_1.21.1.py 通用）
appid = 'xxxxxxxx'
apikey = 'xxxxxxxx'

# Google 翻译无需密钥（仅 main_1.21.1.py）
# 不需要在 priv.py 中配置任何内容，但需确保网络能访问 Google
```

### 2. 运行翻译

**1.16 ~ 1.20.x 版本：**

```
python main.py
```

1. 将整合包的 `quests/` 目录放到项目根目录
2. 运行 `python main.py`，输出在 `out_chapters/`
3. 将 `out_chapters/` 重命名为 `chapters/`，替换回 `quests/` 目录
4. 把 `quests/` 丢回整合包

**1.21.1+ 版本：**

```
python main_1.21.1.py
```

1. 将整合包中的 `en_us.snbt` 放到项目根目录
2. 打开 `main_1.21.1.py`，修改顶部的 `TRANSLATOR_TYPE` 选择引擎（`"deepseek"` / `"openai"` / `"google"` / `"baidu"`）
3. 运行 `python main_1.21.1.py`
4. 将输出的 `zh_cn.snbt` 丢回整合包

### 3. 新版可调参数

`main_1.21.1.py` 顶部配置区：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `TRANSLATOR_TYPE` | 翻译引擎 | `"deepseek"` |
| `INPUT_FILE` | 输入文件名 | `"en_us.snbt"` |
| `OUTPUT_FILE` | 输出文件名 | `"zh_cn.snbt"` |
| `MODPACK_NAME` | 整合包名称（提供给 AI 作为上下文） | `"Your Modpack"` |
| `DEBUG` | 是否打印翻译过程 | `True` |
| `MERGE_CONSECUTIVE_STRINGS` | 合并连续字符串再翻译 | `True` |
| `THINK_THRESHOLD` | 超过此长度的文本使用 reasoning 模型 | `100` |

## 依赖

```
pip install -r requirements.txt
```

## 致谢

原始代码作者 [jerrita](https://github.com/jerrita)，本项目在其基础上持续增加新功能和版本适配。

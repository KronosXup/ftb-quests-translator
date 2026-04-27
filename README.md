# FTB Quests 一键翻译器

找汉化包要么对不上版本，要么服务端没汉化，索性整一个

## 版本说明

| 脚本 | 适用版本 | 格式 | 支持 API |
|------|----------|------|-----|
| `main.py` | 1.16 ~ 1.20.x | chapters 目录结构 (多个 .snbt) | OpenAI |
| `translate_1.21.1.py` | 1.21.1+ | 单文件 en_us.snbt | DeepSeek / OpenAI / Google / Baidu |

1.21.1 起 FTB Quests 的存储格式变更（从 `chapters/` 目录变为单个 `en_us.snbt`），旧版 `main.py` 不适用于新版，请按版本选用对应脚本。

## Feature

- 硬编码翻译写入，省时省力 (i18n 去他妈)
- 支持 OpenAI / DeepSeek / Google / Baidu 四种 API
- DeepSeek 翻译器支持长短文本分流：短文本用 flash 模型，长文本用 reasoner 模型
- 新版脚本通过 `TRANSLATOR_TYPE` 一键切换翻译引擎
- 默认 Async OpenAI 翻译器，一个大型包可以 10S 翻译完
- 某格雷空岛包在 gpt-4o-mini 下大概用量为 $0.02

## 使用教程

### 1.16 ~ 1.20.x (`main.py`)

- 将你整合包的 quests 目录丢过来 (你也可以 ln)
- 新建 priv.py，并在 main.py 配置你的 Translator
- python main.py
- (Optional) 备份原有 chapters
- mv out_chapters chapters
- mv chapters quests
- 将 quests 丢回去

### 1.21.1+ (`translate_1.21.1.py`)

- 将 en_us.snbt 放到项目根目录
- 新建 priv.py，根据需要配置对应 API 的密钥（见下方 priv.py 格式）
- 在 `translate_1.21.1.py` 顶部修改 `TRANSLATOR_TYPE` 选择翻译引擎（`"deepseek"` / `"openai"` / `"google"` / `"baidu"`）
- python translate_1.21.1.py
- 输出的 zh_cn.snbt 丢回整合包

## priv.py 格式

```python
# baidu（主脚本 + 新版通用）
appid, apikey = 'xxx', 'xxx'

# openai（主脚本 + 新版通用）
base_url = 'https://api.example.com/v1'
api_key = 'sk-1145141919810'

# deepseek（仅新版）
deepseek_base_url = 'https://api.deepseek.com/v1'
deepseek_api_key = 'sk-xxxxxxxxxxxxxxxx'

# google（仅新版，无需密钥，但需网络能访问 Google）
```


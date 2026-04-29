import asyncio
import json
import re
import ftb_snbt_lib as slib

# ========== 配置 ==========
INPUT_FILE = "en_us.snbt"
OUTPUT_FILE = "zh_cn.snbt"
MODPACK_NAME = "Your Modpack"
SRC = "en"
DST = "zh-CN"
DEBUG = True
MERGE_CONSECUTIVE_STRINGS = True
THINK_THRESHOLD = 100

# 翻译器选择: "deepseek" | "openai" | "google" | "baidu"
TRANSLATOR_TYPE = "deepseek"
# =========================


def create_translator():
    if TRANSLATOR_TYPE == "deepseek":
        from priv import deepseek_base_url, deepseek_api_key
        from translator.deepseek import DeepSeekTranslator
        return DeepSeekTranslator(
            base_url=deepseek_base_url,
            api_key=deepseek_api_key,
            fast_model="deepseek-v4-flash",
            reasoner_model="deepseek-reasoner",
            modpack=MODPACK_NAME,
            think_threshold=THINK_THRESHOLD
        )
    elif TRANSLATOR_TYPE == "openai":
        from priv import base_url, api_key
        from translator.openai import OpenAITranslator
        return OpenAITranslator(
            base_url=base_url,
            api_key=api_key,
            modpack=MODPACK_NAME
        )
    elif TRANSLATOR_TYPE == "google":
        from translator.google import GoogleTranslator
        return GoogleTranslator()
    elif TRANSLATOR_TYPE == "baidu":
        from priv import appid, apikey
        from translator.baidu import BaiduTranslator
        return BaiduTranslator(appid, apikey)
    else:
        raise ValueError(f"未知翻译器类型: {TRANSLATOR_TYPE}，可选: deepseek, openai, google, baidu")


translator = create_translator()
_is_async = asyncio.iscoroutinefunction(translator.translate)
_has_context_len = hasattr(translator, 'context_len')


def _list_text_total(lst) -> int:
    """估算一个列表中所有文本内容的总长度（用于判断是否需要深度思考）"""
    total = 0
    for item in lst:
        if isinstance(item, str):
            total += len(item)
        elif isinstance(item, slib.String):
            total += len(str(item))
        elif isinstance(item, slib.Compound) and 'text' in item:
            total += len(str(item['text']))
    return total

cache = {}
errors = []


# ---------- 辅助函数 ----------
def should_translate(text: str) -> bool:
    if not isinstance(text, str) or len(text.strip()) < 2:
        return False
    if re.match(r'^[\dIVXLCDM]+$', text, re.I):
        return False
    if re.match(r'^[a-z0-9_]+:[a-z0-9_]+$', text, re.I):
        return False
    if text.startswith('§'):
        return False
    if len(text) < 2 and not any(c.isalpha() for c in text):
        return False
    return any(c.isalpha() for c in text)


async def translate_text(text: str, path: str = "") -> str:
    if not should_translate(text):
        return text
    if text in cache:
        return cache[text]
    try:
        if _is_async:
            translated = await translator.translate(text, src=SRC, dst=DST)
        else:
            translated = await asyncio.to_thread(translator.translate, text, SRC, DST)
        cache[text] = translated
        if DEBUG:
            print(f'✅ 翻译成功: {text[:50]}... -> {translated[:50]}...')
        return translated
    except Exception as e:
        errors.append({
            "path": path,
            "original": text[:200],
            "error": str(e)[:200]
        })
        print(f"❌ 失败 {path}: {str(e)[:100]}")
        return text


async def translate_component(obj, path: str = ""):
    """递归翻译 JSON 文本组件（支持 list/dict）"""
    if isinstance(obj, str):
        return await translate_text(obj, path)
    elif isinstance(obj, list):
        return [await translate_component(item, f"{path}[{i}]") for i, item in enumerate(obj)]
    elif isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if k == "text" and isinstance(v, str):
                new[k] = await translate_text(v, f"{path}.text")
            elif k in ("hoverEvent", "clickEvent") and isinstance(v, dict):
                new[k] = await translate_component(v, f"{path}.{k}")
            else:
                if isinstance(v, str):
                    new[k] = v
                else:
                    new[k] = await translate_component(v, f"{path}.{k}")
        return new
    else:
        return obj


def merge_strings_in_list(lst):
    """合并列表中的连续纯字符串（保留空字符串）"""
    if not isinstance(lst, list):
        return lst
    new_list = []
    buffer = []
    for item in lst:
        if isinstance(item, str):
            if item == "":
                if buffer:
                    new_list.append("\n".join(buffer))
                    buffer = []
                new_list.append("")
            else:
                buffer.append(item)
        else:
            if buffer:
                new_list.append("\n".join(buffer))
                buffer = []
            new_list.append(merge_strings_in_list(item))
    if buffer:
        new_list.append("\n".join(buffer))
    return new_list


async def process_value(tag, path: str = ""):
    """
    递归翻译 slib Tag 对象，返回翻译后的 tag。
    slib.String 继承自 str（不可变），所以需要返回新对象替换父容器中的旧值。
    """
    if isinstance(tag, slib.String):
        original = tag
        stripped = original.strip()
        if stripped.startswith(('[', '{')):
            try:
                parsed = json.loads(stripped)
                translated_obj = await translate_component(parsed, path)
                new_value = json.dumps(translated_obj, ensure_ascii=False)
                return slib.String(new_value)
            except json.JSONDecodeError:
                return slib.String(await translate_text(original, path))
        else:
            return slib.String(await translate_text(original, path))
    elif isinstance(tag, slib.List):
        if MERGE_CONSECUTIVE_STRINGS:
            merged = merge_strings_in_list(list(tag))
            tag.clear()
            for item in merged:
                if isinstance(item, str):
                    tag.append(slib.String(item))
                else:
                    tag.append(item)
        # 计算整段任务文本总长度，设置翻译器上下文
        prev_context_len = 0
        if _has_context_len:
            total_len = _list_text_total(tag)
            if total_len > THINK_THRESHOLD:
                prev_context_len = translator.context_len
                translator.context_len = total_len
        for idx, item in enumerate(tag):
            new_path = f"{path}[{idx}]"
            tag[idx] = await process_value(item, new_path)
        if _has_context_len and prev_context_len != translator.context_len:
            translator.context_len = prev_context_len
        return tag
    elif isinstance(tag, slib.Compound):
        for key, sub_tag in tag.items():
            new_path = f"{path}.{key}" if path else key
            tag[key] = await process_value(sub_tag, new_path)
        return tag
    return tag


async def main():
    global errors
    print(f"翻译器: {TRANSLATOR_TYPE.upper()} | 加载文件: {INPUT_FILE}")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = slib.load(f)
    except FileNotFoundError:
        print(f"错误：文件 {INPUT_FILE} 不存在")
        return
    except Exception as e:
        print(f"加载失败: {e}")
        return

    print("开始翻译...")
    data = await process_value(data, path="root")

    print(f"保存到: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            slib.dump(data, f)
    except Exception as e:
        print(f"保存失败: {e}")
        return

    if errors:
        with open("translation_errors.txt", 'w', encoding='utf-8') as f:
            f.write(f"共 {len(errors)} 条错误：\n\n")
            for i, e in enumerate(errors, 1):
                f.write(f"{i}. 路径: {e['path']}\n   原文: {e['original']}\n   错误: {e['error']}\n\n")
        print(f"⚠️ 错误已保存到 translation_errors.txt")
    else:
        print("✅ 全部完成，无错误")

    # 关闭翻译器（仅异步客户端需要）
    if hasattr(translator, 'close'):
        result = translator.close()
        if asyncio.iscoroutine(result):
            await result


if __name__ == "__main__":
    asyncio.run(main())

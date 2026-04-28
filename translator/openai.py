import asyncio
import re
from openai import AsyncOpenAI

from translator import Translator
from translator.mc_terms import build_glossary_prompt


class OpenAITranslator(Translator):
    def __init__(self, base_url, api_key, model='gpt-4o-mini', modpack='Modpack'):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.modpack = modpack

    def set_modpack_name(self, modpack: str):
        self.modpack = modpack

    async def translate(self, query: str, src='auto', dst='zh-CN') -> str:
        # 1. 跳过纯颜色代码片段（无字母）
        if any(c in query for c in ['&', '§']):
            clean = re.sub(r'[&§][0-9a-fklmnor]', '', query).strip()
            if not any(c.isalpha() for c in clean):
                print(f"⏭️ 跳过纯颜色代码短文本: {query[:60]}")
                return query

        # 2. 常见占位符直接返回
        if query in ['I', 'i', 'II', 'III', 'IV', 'V']:
            return query

        # 3. 构建翻译提示词
        glossary = build_glossary_prompt()
        prompt = ' '.join([
            f"Please translate the following Minecraft-related text to {dst}.",
            f"This text is from an FTB Quests mod for Minecraft. The modpack name is `{self.modpack}`.",
            f"Do NOT translate item IDs, color codes (§a, &l), or roman numerals.",
            f"Handle JSON text components properly: only translate the 'text' field; keep 'color', 'clickEvent', 'hoverEvent' unchanged.",
            f"Return only the translated text without any explanation.\n\n",
            glossary,
            f"\n\nText to translate:\n{query}"
        ])

        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=1024
                )
                if response.choices and len(response.choices) > 0:
                    translation = response.choices[0].message.content.strip()
                    return translation
                else:
                    raise Exception("Unexpected response format")
            except Exception as e:
                error_msg = str(e)
                retryable = any(code in error_msg for code in ['400', '429', '500', '502', '503', 'content_filter'])
                if retryable and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"⚠️ 翻译出错 ({error_msg[:100]}), {delay} 秒后重试 (尝试 {attempt+1}/{max_retries})... 原文: {query[:50]}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ 翻译失败 (最终): {error_msg} | 原文: {query[:100]}")
                    if 'content_filter' in error_msg:
                        print(f"↩️ 因内容过滤返回原文: {query}")
                        return query
                    raise Exception(f"OpenAI translation failed: {error_msg}")
        return query

    async def close(self):
        await self.client.close()
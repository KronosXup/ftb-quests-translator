import asyncio
import re
import time
from openai import AsyncOpenAI
from translator import Translator
from translator.mc_terms import build_glossary_prompt


class DeepSeekTranslator(Translator):
    def __init__(self, base_url, api_key,
                 fast_model='deepseek-v4-flash',
                 reasoner_model='deepseek-reasoner',
                 modpack='Modpack',
                 think_threshold=100):
        """
        Initialize DeepSeek translator
        :param base_url: API base URL (e.g. https://api.deepseek.com/v1)
        :param api_key: API key
        :param fast_model: Fast non-reasoning model name
        :param reasoner_model: Reasoning model name
        :param modpack: Modpack name for context
        :param think_threshold: Use reasoning model if text longer than this
        """
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.fast_model = fast_model
        self.reasoner_model = reasoner_model
        self.modpack = modpack
        self.think_threshold = think_threshold

    def _choose_model(self, text: str) -> str:
        """Choose model based on text length and complexity"""
        if len(text) > self.think_threshold:
            return self.reasoner_model
        if len(text.split()) > 20:
            return self.reasoner_model
        if text.strip().startswith(('[', '{')):
            return self.reasoner_model
        if ('&' in text or '§' in text) and len(text) > 50:
            return self.reasoner_model
        return self.fast_model

    @staticmethod
    def _dynamic_max_tokens(text: str, model: str = None) -> int:
        """
        Dynamically compute max_tokens based on text length and model type.
        Chinese translations typically need ~2.5x characters, reasoning model may need more.
        Lower bound raised to 768 to reduce truncation.
        """
        base_ratio = 2.5
        if model and 'reasoner' in model:
            base_ratio = 3.0
        estimated = int(len(text) * base_ratio)
        return max(768, min(4096, estimated))   # 下限提升至768

    @staticmethod
    def _is_invalid_translation(original: str, translated: str) -> bool:
        """Check if translation result is invalid (ellipsis, empty, too short)"""
        if not translated or translated.strip() == '':
            return True
        if translated.strip() in ['...', '…', '.', '。', '..']:
            return True
        if len(original) > 5 and len(translated.strip()) < 2:
            return True
        # If original has letters but translated has no Chinese/letters (likely garbage)
        if re.search(r'[a-zA-Z]', original) and not re.search(r'[\u4e00-\u9fff]', translated):
            if len(original) > 10:
                return True
        return False

    async def translate(self, query: str, src='auto', dst='zh-CN') -> str:
        """
        Translate text, auto-select model, use English prompt + dynamic max_tokens,
        and detect invalid responses with internal retry.
        """
        # Skip pure color code snippets (no letters)
        if any(c in query for c in ['&', '§']):
            clean = re.sub(r'[&§][0-9a-fklmnor]', '', query).strip()
            if not any(c.isalpha() for c in clean):
                return query
        if query in ['I', 'i', 'II', 'III', 'IV', 'V']:
            return query

        model = self._choose_model(query)
        start_time = time.time()

        glossary = build_glossary_prompt()
        base_system_prompt = (
            "You are a professional translator specializing in Minecraft mod content.\n"
            "You are translating FTB Quests text from English to Simplified Chinese.\n"
            "The text belongs to a Minecraft modpack environment, containing item IDs, block names, entity names, and mod-specific terminology.\n"
            f"{glossary}\n"
            "Rules:\n"
            "1. Keep item IDs (e.g., 'minecraft:stone', 'kubejs:custom_item') unchanged.\n"
            "2. Keep color codes (e.g., §a, &l, &6) unchanged.\n"
            "3. Keep Roman numerals (I, II, III) unchanged.\n"
            "4. For JSON text components, translate ONLY the 'text' field; preserve all other fields like 'color', 'clickEvent', 'hoverEvent' exactly as they are.\n"
            "5. Output the COMPLETE translation. Do NOT use '...' or any ellipsis. Even very short text must be fully translated.\n"
            "6. Do not add any explanations, notes, or extra markup. Output only the translated text."
        )
        user_prompt = f"Translate to Chinese: {query}"
        max_tokens = self._dynamic_max_tokens(query, model)

        max_retries = 4
        for attempt in range(max_retries):
            system_prompt = base_system_prompt
            if attempt > 0:
                system_prompt += "\nIMPORTANT: You MUST output a valid translation. Do NOT output '...' or empty text. If you cannot translate, still output the original text."

            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=max_tokens
                )
                elapsed = time.time() - start_time
                if response.choices and len(response.choices) > 0:
                    translated = response.choices[0].message.content.strip()
                    if self._is_invalid_translation(query, translated):
                        print(f"⚠️ Attempt {attempt+1}/{max_retries}: Invalid translation '{translated}', retrying...")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            print(f"❌ Max retries exceeded, returning original")
                            return query
                    print(f"⏱️ [{model}] took {elapsed:.2f}s | original {len(query)} chars | max_tokens={max_tokens}")
                    display = translated[:200] + '...' if len(translated) > 200 else translated
                    print(f"   Translation: {display}")
                    return translated
                else:
                    raise Exception("Empty response")
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Translation failed after {max_retries} attempts: {e} | preview: {query[:80]}")
                    return query
                print(f"⚠️ Request error (attempt {attempt+1}/{max_retries}): {e}, retrying...")
                await asyncio.sleep(2 ** attempt)
        return query

    async def close(self):
        await self.client.close()
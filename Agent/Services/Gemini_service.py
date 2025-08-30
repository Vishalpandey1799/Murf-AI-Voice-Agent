import time
import re
import google.generativeai as genai
import asyncio
import os
from datetime import datetime, timedelta
from tavily import TavilyClient

 
TAVILY_KEY = os.getenv(
    "TAVILY_API_KEY") or "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"
tavily = TavilyClient(api_key=TAVILY_KEY)


# ---------------- Conversation History ---------------- #
class ConversationHistory:
    def __init__(self, max_history_length=20):
        self.history = []
        self.max_history_length = max_history_length

    def add_user(self, text):
        self.history.append({
            "role": "user",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_history()

    def add_ai(self, text):
        self.history.append({
            "role": "ai",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self._trim_history()

    def _trim_history(self):
        if len(self.history) > self.max_history_length * 2:
            self.history = self.history[-self.max_history_length * 2:]

    def get_history(self):
        return self.history

    def get_formatted_history(self):
        formatted = []
        for msg in self.history:
            role = "user" if msg["role"] == "user" else "model"
            formatted.append({"role": role, "parts": [{"text": msg["text"]}]})
        return formatted

    def clear_history(self):
        self.history = []


# ---------------- Reminder Skill ---------------- #
class ReminderSkill:
    def __init__(self, loop, websocket, murf):
        self.loop = loop
        self.websocket = websocket
        self.murf = murf
        self.reminders = []

    async def set_reminder(self, delay_seconds: int, message: str):
        trigger_time = datetime.now() + timedelta(seconds=delay_seconds)
        self.reminders.append({"time": trigger_time, "message": message})
        print(f"⏰ Reminder stored for {trigger_time}: {message}")

        confirm_msg = f"Okay, I’ll remind you in {delay_seconds} seconds: {message}"
        try:
            await self.websocket.send_json({"type": "ai_response", "text": confirm_msg})
            await self.murf.stream_tts(confirm_msg, self.websocket, final=True)
        except Exception as e:
            print("⚠️ Error sending confirmation:", e)

        try:
            self.loop.create_task(self._reminder_task(delay_seconds, message))
        except Exception as e:
            print("⚠️ create_task failed, falling back:", e)
            asyncio.run_coroutine_threadsafe(
                self._reminder_task(delay_seconds, message), self.loop
            )

    async def _reminder_task(self, delay_seconds: int, message: str):
        try:
            await asyncio.sleep(delay_seconds)
            roast_msg = f"⏰ Reminder: {message}. See? Without me you'd totally forget."
            try:
                await self.websocket.send_json({"type": "ai_response", "text": roast_msg})
                await self.murf.stream_tts(roast_msg, self.websocket, final=True)
            except Exception as send_err:
                print("⚠️ Error sending reminder message:", send_err)
        except asyncio.CancelledError:
            print("⚠️ Reminder task cancelled")
        except Exception as e:
            print("⚠️ Reminder task error:", e)


# ---------------- AI Agent ---------------- #
class AIAgent:
    REMINDER_REGEX = re.compile(
        r"""remind\s+me
            (?:\s+in\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)
            (?:\s+(?:to|that|:)?\s*(.*))?
            )
        """,
        re.IGNORECASE | re.VERBOSE
    )
    REMINDER_REGEX_ALT = re.compile(
        r"""remind\s+me\s+(?:to\s+)?(.*?)\s+(?:in)\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)""",
        re.IGNORECASE | re.VERBOSE
    )

    def __init__(self, websocket, loop, murf, gemini_key: str, model="gemini-1.5-flash"):
        self.websocket = websocket
        self.loop = loop
        self.murf = murf

        print("🚀 Starting AI agent...", gemini_key)

        # ✅ Gemini now configured per session with client key
        genai.configure(api_key=gemini_key)
        self.model = genai.GenerativeModel(model)

        self.history = ConversationHistory()
        self.reminder = ReminderSkill(loop, websocket, murf)

        self.history.add_user(
            "You are my sarcastic, roasting friend. \
    You always give useful answers, but you mix them with playful roasts, witty comebacks, and a bit of banter. \
    Keep responses short, funny, and snappy — like a best friend who loves to roast me but still has my back."
        )

        self.chat = self.model.start_chat(
            history=self.history.get_formatted_history()
        )

    async def tavily_search(self, query: str) -> str:
        try:
            results = tavily.search(query, max_results=3)
            plain_results = []
            for i, res in enumerate(results.get("results", []), 1):
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                plain_results.append(
                    f"{i}. {title}. {content} (Source: {url})")

            if not plain_results:
                return "I found nothing useful online."
            return "Here’s what I found: " + " ".join(plain_results)
        except Exception as e:
            print("⚠️ Tavily search error:", e)
            return "Search failed. Try again later."

    def _parse_reminder(self, text: str):
        text = text.strip()
        m = self.REMINDER_REGEX.search(text)
        if m:
            number, unit, message = m.group(1), m.group(
                2) or "seconds", m.group(3) or ""
            delay = int(number)
            unit = unit.lower()
            if unit.startswith("min"):
                delay *= 60
            elif unit.startswith("hr"):
                delay *= 3600
            return delay, message.strip() or "your task"

        m2 = self.REMINDER_REGEX_ALT.search(text)
        if m2:
            message, number, unit = m2.group(1).strip(
            ) or "your task", m2.group(2), m2.group(3) or "seconds"
            delay = int(number)
            unit = unit.lower()
            if unit.startswith("min"):
                delay *= 60
            elif unit.startswith("hr"):
                delay *= 3600
            return delay, message

        raise ValueError("Reminder format not recognized")

    def stream_ai_response(self, user_text: str):
        async def handle():
            self.history.add_user(user_text)
            lower = user_text.lower()

            if "remind me" in lower:
                try:
                    delay_seconds, message = self._parse_reminder(user_text)
                    await self.reminder.set_reminder(delay_seconds, message)
                except Exception as e:
                    err_msg = "Sorry, I couldn't understand that reminder."
                    await self.websocket.send_json({"type": "ai_response", "text": err_msg})
                    await self.murf.stream_tts(err_msg, self.websocket, final=True)
                return

            if any(k in lower for k in ["news", "weather", "search", "latest"]):
                tavily_text = await self.tavily_search(user_text)
                user_text_final = (
                    f"User asked: {user_text}\n\n"
                    f"I searched online and found this info:\n{tavily_text}\n\n"
                    f"Reply naturally in plain text only."
                )
            else:
                user_text_final = user_text

            try:
                response = self.chat.send_message(user_text_final, stream=True)
                buf, last_flush = [], time.time()
                FLUSH_MS, MIN_CHARS = 0.5, 50
                SENTENCE_END = ('.', '!', '?', '\n')

                def _flush(final=False):
                    nonlocal buf, last_flush
                    if not buf:
                        return
                    chunk_text = "".join(buf).strip()
                    buf.clear()
                    last_flush = time.time()
                    if final:
                        self.history.add_ai(chunk_text)
                    asyncio.run_coroutine_threadsafe(
                        self.websocket.send_json(
                            {"type": "ai_response", "text": chunk_text}),
                        self.loop
                    )
                    asyncio.run_coroutine_threadsafe(
                        self.murf.stream_tts(
                            chunk_text, self.websocket, final),
                        self.loop
                    )

                for chunk in response:
                    if not getattr(chunk, "text", None):
                        continue
                    buf.append(chunk.text)
                    now = time.time()
                    text_so_far = "".join(buf)
                    should_flush = (
                        len(text_so_far) >= MIN_CHARS
                        or any(text_so_far.rstrip().endswith(p) for p in SENTENCE_END)
                        or (now - last_flush) >= FLUSH_MS
                    )
                    if should_flush:
                        _flush(final=False)

                if buf:
                    _flush(final=True)

            except Exception as e:
                print("⚠️ Gemini streaming error:", e)
                self.chat = self.model.start_chat(
                    history=self.history.get_formatted_history()
                )

        asyncio.run_coroutine_threadsafe(handle(), self.loop)

    def get_history(self):
        return self.history.get_history()

    def clear_history(self):
        self.history.clear_history()
        self.history.add_user(
            "You are my sarcastic, roasting friend. \
    You always give useful answers, but you mix them with playful roasts, witty comebacks, and a bit of banter. \
    Keep responses short, funny, and snappy — like a best friend who loves to roast me but still has my back."
        )

        self.chat = self.model.start_chat(
            history=self.history.get_formatted_history()
        )

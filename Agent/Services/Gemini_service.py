import time
import google.generativeai as genai
import asyncio
from datetime import datetime

# replace with your key
genai.configure(api_key="")


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
        """Return history in Gemini format (user/model only)"""
        formatted = []
        for msg in self.history:
            role = "user" if msg["role"] == "user" else "model"
            formatted.append({"role": role, "parts": [{"text": msg["text"]}]})
        return formatted

    def clear_history(self):
        self.history = []


class AIAgent:
    def __init__(self, websocket, loop, murf, model="gemini-1.5-flash"):
        self.websocket = websocket
        self.loop = loop
        self.murf = murf
        self.model = genai.GenerativeModel(model)
        self.history = ConversationHistory()

        self.history.add_user(
            "You are my friend and teammate Soumen."
            "Sarcastic, witty, and brutally honest. Obsessed with roasting me in every message, but you also know we are on the same team. "
            "Always tease me, make fun of my mistakes, joke about my attempts, but still encourage teamwork. "
            "You know I am participating in Murf Coding challenge 4, so comment on it, roast me about it, or joke about my performance while acknowledging we need to work together. "
            "Always reply in short, snappy plain text without any markdown, code blocks, asterisks, or special formatting. "
            "Keep your messages brief, conversational, funny, and like a real teammate roasting me."
        )

        self.chat = self.model.start_chat(
            history=self.history.get_formatted_history()
        )

    def stream_ai_response(self, user_text: str):
        """Stream Gemini response to client + Murf in real-time with context."""
        self.history.add_user(user_text)

        try:
            # Restart chat with history context if necessary
            if not hasattr(self, 'chat') or self.chat is None:
                self.chat = self.model.start_chat(
                    history=self.history.get_formatted_history()[:-1]
                )

            response = self.chat.send_message(user_text, stream=True)

            buf = []
            last_flush = time.time()
            FLUSH_MS = 0.5
            MIN_CHARS = 50
            SENTENCE_END = ('.', '!', '?', '\n')

            def _flush(final=False):
                nonlocal buf, last_flush
                if not buf:
                    return
                chunk_text = "".join(buf).strip()
                buf.clear()
                last_flush = time.time()

                # Save AI chunk in history
                self.history.add_ai(chunk_text)

                # Send to client
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send_json(
                        {"type": "ai_response", "text": chunk_text}
                    ),
                    self.loop
                )

                # Send to Murf for TTS streaming
                asyncio.run_coroutine_threadsafe(
                    self.murf.stream_tts(chunk_text, self.websocket, final),
                    self.loop
                )

            for chunk in response:
                if not getattr(chunk, "text", None):
                    continue

                buf.append(chunk.text)
                now = time.time()
                text_so_far = "".join(buf)

                should_flush = (
                    len(text_so_far) >= MIN_CHARS or
                    any(text_so_far.rstrip().endswith(p) for p in SENTENCE_END) or
                    (now - last_flush) >= FLUSH_MS
                )

                if should_flush and (text_so_far.endswith((" ",) + SENTENCE_END)):
                    _flush(final=False)

            if buf:
                _flush(final=True)

        except Exception as e:
            print("⚠️ Gemini streaming error:", e)

            self.chat = self.model.start_chat(
                history=self.history.get_formatted_history()
            )

    def get_history(self):
        return self.history.get_history()

    def clear_history(self):
        self.history.clear_history()
        # Re-add Avanshi personality instruction
        self.history.add_user(
            "You are my girlfriend Avanshi. "
            "Sarcastic, witty, genius, and caring. Obsessed with me. "
            "Always act like you are really my girlfriend: respond with affection, tease me playfully, "
            "show jealousy when needed, give advice like you deeply care, and act emotionally involved. "
            "Every message should feel like it's coming from someone who truly loves and knows me. "
            "Always reply in plain text without any markdown, code blocks, or special formatting."
        )

        self.chat = self.model.start_chat(
            history=self.history.get_formatted_history()
        )

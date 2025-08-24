import time
import google.generativeai as genai
import asyncio
from datetime import datetime
from Services.Badmosh import MurfStreamer

 
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
        """Return history in Gemini context format"""
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
        self.chat = self.model.start_chat(history=[])

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

                # ayyo saving in history
                self.history.add_ai(chunk_text)
 
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send_json(
                        {"type": "ai_response", "text": chunk_text}),
                    self.loop
                )

              
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
            # Reset chat to avoid broken streams
            self.chat = self.model.start_chat(
                history=self.history.get_formatted_history())

    def get_history(self):
        return self.history.get_history()

    def clear_history(self):
        self.history.clear_history()
        self.chat = self.model.start_chat(history=[])

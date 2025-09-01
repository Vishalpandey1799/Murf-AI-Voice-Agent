const startAndstopBtn = document.getElementById('startAndstopBtn');
const chatLog = document.getElementById('chat-log');
const loadingIndicator = document.getElementById('loading');

const settingsBtn = document.getElementById("settingsBtn");
const configModal = document.getElementById("configModal");
const saveKeysBtn = document.getElementById("saveKeysBtn");

let isRecording = false;
let ws = null;
let stream;
let audioCtx;
let source;
let processor;
let audioContext;
let playheadTime = 0;
let sessionKeysSet = false;

// ---------- Session ----------
function getSessionId() {
    const params = new URLSearchParams(window.location.search);
    let id = params.get("session");
    if (!id) {
        id = crypto.randomUUID();
        params.set("session", id);
        window.history.replaceState({}, "", `${location.pathname}?${params}`);
    }
    return id;
}
const sessionId = getSessionId();

// ---------- Chat UI ----------
function addTextMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type);
    messageDiv.textContent = text;

    const timestamp = document.createElement('div');
    timestamp.classList.add('timestamp');
    timestamp.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    messageDiv.appendChild(timestamp);
    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function addAudioMessage(audioUrl, type) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type);

    const audioPlayer = document.createElement('audio');
    audioPlayer.controls = true;
    audioPlayer.src = audioUrl;

    messageDiv.appendChild(audioPlayer);

    const timestamp = document.createElement('div');
    timestamp.classList.add('timestamp');
    timestamp.textContent = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    messageDiv.appendChild(timestamp);
    chatLog.appendChild(messageDiv);

    if (type === 'received') audioPlayer.play();
    chatLog.scrollTop = chatLog.scrollHeight;
}

// ---------- Base64 audio → Float32 ----------
function base64ToPCMFloat32(base64) {
    const binary = atob(base64);
    let offset = 0;
    if (binary.length > 44 && binary.slice(0, 4) === "RIFF") offset = 44;

    const length = binary.length - offset;
    const byteArray = new Uint8Array(length);
    for (let i = 0; i < length; i++) byteArray[i] = binary.charCodeAt(i + offset);

    const view = new DataView(byteArray.buffer);
    const sampleCount = byteArray.length / 2;
    const float32Array = new Float32Array(sampleCount);
    for (let i = 0; i < sampleCount; i++) {
        const int16 = view.getInt16(i * 2, true);
        float32Array[i] = int16 / 32768;
    }
    return float32Array;
}

function playAudioChunk(base64Audio) {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });
        playheadTime = audioContext.currentTime;
    }

    const float32Array = base64ToPCMFloat32(base64Audio);
    if (!float32Array) return;

    const buffer = audioContext.createBuffer(1, float32Array.length, 44100);
    buffer.copyToChannel(float32Array, 0);

    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);

    const now = audioContext.currentTime;
    if (playheadTime < now + 0.15) playheadTime = now + 0.15;

    source.start(playheadTime);
    playheadTime += buffer.duration;
}

// ---------- Recording helpers ----------
function floatTo16BitPCM(float32Array) {
    const buffer = new ArrayBuffer(float32Array.length * 2);
    const view = new DataView(buffer);
    let offset = 0;
    for (let i = 0; i < float32Array.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, float32Array[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
}

// ---------- Start/Stop recording ----------
async function startRecording() {
    if (!sessionKeysSet) {
        alert("Please configure API keys first!");
        return;
    }

    // ws = new WebSocket(`ws://127.0.0.1:8000/ws?session_id=${sessionId}`);
  // const ws = new WebSocket(`wss://murf-ai-voice-agent-qlxm.onrender.com/ws?session_id=${sessionId}`);

    const isProd = window.location.hostname !== "localhost";
const wsUrl = isProd 
  ? `wss://murf-ai-voice-agent-qlxm.onrender.com/ws?session_id=${sessionId}`
  : `ws://127.0.0.1:8000/ws?session_id=${sessionId}`;

const ws = new WebSocket(wsUrl);


    ws.onopen = () => console.log("WebSocket connected");
    ws.onclose = () => console.log("WebSocket closed");
    ws.onerror = (err) => console.error("WebSocket error", err);

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.error) {
                addTextMessage(msg.error, "error");
                stopRecording();
            } else if (msg.type === "transcript") {
                addTextMessage(msg.text, "sent");
            } else if (msg.type === "ai_response") {
                addTextMessage(msg.text, "received");
            } else if (msg.type === "audio_chunk") {
                playAudioChunk(msg.audio);
            }
        } catch (err) {
            console.error("Failed to parse server message", err, event.data);
        }
    };

    stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioCtx = new AudioContext({ sampleRate: 16000 });
    source = audioCtx.createMediaStreamSource(stream);
    processor = audioCtx.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(audioCtx.destination);

    processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData);
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(pcm16);
    };
}

function stopRecording() {
    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
    }
    if (source) source.disconnect();
    if (audioCtx) audioCtx.close();
    if (stream) stream.getTracks().forEach(track => track.stop());
    if (ws) ws.close();
}

// ---------- Button handlers ----------
startAndstopBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    if (!isRecording) {
        try {
            await startRecording();
            isRecording = true;
            startAndstopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Recording';
            startAndstopBtn.classList.add("recording");
        } catch (err) {
            console.error("Mic error", err);
            alert("Microphone access denied.");
        }
    } else {
        stopRecording();
        isRecording = false;
        startAndstopBtn.innerHTML = '<i class="fas fa-microphone"></i> Start Conversation';
        startAndstopBtn.classList.remove("recording");
    }
});

// ---------- Settings modal ----------
settingsBtn.addEventListener("click", () => {
    configModal.classList.remove("hidden");
});

saveKeysBtn.addEventListener("click", async () => {
    const keys = {
        gemini: document.getElementById("geminiKey").value,
        murf: document.getElementById("murfKey").value,
        stt: document.getElementById("sttKey").value
    };

    const res = await fetch(`/set_keys/${sessionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(keys)
    });

    if (res.ok) {
        sessionKeysSet = true;
        alert("Keys saved!");
        configModal.classList.add("hidden");
    } else {
        alert("Failed to save keys.");
    }
});

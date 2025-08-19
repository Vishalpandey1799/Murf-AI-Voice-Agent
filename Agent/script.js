const startAndstopBtn = document.getElementById('startAndstopBtn');
const chatLog = document.getElementById('chat-log');
const loadingIndicator = document.getElementById('loading');

let isRecording = false;
let ws = null;
let stream;
let audioCtx;
let source;
let processor;

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

/*  Append text message to chat */
function addTextMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', type);
    messageDiv.textContent = text
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
    chatLog.appendChild(messageDiv);

    if (type === 'received') {
        audioPlayer.play();
    }
    chatLog.scrollTop = chatLog.scrollHeight;
}

async function endtoendAudio(formdata) {
    try {
        loadingIndicator.style.display = "flex";

        const response = await fetch(`/agent/chat/${sessionId}`, {
            method: "POST",
            body: formdata
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Server error: ${response.status} ${errorText}`);
        }

        const data = await response.json();
        console.log("Chat History:", data.history);
        return data;

    } catch (error) {
        console.error("Error from transcribe to audio:", error.message);
        addTextMessage(`Error: ${error.message}`, 'error');
    } finally {
        loadingIndicator.style.display = "none";
    }
}

/*  Convert Float32 → PCM16 */
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

/*  Start Recording with Web Audio API */
async function startRecording() {
    ws = new WebSocket("ws://127.0.0.1:8000/ws");

    ws.onopen = () => console.log("WebSocket connected");
    ws.onclose = () => console.log("WebSocket closed");
    ws.onerror = (err) => console.error("WebSocket error", err);

    
    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            console.log(msg)
 
            if (msg.type === "transcript") {
               
                 addTextMessage(msg.text, 'sent');
            } else {
                console.log("Server message:", msg);
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
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(pcm16);
        }
    };
}

/*  Stop Recording */
function stopRecording() {
    if (processor) {
        processor.disconnect();
        processor.onaudioprocess = null;
    }
    if (source) source.disconnect();
    if (audioCtx) audioCtx.close();

    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    if (ws) ws.close();
}

startAndstopBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!isRecording) {
        try {
            await startRecording();
            isRecording = true;
            startAndstopBtn.textContent = "Stop Recording";
            startAndstopBtn.classList.add("recording");
        } catch (err) {
            console.error("Mic error", err);
            alert("Microphone access denied.");
        }
    } else {
        stopRecording();
        isRecording = false;
        startAndstopBtn.textContent = "Start Recording";
        startAndstopBtn.classList.remove("recording");
    }
});

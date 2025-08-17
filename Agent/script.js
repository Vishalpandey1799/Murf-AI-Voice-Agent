  
        const startAndstopBtn = document.getElementById('startAndstopBtn');
        const chatLog = document.getElementById('chat-log');
        const loadingIndicator = document.getElementById('loading');

     
        let isRecording = false;
        let mediaRecorder;
        let audioChunks = [];
        let stream;
        let ws = null;

     

     
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

      
   startAndstopBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!isRecording) {
        try {
            
            ws = new WebSocket("ws://127.0.0.1:8000/ws");

            ws.onopen = () => console.log("WebSocket connected");
            ws.onclose = () => console.log("WebSocket closed");
            ws.onerror = (err) => console.error("WebSocket error", err);

           
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    ws.send(event.data);  
                }
            };

        
            mediaRecorder.start(500);

            isRecording = true;
            startAndstopBtn.textContent = "Stop Recording";
            startAndstopBtn.classList.add("recording");

        } catch (err) {
            console.error("Mic error", err);
            alert("Microphone access denied.");
        }
    } else {
        
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        if (ws) ws.close();

        isRecording = false;
        startAndstopBtn.textContent = "Start Recording";
        startAndstopBtn.classList.remove("recording");
    }
});
 

const startAndstopBtn = document.getElementById("startAndstopBtn");
const recordedAudio = document.getElementById("recordedAudio");
const loading = document.getElementById("loading");
const successMessage = document.getElementById("successMessage");
const audioSection = document.getElementById("audioSection");
const audioPlayer = document.getElementById("audioPlayer");

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let stream;

async function transcriptToaudio(formdata) {
    try {
        const response = await fetch("/tts/echo", {
            method: "POST",
            body: formdata
        });

        if (!response.ok) {
            throw new Error("Failed to generate audio");
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error("Error from transcribe to audio:", error.message);
        alert("An error occurred while generating the voice.");
    }
}

startAndstopBtn.addEventListener("click", async (e) => {
    e.preventDefault();

    if (!isRecording) {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Show loading state
                loading.style.display = "block";
                successMessage.classList.remove("show");
                recordedAudio.style.display = "none";

                const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                let formdata = new FormData();
                formdata.append("file", audioBlob);

               
                const { audio_url } = await transcriptToaudio(formdata);
                console.log(audio_url)

                // Hide loading & show success
                loading.style.display = "none";
                successMessage.classList.add("show");

                successMessage.style.opacity = 1;

                // Play the generated audio
                recordedAudio.src = audio_url;
                recordedAudio.style.display = "block";
                recordedAudio.play();

                setTimeout(() => {
                    successMessage.classList.remove("show");
                }, 3000);
            };

            mediaRecorder.start();
            isRecording = true;
            startAndstopBtn.textContent = "Stop Recording";
            startAndstopBtn.classList.add("stillRecording");

        } catch (err) {
            alert("Microphone access denied or unavailable.");
            console.error(err);
        }
    } else {
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        isRecording = false;
        startAndstopBtn.textContent = "Start Recording";
        startAndstopBtn.classList.remove("stillRecording");
    }
});

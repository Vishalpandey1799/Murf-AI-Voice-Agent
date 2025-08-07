const textInput = document.getElementById('textInput');
const playBtn = document.getElementById('playBtn');
const buttonText = document.getElementById('buttonText');
const loading = document.getElementById('loading');
const successMessage = document.getElementById('successMessage');
const audioSection = document.getElementById('audioSection');
const audioPlayer = document.getElementById('audioPlayer');
const startAndstopBtn = document.getElementById("startAndstopBtn")

 

async function uploadFile(audioblob){

    const formdata = new FormData();
    formdata.append("file" , audioblob)
    const uploaded = await fetch("/upload", {
        method: "POST",
        body: formdata,
    });


    const response = await uploaded.json();


    return response


    
}

async function transcription(filename) {
    const response = await fetch("/transcribe/file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename })
    });

   
    const data = await response.json();

    if (!response.ok) {
        alert("Transcription failed: " + data.detail);
        return;
    }


    document.querySelector(".transcript-box").style.opacity = "1";
  const transcriptBox = document.getElementById("transcriptDisplay");
    transcriptBox.textContent = data.transcript;
     
}


 
const placeholders = [
    "Type your message here and I'll speak it for you...",
    "Enter any text to convert to speech...",
    "What would you like me to say?",
    "Write something and hear it come to life..."
];
let placeholderIndex = 0;
setInterval(() => {
    if (!textInput.value) {
        textInput.placeholder = placeholders[placeholderIndex];
        placeholderIndex = (placeholderIndex + 1) % placeholders.length;
    }
}, 3000);


 let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;
  let stream;
  let response = null;

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
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  const response = await uploadFile(audioBlob);  
  
  console.log(response)
  const audioUrl = URL.createObjectURL(audioBlob);

  recordedAudio.src = audioUrl;
  recordedAudio.style.display = "block";
  recordedAudio.play();
 
  const infoHTML = `
    <div class="upload-info-box">
      <p>✅ ${response.message}</p>
      <p><strong>File:</strong> ${response.filename}</p>
      <p><strong>Size:</strong> ${(response.fileSize / 1024).toFixed(2)} KB</p>
      <p><strong>Type:</strong> ${response.fileType}</p>
    </div>
  `;

  document.getElementById("uploadInfo").innerHTML = infoHTML;
  document.getElementById("uploadInfo").style.display = "block";

  await transcription(response.filename)
  
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
 

 

 
playBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();

    if (!text) {
     
        textInput.style.animation = 'shake 0.5s ease-in-out';
        setTimeout(() => {
            textInput.style.animation = '';
        }, 500);
        return;
    }

 
    buttonText.textContent = '🔄 Processing...';
    loading.style.display = 'block';
    playBtn.disabled = true;
    playBtn.classList.remove('pulse');

    try {
        const response = await fetch("/generate-voice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        if (!response.ok) {
            alert("Failed to generate voice.");
            return;
        }

        const data = await response.json();
      

        audioPlayer.src = data.audio_url;
        audioPlayer.style.display = "block";
        audioPlayer.play();

       
        loading.style.display = 'none';
        successMessage.classList.add('show');
        audioSection.classList.add('show');
        buttonText.textContent = '✨ Generate Voice';
        playBtn.disabled = false;
        playBtn.classList.add('pulse');

   
        setTimeout(() => {
            successMessage.classList.remove('show');
        }, 3000);
    } catch (err) {
        alert("An error occurred. Please try again.");
        console.error(err);
    }
});

 
textInput.addEventListener('input', () => {
    if (textInput.value.length > 100) {
        textInput.style.height = '150px';
    } else {
        textInput.style.height = '120px';
    }
});

 
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        75% { transform: translateX(5px); }
    }
`;
document.head.appendChild(shakeStyle);

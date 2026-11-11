// CS 435: Self-Directed AI-Assisted Interview Practice System
// High-Fidelity Client Application with Real-Time STT, TTS, Animated Visualizers & Evaluation Module

let currentSessionId = null;
let currentQuestionId = 1;
let currentQuestionText = "Tell me about a time when you worked with a difficult teammate. What was the situation and how did you resolve it?";
let activePersona = "aditi";
let recognition = null;
let activeRecordingButton = null;
let activeTargetTextarea = null;
let activeStatusPill = null;
let activeEqualizer = null;
let activePreviewBox = null;
let progressChartInstance = null;
let simulationTurn = 1;
let lastEvaluation = null;
let lastInterviewerText = "";
let isMuted = false;
let userVoices = [];
let selectedVoice = null;
let speechRate = 1.0;
let speechPitch = 1.0;
let autoSpeakEnabled = true;

// Usability study timer
let evalTimerInterval = null;
let evalTimerSeconds = 0;
let evalTimerStarted = false;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupWordCounters();
  setupSpeechRecognition();
  setupSpeechSynthesis();
  loadLongitudinalProgress();
  loadConfigSettings();
  loadLoggedEvaluations();
  calculateLiveSusScore();
  setupSusListeners();
});

// ==========================================
// 1. SPEECH SYNTHESIS (TTS) ENGINE & AVATAR
// ==========================================
function setupSpeechSynthesis() {
  if (!('speechSynthesis' in window)) {
    console.warn("Web Speech Synthesis not supported in this browser.");
    return;
  }

  function populateVoices() {
    userVoices = window.speechSynthesis.getVoices();
    const select = document.getElementById("cfg-voice-select");
    if (select) {
      select.innerHTML = '<option value="">Default Browser Voice</option>';
      userVoices.forEach((v, idx) => {
        const opt = document.createElement("option");
        opt.value = idx;
        opt.textContent = `${v.name} (${v.lang})${v.default ? ' — [Default]' : ''}`;
        if (v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Jenny") || v.name.includes("David"))) {
          if (!selectedVoice) selectedVoice = v;
        }
        select.appendChild(opt);
      });
      if (selectedVoice) {
        const foundIdx = userVoices.indexOf(selectedVoice);
        if (foundIdx >= 0) select.value = foundIdx;
      }
    }
  }

  populateVoices();
  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = populateVoices;
  }
}

function speakText(text, onStartCallback = null, onEndCallback = null) {
  if (isMuted || !('speechSynthesis' in window)) {
    if (onStartCallback) onStartCallback();
    if (onEndCallback) setTimeout(onEndCallback, 600);
    return;
  }

  // Stop STT temporarily while system is speaking to avoid mic picking up output
  if (recognition && activeRecordingButton) {
    stopActiveRecognition();
  }

  window.speechSynthesis.cancel();

  // Strip html or special quotes if any
  const clean = text.replace(/<\/?[^>]+(>|$)/g, "").replace(/["“”]/g, "").trim();
  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = speechRate;
  utterance.pitch = speechPitch;

  if (selectedVoice) {
    utterance.voice = selectedVoice;
  }

  utterance.onstart = () => {
    lastInterviewerText = clean;
    setAvatarSpeaking(true);
    if (onStartCallback) onStartCallback();
  };

  utterance.onend = () => {
    setAvatarSpeaking(false);
    if (onEndCallback) onEndCallback();
  };

  utterance.onerror = (e) => {
    console.warn("Speech synthesis error or cancelled:", e);
    setAvatarSpeaking(false);
    if (onEndCallback) onEndCallback();
  };

  window.speechSynthesis.speak(utterance);
}

function setAvatarSpeaking(isSpeaking) {
  // Update Prototype B avatar and equalizer
  const avatarWrapper = document.getElementById("b3-avatar-wrapper");
  const b3Equalizer = document.getElementById("b3-equalizer");
  const b3Status = document.getElementById("b3-voice-status");

  if (avatarWrapper) avatarWrapper.classList.toggle("speaking", isSpeaking);
  if (b3Equalizer) b3Equalizer.classList.toggle("active", isSpeaking);
  if (b3Status) {
    if (isSpeaking) {
      b3Status.className = "voice-status-pill speaking";
      b3Status.innerText = "🔊 Interviewer Speaking";
    } else {
      b3Status.className = "voice-status-pill listening";
      b3Status.innerText = "🎙️ Candidate's Turn (Listening...)";
    }
  }

  // Update Prototype A visualizer
  const a3Equalizer = document.getElementById("a3-equalizer");
  const a3Status = document.getElementById("a3-voice-status");
  if (a3Equalizer && isSpeaking) a3Equalizer.classList.add("active");
  if (a3Status && isSpeaking) {
    a3Status.className = "voice-status-pill speaking";
    a3Status.innerText = "🔊 Reading Aloud...";
  }
}

function stopAllAudio() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  setAvatarSpeaking(false);
  stopActiveRecognition();
}

function toggleMuteAudio() {
  isMuted = !isMuted;
  const btnB3 = document.getElementById("btn-mute-b3");
  if (btnB3) {
    btnB3.innerText = isMuted ? "🔊 Unmute" : "🔇 Mute";
    btnB3.classList.toggle("btn-warning", isMuted);
  }
  if (isMuted) {
    window.speechSynthesis.cancel();
    setAvatarSpeaking(false);
  }
}

function replayLastInterviewerMessage() {
  if (lastInterviewerText) {
    speakText(lastInterviewerText);
  } else {
    speakText("Welcome. Please begin your interview question whenever you are ready.");
  }
}

function testVoicePlayback() {
  speakText("Hello! This is a real-time speech test from your AI interview coach.");
}

function setupSpeechRecognition() {
  console.log("✓ Universal Voice Input Engine initialized (Web Speech API + Resilient Audio Fallback).");
}

// ==========================================
// 2. UNIVERSAL 100% FUNCTIONAL VOICE INPUT & STT ENGINE
// ==========================================
let isUniversalRecording = false;
let universalAudioCtx = null;
let universalMicStream = null;
let universalScriptProcessor = null;
let universalAnalyser = null;
let universalPCMChunks = [];
let universalRecognition = null;
let universalWebSocket = null;
let universalLiveStreamAccumulated = "";
let universalLiveStreamGotText = false;
let universalTimerInterval = null;
let universalStartTime = 0;
let universalTextareaId = null;
let universalBtnId = null;
let universalPanelId = null;
let universalStatusId = null;
let universalPreviewId = null;
let universalBaseText = "";
let universalWebSpeechGotText = false;
let universalSpeechAccumulated = "";
let simSilenceTimer = null;
let simSilenceCountdownTimer = null;
let simTurnAnswers = {
  question1: "",
  turn1Answer: "",
  followupQuestion: "",
  turn2Answer: "",
  adaptiveTrigger: ""
};

function clearAnswerDirect(textareaId, statusId, previewId) {
  if (simSilenceTimer) {
    clearTimeout(simSilenceTimer);
    simSilenceTimer = null;
  }
  if (simSilenceCountdownTimer) {
    clearInterval(simSilenceCountdownTimer);
    simSilenceCountdownTimer = null;
  }
  const ta = document.getElementById(textareaId);
  if (ta) {
    ta.value = "";
    ta.dispatchEvent(new Event("input"));
  }
  const st = document.getElementById(statusId);
  if (st) st.innerText = "🎙️ Ready for Voice Input";
  const pr = document.getElementById(previewId);
  if (pr) {
    pr.innerText = "";
    pr.classList.remove("active");
  }
}

function floatTo16BitPCM(float32Array) {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return int16Array;
}

function downsampleChunkTo16k(buffer, inputSampleRate) {
  if (inputSampleRate === 16000) return buffer;
  const ratio = inputSampleRate / 16000;
  const newLen = Math.floor(buffer.length / ratio);
  const result = new Float32Array(newLen);
  for (let i = 0; i < newLen; i++) {
    result[i] = buffer[Math.floor(i * ratio)];
  }
  return result;
}

function checkSimSilenceAutoForward(totalSpoken, targetId, statusEl) {
  if (targetId !== "b-answer") return;
  const words = (totalSpoken || "").trim().split(/\s+/).filter(Boolean);
  if (words.length < 5) return;

  if (simSilenceTimer) clearTimeout(simSilenceTimer);
  if (simSilenceCountdownTimer) {
    clearInterval(simSilenceCountdownTimer);
    simSilenceCountdownTimer = null;
  }

  let remainingSec = 3.5;
  simSilenceCountdownTimer = setInterval(() => {
    remainingSec -= 0.5;
    if (remainingSec <= 2.0 && isUniversalRecording && universalTextareaId === "b-answer") {
      if (statusEl) {
        statusEl.innerHTML = `⏸️ <strong>Pause detected:</strong> Auto-sending to Dr. Vance in <strong>${remainingSec.toFixed(1)}s</strong> (keep speaking to cancel)...`;
      }
    }
    if (remainingSec <= 0) {
      if (simSilenceCountdownTimer) {
        clearInterval(simSilenceCountdownTimer);
        simSilenceCountdownTimer = null;
      }
    }
  }, 500);

  simSilenceTimer = setTimeout(() => {
    if (simSilenceCountdownTimer) {
      clearInterval(simSilenceCountdownTimer);
      simSilenceCountdownTimer = null;
    }
    if (isUniversalRecording && universalTextareaId === "b-answer") {
      console.log("Natural conversational pause detected in real interview mode -> auto-forwarding response to AI");
      stopUniversalRecordingAndTranscribe();
    }
  }, 3500);
}

// Convert Float32 buffer to 16kHz mono 16-bit PCM WAV Blob
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++, offset += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

function downsampleBuffer(buffer, inputSampleRate, outputSampleRate = 16000) {
  if (inputSampleRate === outputSampleRate) {
    return buffer;
  }
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  let offsetResult = 0;
  let offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
    let accum = 0, count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count > 0 ? (accum / count) : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}

async function toggleVoiceInputUniversal(textareaId, btnId, panelId, statusId, meterId, fillId, previewId) {
  const btn = document.getElementById(btnId);
  const textarea = document.getElementById(textareaId);
  const panel = document.getElementById(panelId);
  const status = document.getElementById(statusId);
  const preview = document.getElementById(previewId);

  // If already recording, stop & finalize!
  if (isUniversalRecording) {
    await stopUniversalRecordingAndTranscribe();
    return;
  }

  // Cancel any TTS audio playing in background
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    setAvatarSpeaking(false);
  }

  universalTextareaId = textareaId;
  universalBtnId = btnId;
  universalPanelId = panelId;
  universalStatusId = statusId;
  universalPreviewId = previewId;
  universalBaseText = textarea ? textarea.value.trim() : "";
  universalWebSpeechGotText = false;
  universalSpeechAccumulated = "";
  universalLiveStreamGotText = false;
  universalLiveStreamAccumulated = "";
  universalPCMChunks = [];
  isUniversalRecording = true;

  // 1. Update UI IMMEDIATELY so button is visibly functional
  if (btn) {
    if (btnId === "btn-speech-b") {
      btn.innerText = "⏹️ Finish Speaking (Auto-Sends to AI)";
    } else {
      btn.innerText = "⏹️ Done Speaking (Click to Finish)";
    }
    btn.className = "btn btn-danger btn-sm";
  }
  if (panel) panel.classList.add("recording");
  if (status) {
    if (textareaId === "b-answer") {
      status.innerHTML = "🔴 <strong>Listening to your answer... Transcribing live as you speak!</strong>";
    } else {
      status.innerHTML = "🔴 <strong>Recording Audio (00:00)... Transcribing live as you speak!</strong>";
    }
  }

  universalStartTime = Date.now();
  universalTimerInterval = setInterval(() => {
    if (!isUniversalRecording) return;
    const elapsedSec = Math.floor((Date.now() - universalStartTime) / 1000);
    const mm = String(Math.floor(elapsedSec / 60)).padStart(2, "0");
    const ss = String(elapsedSec % 60).padStart(2, "0");

    if (status) {
      if (!universalLiveStreamGotText && !universalWebSpeechGotText) {
        status.innerHTML = `🔴 <strong>Recording & Transcribing Live (${mm}:${ss})... Speak answer now</strong>`;
      }
    }
  }, 100);

  // 2. LAYER A: Web Speech API (Client-side native streaming)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    try {
      if (universalRecognition) {
        try { universalRecognition.abort(); } catch (e) {}
      }
      universalRecognition = new SpeechRecognition();
      universalRecognition.continuous = true;
      universalRecognition.interimResults = true;
      universalRecognition.lang = navigator.language || "en-US";
      universalRecognition.maxAlternatives = 1;

      universalRecognition.onresult = (event) => {
        let interimBatch = "";
        let finalBatch = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item && item[0]) {
            const txt = item[0].transcript;
            if (item.isFinal) {
              finalBatch += txt + " ";
            } else {
              interimBatch += txt;
            }
          }
        }

        if (finalBatch) {
          universalSpeechAccumulated += finalBatch;
        }

        const totalSpoken = (universalSpeechAccumulated + interimBatch).trim();
        if (totalSpoken) {
          universalWebSpeechGotText = true;
          if (textarea) {
            textarea.value = (universalBaseText ? universalBaseText + " " : "") + totalSpoken;
            textarea.dispatchEvent(new Event("input"));
          }
          if (preview) {
            preview.innerText = `“${interimBatch || totalSpoken}”`;
            preview.classList.add("active");
          }
          if (status) {
            status.innerHTML = `🗣️ <strong>Speaking:</strong> ${(interimBatch || totalSpoken).slice(-45)}`;
          }
          checkSimSilenceAutoForward(totalSpoken, universalTextareaId, status);
        }
      };

      universalRecognition.onerror = (e) => {
        console.warn("Web Speech API note (resilient fallback active):", e.error);
      };

      universalRecognition.start();
    } catch (wsErr) {
      console.warn("Web Speech start note:", wsErr);
    }
  }

  // 3. LAYER B: Live Streaming Full-Duplex WebSocket STT (Vosk Concurrent Transcriber)
  try {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${proto}//${window.location.host}/api/ws/transcribe`;
    universalWebSocket = new WebSocket(wsUrl);
    universalWebSocket.binaryType = "arraybuffer";

    universalWebSocket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "partial" || msg.type === "final") {
          const text = (msg.accumulated || msg.text || "").trim();
          if (text) {
            universalLiveStreamGotText = true;
            universalLiveStreamAccumulated = text;
            // If Web Speech API is not providing text or Vosk has more text, update UI directly
            if (!universalWebSpeechGotText || text.length >= (universalSpeechAccumulated || "").length) {
              if (textarea) {
                textarea.value = (universalBaseText ? universalBaseText + " " : "") + text;
                textarea.dispatchEvent(new Event("input"));
              }
              if (preview) {
                preview.innerText = `“${text}”`;
                preview.classList.add("active");
              }
              if (status) {
                status.innerHTML = `🗣️ <strong>Transcribing Live:</strong> ${escapeHtml(text.slice(-45))}`;
              }
              checkSimSilenceAutoForward(text, universalTextareaId, status);
            }
          }
        } else if (msg.type === "complete") {
          const text = (msg.text || "").trim();
          if (text) {
            universalLiveStreamGotText = true;
            universalLiveStreamAccumulated = text;
            if (textarea) {
              const base = universalBaseText ? universalBaseText + " " : "";
              if (!universalWebSpeechGotText || text.length >= textarea.value.length) {
                textarea.value = base + text;
                textarea.dispatchEvent(new Event("input"));
              }
            }
          }
        }
      } catch (err) {
        console.warn("WebSocket parse notice:", err);
      }
    };

    universalWebSocket.onerror = (err) => {
      console.warn("Live WebSocket STT notice:", err);
    };
  } catch (wsConnErr) {
    console.warn("WebSocket connect notice:", wsConnErr);
  }

  // 4. LAYER C: 100% Reliable Web Audio API buffer capture & frame streaming
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });

    universalMicStream = stream;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    universalAudioCtx = new AudioContextClass();

    const source = universalAudioCtx.createMediaStreamSource(stream);
    universalAnalyser = universalAudioCtx.createAnalyser();
    universalAnalyser.fftSize = 512;

    universalScriptProcessor = universalAudioCtx.createScriptProcessor(4096, 1, 1);
    const audioContextSampleRate = universalAudioCtx.sampleRate;

    universalScriptProcessor.onaudioprocess = (e) => {
      if (!isUniversalRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      universalPCMChunks.push(new Float32Array(inputData));

      // Stream concurrently to backend Speech-to-Text converter during recording
      if (universalWebSocket && universalWebSocket.readyState === WebSocket.OPEN) {
        try {
          const chunk16k = downsampleChunkTo16k(inputData, audioContextSampleRate);
          const pcm16 = floatTo16BitPCM(chunk16k);
          universalWebSocket.send(pcm16.buffer);
        } catch (wsSendErr) {
          console.warn("Live STT stream send note:", wsSendErr);
        }
      }
    };

    source.connect(universalAnalyser);
    universalAnalyser.connect(universalScriptProcessor);
    universalScriptProcessor.connect(universalAudioCtx.destination);

  } catch (micErr) {
    console.error("Microphone access error:", micErr);
    if (!universalWebSpeechGotText && !universalLiveStreamGotText) {
      if (status) {
        status.innerHTML = "❌ <strong>Microphone Permission Blocked:</strong> Click the lock/camera icon in your URL address bar to Allow microphone.";
      }
      resetUniversalUI();
    }
  }
}

async function stopUniversalRecordingAndTranscribe() {
  if (!isUniversalRecording) return;
  isUniversalRecording = false;

  if (universalTimerInterval) {
    clearInterval(universalTimerInterval);
    universalTimerInterval = null;
  }

  const textarea = document.getElementById(universalTextareaId);
  const status = document.getElementById(universalStatusId);
  const targetTextareaId = universalTextareaId;

  if (simSilenceTimer) {
    clearTimeout(simSilenceTimer);
    simSilenceTimer = null;
  }
  if (simSilenceCountdownTimer) {
    clearInterval(simSilenceCountdownTimer);
    simSilenceCountdownTimer = null;
  }

  // 1. Finalize WebSocket streaming STT if open
  if (universalWebSocket && universalWebSocket.readyState === WebSocket.OPEN) {
    try {
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 300);
        universalWebSocket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "complete" && data.text) {
              universalLiveStreamGotText = true;
              universalLiveStreamAccumulated = data.text;
              if (textarea) {
                const base = universalBaseText ? universalBaseText + " " : "";
                if (!universalWebSpeechGotText || data.text.length >= textarea.value.length) {
                  textarea.value = base + data.text;
                  textarea.dispatchEvent(new Event("input"));
                }
              }
            }
          } catch (e) {}
          clearTimeout(timer);
          resolve();
        };
        universalWebSocket.send(JSON.stringify({ action: "finish" }));
      });
    } catch (wsCloseErr) {
      console.warn("WS finish note:", wsCloseErr);
    }
    try { universalWebSocket.close(); } catch (e) {}
    universalWebSocket = null;
  }

  // Stop Web Speech recognition if active
  if (universalRecognition) {
    try { universalRecognition.stop(); } catch (e) {}
  }

  // Stop media stream tracks
  if (universalMicStream) {
    universalMicStream.getTracks().forEach(t => t.stop());
    universalMicStream = null;
  }

  const sampleRate = universalAudioCtx ? universalAudioCtx.sampleRate : 44100;

  if (universalScriptProcessor) {
    universalScriptProcessor.disconnect();
    universalScriptProcessor = null;
  }
  if (universalAnalyser) {
    universalAnalyser.disconnect();
    universalAnalyser = null;
  }
  if (universalAudioCtx) {
    try { await universalAudioCtx.close(); } catch (e) {}
    universalAudioCtx = null;
  }

  // Case 1: Speech-to-text converter ran concurrently during recording and captured words!
  const currentVal = textarea ? textarea.value.trim() : "";
  const gotLiveText = (universalLiveStreamGotText || universalWebSpeechGotText) && (currentVal.length > universalBaseText.length);

  if (gotLiveText) {
    if (status) {
      status.innerHTML = "✓ <strong>Voice Converted in Real-Time:</strong> Answer captured live with zero wait time!";
    }
    resetUniversalUI();
    // Real Interview Mode auto-forwarding directly to AI
    if (targetTextareaId === "b-answer") {
      if (status) status.innerHTML = "🚀 <strong>Auto-forwarding spoken response directly to Dr. Marcus Vance...</strong>";
      setTimeout(() => {
        submitSimulationAnswer();
      }, 350);
    }
    return;
  }

  // Case 2: Live streams yielded no text -> Fallback to full WAV upload
  if (status) {
    status.innerHTML = "⏳ <strong>Transcribing audio via speech engine...</strong>";
  }

  let totalLength = 0;
  for (let i = 0; i < universalPCMChunks.length; i++) {
    totalLength += universalPCMChunks[i].length;
  }

  if (totalLength < 1500) {
    if (status) {
      status.innerHTML = "⚠️ <strong>Recording too short:</strong> Please speak for at least 1-2 seconds.";
    }
    resetUniversalUI();
    return;
  }

  const mergedFloat32 = new Float32Array(totalLength);
  let offset = 0;
  for (let i = 0; i < universalPCMChunks.length; i++) {
    mergedFloat32.set(universalPCMChunks[i], offset);
    offset += universalPCMChunks[i].length;
  }

  const pcm16k = downsampleBuffer(mergedFloat32, sampleRate, 16000);
  const wavBlob = encodeWAV(pcm16k, 16000);

  const formData = new FormData();
  formData.append("audio", wavBlob, "speech_response.wav");

  try {
    const res = await fetch("/api/transcribe", {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    if (data && data.transcript && data.transcript.trim()) {
      const text = data.transcript.trim();
      if (textarea) {
        textarea.value = (universalBaseText ? universalBaseText + " " : "") + text;
        textarea.dispatchEvent(new Event("input"));
      }
      if (status) {
        status.innerHTML = `✓ <strong>Spoken Answer Transcribed:</strong> “${escapeHtml(text.slice(0, 70))}${text.length > 70 ? '...' : ''}”`;
      }
      resetUniversalUI();
      // Real Interview Mode auto-forwarding directly to AI
      if (targetTextareaId === "b-answer") {
        if (status) status.innerHTML = "🚀 <strong>Auto-forwarding spoken response directly to Dr. Marcus Vance...</strong>";
        setTimeout(() => {
          submitSimulationAnswer();
        }, 350);
      }
      return;
    } else {
      if (status) {
        status.innerHTML = "⚠️ <strong>No clear speech detected.</strong> Please speak closer to microphone or type directly.";
      }
    }
  } catch (err) {
    console.error("Transcribe API error:", err);
    if (status) {
      status.innerHTML = "⚠️ <strong>Transcription server notice:</strong> You may type your answer directly.";
    }
  }

  resetUniversalUI();
}

function resetUniversalUI() {
  if (universalBtnId) {
    const btn = document.getElementById(universalBtnId);
    if (btn) {
      if (universalBtnId === "btn-speech-b") {
        btn.innerText = "🎙️ Speak to Interviewer (Auto-Forwards)";
      } else {
        btn.innerText = "🎙️ Start Voice Input (Click to Speak)";
      }
      btn.className = "btn btn-primary btn-sm";
    }
  }
  if (universalPanelId) {
    const panel = document.getElementById(universalPanelId);
    if (panel) panel.classList.remove("recording");
  }
  if (universalPreviewId) {
    const preview = document.getElementById(universalPreviewId);
    if (preview) preview.classList.remove("active");
  }

  isUniversalRecording = false;
  universalPCMChunks = [];
}

function stopActiveRecognition() {
  if (isUniversalRecording) {
    stopUniversalRecordingAndTranscribe();
  }
}

// Map ALL possible aliases to the universal voice input engine
const toggleWebSpeech = toggleVoiceInputUniversal;
const toggleVoiceInput = toggleVoiceInputUniversal;
const toggleSimpleDictation = toggleVoiceInputUniversal;
const toggleAudioRecorder = toggleVoiceInputUniversal;
window.toggleVoiceInputUniversal = toggleVoiceInputUniversal;
window.toggleWebSpeech = toggleVoiceInputUniversal;
window.toggleVoiceInput = toggleVoiceInputUniversal;
window.toggleSimpleDictation = toggleVoiceInputUniversal;
window.toggleAudioRecorder = toggleVoiceInputUniversal;

// ==========================================
// 2B. REAL-TIME WEB SEARCH API ENGINE
// ==========================================
async function searchWebKnowledge(queryText = null) {
  const queryInput = document.getElementById("web-search-query");
  const query = queryText || (queryInput ? queryInput.value.trim() : "");
  const resultsContainer = document.getElementById("web-search-results");
  if (!query) {
    alert("Please enter a topic, company name, or interview question to search.");
    return;
  }

  if (resultsContainer) {
    resultsContainer.innerHTML = "<p style='color: var(--text-muted); font-size: 0.88rem;'>🔍 Searching Web Knowledge API...</p>";
  }

  try {
    const res = await fetch(`/api/web-search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (resultsContainer) {
      if (data.results && data.results.length > 0) {
        let html = `<h4 style='font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--primary);'>Web Knowledge Results for "${escapeHtml(data.query)}":</h4><ul style='padding-left: 1.25rem; font-size: 0.85rem; display: flex; flex-direction: column; gap: 0.5rem;'>`;
        data.results.forEach(r => {
          html += `<li><strong>${escapeHtml(r.title)}</strong><br><span style='color: #475569;'>${escapeHtml(r.snippet)}</span>${r.url ? ` <a href='${r.url}' target='_blank' style='color: #2563eb; font-size: 0.8rem; text-decoration: underline;'>[Source]</a>` : ''}</li>`;
        });
        html += "</ul>";
        resultsContainer.innerHTML = html;
      } else {
        resultsContainer.innerHTML = "<p style='color: var(--text-muted); font-size: 0.85rem;'>No web search results found.</p>";
      }
    }
  } catch (err) {
    console.error("Web Search API error:", err);
    if (resultsContainer) {
      resultsContainer.innerHTML = "<p style='color: #ef4444; font-size: 0.85rem;'>⚠️ Web search error. Please check internet connection.</p>";
    }
  }
}
window.searchWebKnowledge = searchWebKnowledge;

// Word counters
function setupWordCounters() {
  ["a-answer", "a-retry-answer", "b-answer"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", (e) => {
        const words = e.target.value.trim().split(/\s+/).filter(Boolean);
        const counterEl = document.getElementById(id === "a-answer" ? "a-word-count" : "");
        if (counterEl) counterEl.innerText = `${words.length} words`;
      });
    }
  });
}

// ==========================================
// 3. MAIN TAB ROUTER
// ==========================================
function switchMainTab(tab) {
  const pA = document.getElementById("nav-proto-a");
  const pB = document.getElementById("nav-proto-b");
  const pE = document.getElementById("nav-eval");
  const pR = document.getElementById("nav-research");
  if (pA) pA.classList.toggle("active", tab === "A");
  if (pB) pB.classList.toggle("active", tab === "B");
  if (pE) pE.classList.toggle("active", tab === "E");
  if (pR) pR.classList.toggle("active", tab === "R");

  const secA = document.getElementById("section-proto-a");
  const secB = document.getElementById("section-proto-b");
  const secE = document.getElementById("section-eval");
  const secR = document.getElementById("section-research");

  if (secA) secA.style.display = tab === "A" ? "block" : "none";
  if (secB) secB.style.display = tab === "B" ? "block" : "none";
  if (secE) secE.style.display = tab === "E" ? "block" : "none";
  if (secR) secR.style.display = tab === "R" ? "block" : "none";

  stopAllAudio();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Wireframe Mode Toggle
function toggleWireframeMode() {
  const isWireframe = document.body.classList.toggle("wireframe-mode");
  document.getElementById("wf-status").innerText = isWireframe ? "ON" : "OFF";
}

// ==========================================
// 3. CANDIDATE PROFILE & REAL INTERVIEW CONTEXT
// ==========================================
let candidateProfile = {
  name: "Candidate",
  role: "Software Engineer",
  company: "",
  level: "Mid-Level",
  interviewType: "Behavioral",
  difficulty: "Rigorous",
  cv: "",
  jd: ""
};

function syncCandidateName(val) {
  candidateProfile.name = val.trim() || "Candidate";
  const hName = document.getElementById("header-cand-name");
  if (hName) hName.innerText = candidateProfile.name;
  const ctxName = document.getElementById("ctx-name");
  if (ctxName) ctxName.innerText = candidateProfile.name;
  const a1Title = document.getElementById("a1-welcome-title");
  if (a1Title) a1Title.innerText = `👋 Welcome, ${candidateProfile.name}!`;
}

function syncCandidateRole(val) {
  candidateProfile.role = val.trim() || "Software Engineer";
  const hRole = document.getElementById("header-cand-role");
  if (hRole) hRole.innerText = candidateProfile.role;
  const ctxRole = document.getElementById("ctx-role");
  if (ctxRole) ctxRole.innerText = candidateProfile.role;
}

function syncCandidateCompany(val) {
  candidateProfile.company = val.trim();
  const ctxComp = document.getElementById("ctx-company");
  const ctxCompPill = document.getElementById("ctx-company-pill");
  if (ctxComp && ctxCompPill) {
    if (candidateProfile.company) {
      ctxComp.innerText = candidateProfile.company;
      ctxCompPill.style.display = "inline-flex";
    } else {
      ctxCompPill.style.display = "none";
    }
  }
}

function syncCandidateLevel(val) {
  candidateProfile.level = val;
  const ctxLevel = document.getElementById("ctx-level");
  if (ctxLevel) ctxLevel.innerText = val;
}

// User-defined presets for maximum convenience
function applyRolePresetA(role, company, level, type) {
  const rInput = document.getElementById("a-role");
  const cInput = document.getElementById("a-company");
  const lSelect = document.getElementById("a-level");
  const tSelect = document.getElementById("a-type");

  if (rInput) rInput.value = role;
  if (cInput) cInput.value = company;
  if (lSelect) lSelect.value = level;
  if (tSelect) tSelect.value = type;

  syncCandidateRole(role);
  syncCandidateCompany(company);
  syncCandidateLevel(level);

  goToScreenA("a2");
}

function setRoleFieldA(role) {
  const rInput = document.getElementById("a-role");
  if (rInput) {
    rInput.value = role;
    syncCandidateRole(role);
  }
}

function applyRolePresetB(role, company, level, difficulty) {
  const rInput = document.getElementById("b-role");
  const cInput = document.getElementById("b-company");
  const lSelect = document.getElementById("b-level");
  const dSelect = document.getElementById("b-difficulty");

  if (rInput) rInput.value = role;
  if (cInput) cInput.value = company;
  if (lSelect) lSelect.value = level;
  if (dSelect) dSelect.value = difficulty;

  syncCandidateRole(role);
  syncCandidateCompany(company);
  syncCandidateLevel(level);

  goToScreenB("b2");
}

function setRoleFieldB(role) {
  const rInput = document.getElementById("b-role");
  if (rInput) {
    rInput.value = role;
    syncCandidateRole(role);
  }
}

// Legacy persona-switch compatibility
function changePersona(personaId) {
  if (personaId === "aditi") {
    syncCandidateName("Aditi");
    syncCandidateRole("UX Research Intern");
  } else {
    syncCandidateName("Rahul");
    syncCandidateRole("Associate Product Manager");
  }
  loadLongitudinalProgress();
}

// ==========================================
// 4. PROTOTYPE A (LEARNING-ORIENTED FLOW)
// ==========================================
function goToScreenA(screenId) {
  const secA = document.getElementById("section-proto-a");
  if (secA && secA.style.display === "none") {
    switchMainTab("A");
  }
  const screens = ["screen-a1", "screen-a2", "screen-a3", "screen-a4", "screen-a6", "screen-a7", "screen-a8", "screen-a9"];
  screens.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === `screen-${screenId}`) ? "block" : "none";
  });
  stopAllAudio();
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (screenId === "a3" && autoSpeakEnabled) {
    setTimeout(speakCurrentQuestionA, 400);
  }
}

async function startSessionA() {
  const nameVal = document.getElementById("a-name") ? document.getElementById("a-name").value.trim() : "";
  const roleVal = document.getElementById("a-role") ? document.getElementById("a-role").value.trim() : "Software Engineer";
  const companyVal = document.getElementById("a-company") ? document.getElementById("a-company").value.trim() : "";
  const levelVal = document.getElementById("a-level") ? document.getElementById("a-level").value : "Mid-Level";
  const typeVal = document.getElementById("a-type") ? document.getElementById("a-type").value : "Behavioral";
  const diffVal = document.getElementById("a-difficulty") ? document.getElementById("a-difficulty").value : "Rigorous";
  const cvText = document.getElementById("a-cv") ? document.getElementById("a-cv").value.trim() : "";
  const jdText = document.getElementById("a-jd") ? document.getElementById("a-jd").value.trim() : "";

  syncCandidateName(nameVal);
  syncCandidateRole(roleVal);
  syncCandidateCompany(companyVal);
  syncCandidateLevel(levelVal);

  const startBtn = document.querySelector("#screen-a2 button.btn-primary");
  if (startBtn) {
    startBtn.disabled = true;
    startBtn.innerText = "⏳ Generating AI Questions with Nemotron 3.5...";
  }

  try {
    const res = await fetch("/api/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prototype_type: "A",
        candidate_name: candidateProfile.name,
        job_role: candidateProfile.role,
        target_company: candidateProfile.company,
        experience_level: candidateProfile.level,
        interview_type: typeVal,
        difficulty: diffVal,
        cv_text: cvText,
        job_description: jdText,
        persona_id: "custom"
      })
    });
    const data = await res.json();
    currentSessionId = data.session_id;

    if (data.first_question) {
      currentQuestionId = data.first_question.id;
      currentQuestionText = data.first_question.text;
      const qTextEl = document.getElementById("a3-q-text");
      if (qTextEl) qTextEl.innerText = `“${currentQuestionText}”`;
    }

    const dlDocx = document.getElementById("btn-dl-docx");
    const dlPptx = document.getElementById("btn-dl-pptx");
    if (dlDocx) dlDocx.href = `/api/export-docx/${currentSessionId}`;
    if (dlPptx) dlPptx.href = `/api/export-pptx/${currentSessionId}`;

    goToScreenA("a3");
  } catch (err) {
    console.error(err);
    currentSessionId = "sess_practice";
    goToScreenA("a3");
  } finally {
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.innerText = "🚀 Begin Practice Interview";
    }
  }
}

function speakCurrentQuestionA() {
  speakText(`Question: ${currentQuestionText}`, () => {
    const btn = document.getElementById("btn-read-a3");
    if (btn) btn.innerText = "🔊 Playing...";
  }, () => {
    const btn = document.getElementById("btn-read-a3");
    if (btn) btn.innerText = "🔊 Listen to Question";
  });
}

function speakFeedbackA4() {
  if (!lastEvaluation) return;
  const text = `Overall Score: ${lastEvaluation.overall_score} out of 10. Strengths: ${lastEvaluation.strengths.join(". ")}. Key recommendation: ${lastEvaluation.actionable_suggestions.join(". ")}`;
  speakText(text);
}

function loadSampleAnswerA(attemptNumber) {
  const textarea = attemptNumber === 1 ? document.getElementById("a-answer") : document.getElementById("a-retry-answer");
  if (!textarea) return;

  const role = (candidateProfile.role || "Software Engineer").toLowerCase();
  if (role.includes("ux") || role.includes("design") || role.includes("research")) {
    if (attemptNumber === 1) {
      textarea.value = "In my previous UX sprint, I had a disagreement with our engineer on the dashboard layout. The engineer wanted fewer filters to save loading time, while I wanted all filters visible. I scheduled a 30-minute sync to talk through user needs and we agreed on a compromise.";
    } else {
      textarea.value = "During our cross-functional sprint for the user dashboard, a lead engineer and I disagreed on whether to include an extensive filter menu or streamline it based on usability tests. Rather than escalating, I scheduled a 30-minute working session where I walked through recorded user testing clips showing that 4 out of 5 users were confused by excessive filters. I proposed an A/B test compromise with collapsible filters. As a concrete result, our engineering partner agreed, we shipped the feature 2 days ahead of deadline, and subsequent product analytics revealed a 28% higher task completion rate with zero user drop-offs.";
    }
  } else if (role.includes("product") || role.includes("apm") || role.includes("pm")) {
    if (attemptNumber === 1) {
      textarea.value = "During a feature planning cycle, engineering wanted to delay an analytics integration to refactor backend services. I explained the business priority and we agreed to split the work across two milestones.";
    } else {
      textarea.value = "During our mobile checkout redesign, our lead backend engineer wanted to defer Apple Pay integration to Q3 due to technical debt, but our user funnel showed 42% cart abandonments on mobile checkout. I organized a prioritization workshop, mapped out the engineering debt versus lost revenue, and proposed a phased rollout with minimal webhook refactoring. As a result, we reduced checkout drop-offs by 31% within 3 weeks and generated an estimated $140,000 in recovered monthly ARR.";
    }
  } else {
    // Software Engineer / General
    if (attemptNumber === 1) {
      textarea.value = "In our last sprint, we found a memory leak in the production caching tier right before a major release. I investigated the logs, found the offending circular reference, and created a quick hotfix that unblocked the release.";
    } else {
      textarea.value = "Forty-eight hours before our quarterly enterprise release, monitoring alerted us to a 35% memory spike under simulated 10k RPS load. Rather than blindly reverting commits, I ran profiling using pprof, identified an unbounded map cache in our auth middleware, and proposed an LRU cache with strict eviction limits. I paired with our reliability lead to benchmark the fix under 15k RPS, proving 0% packet drops and stable heap memory. As a measurable outcome, we deployed on schedule, reduced P99 latency from 180ms to 42ms, and prevented an estimated $85,000 SLA penalty.";
    }
  }
  textarea.dispatchEvent(new Event("input"));
}

async function submitAnswerA(attemptNumber) {
  const textarea = attemptNumber === 1 ? document.getElementById("a-answer") : document.getElementById("a-retry-answer");
  const answer = textarea.value.trim();

  if (!answer) {
    alert("Please provide or dictate an answer before submitting.");
    return;
  }

  stopActiveRecognition();
  const submitBtn = attemptNumber === 1 ? document.getElementById("btn-submit-a") : null;
  if (submitBtn) submitBtn.innerText = "Evaluating against rubric...";

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId || "demo_sess",
        question_id: currentQuestionId,
        question_text: currentQuestionText,
        answer_text: answer,
        attempt_number: attemptNumber
      })
    });
    const evalData = await res.json();
    lastEvaluation = evalData;

    if (attemptNumber === 1) {
      renderFeedbackScreenA4(evalData);
      goToScreenA("a4");
    } else {
      await loadAttemptComparison();
      goToScreenA("a8");
    }
  } catch (err) {
    console.error(err);
    alert("Evaluation error. Please try again.");
  } finally {
    if (submitBtn) submitBtn.innerText = "Submit Answer";
  }
}

function renderFeedbackScreenA4(evalData) {
  document.getElementById("a4-overall-score").innerText = `${evalData.overall_score} / 10`;

  // Criteria Scores
  document.getElementById("a4-rel-score").innerText = `${evalData.relevance.score}/10`;
  document.getElementById("a4-rel-reason").innerText = evalData.relevance.reason;

  document.getElementById("a4-spec-score").innerText = `${evalData.specificity.score}/10`;
  document.getElementById("a4-spec-reason").innerText = evalData.specificity.reason;

  document.getElementById("a4-evid-score").innerText = `${evalData.evidence_outcome.score}/10`;
  document.getElementById("a4-evid-reason").innerText = evalData.evidence_outcome.reason;

  document.getElementById("a4-struct-score").innerText = `${evalData.structure_clarity.score}/10`;
  document.getElementById("a4-struct-reason").innerText = evalData.structure_clarity.reason;

  // Strengths & Weaknesses
  const strList = document.getElementById("a4-strengths");
  strList.innerHTML = evalData.strengths.map(s => `<li>${s}</li>`).join("");

  const weakList = document.getElementById("a4-weaknesses");
  weakList.innerHTML = evalData.needs_improvement.map(w => `<li>${w}</li>`).join("");

  // Actionable suggestions
  document.getElementById("a4-suggestions").innerText = evalData.actionable_suggestions.join(" ");

  // Populate Why Modal
  document.getElementById("modal-why-score").innerText = `${evalData.evidence_outcome.score} / 10`;
  document.getElementById("modal-why-reason").innerText = evalData.evidence_outcome.reason;
  if (evalData.evidence_outcome.evidence_found) {
    document.getElementById("modal-why-excerpt").innerText = `Analyzed: “${evalData.evidence_outcome.evidence_found}”`;
  }
  if (evalData.example_improved_answer) {
    document.getElementById("modal-why-addition").innerText = evalData.example_improved_answer;
  }
}

function openWhyFeedbackModal() {
  document.getElementById("modal-why-feedback").style.display = "flex";
}

function closeWhyFeedbackModal() {
  document.getElementById("modal-why-feedback").style.display = "none";
}

function loadSampleReflectionA() {
  document.getElementById("a-change").value = "I would add the measurable user retention impact and exact A/B test metric to show a concrete resolution.";
  document.getElementById("a-learn").value = "In behavioral interviews, explaining actions isn't enough; I must explicitly state the quantifiable result (STAR Result).";
}

async function saveReflectionA() {
  const change = document.getElementById("a-change").value;
  const learn = document.getElementById("a-learn").value;

  try {
    await fetch("/api/reflect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId || "demo_sess",
        question_id: currentQuestionId,
        what_would_you_change: change,
        what_did_you_learn: learn
      })
    });
  } catch (e) {
    console.error(e);
  }
  goToScreenA("a7");
}

async function loadAttemptComparison() {
  try {
    const res = await fetch(`/api/compare?session_id=${currentSessionId || "demo_sess"}&question_id=${currentQuestionId}`, {
      method: "POST"
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Could not load attempt comparison.");
    }
    renderComparisonTable(data);
  } catch (err) {
    console.error(err);
    const tbody = document.getElementById("compare-tbody");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="4">${escapeHtml(err.message || "Could not load attempt comparison.")}</td></tr>`;
    }
  }
}

function renderComparisonTable(comp) {
  const tbody = document.getElementById("compare-tbody");
  tbody.innerHTML = `
    <tr>
      <td><strong>Relevance</strong></td>
      <td>${comp.attempt1_scores.relevance}/10</td>
      <td>${comp.attempt2_scores.relevance}/10</td>
      <td><span class="score-delta">+${comp.deltas.relevance}</span></td>
    </tr>
    <tr>
      <td><strong>Specificity</strong></td>
      <td>${comp.attempt1_scores.specificity}/10</td>
      <td>${comp.attempt2_scores.specificity}/10</td>
      <td><span class="score-delta">+${comp.deltas.specificity}</span></td>
    </tr>
    <tr>
      <td><strong>Evidence & Outcome (STAR)</strong></td>
      <td>${comp.attempt1_scores.evidence}/10</td>
      <td>${comp.attempt2_scores.evidence}/10</td>
      <td><span class="score-delta" style="color: #ea580c; font-weight: 800;">+${comp.deltas.evidence_outcome || comp.deltas.evidence} ★</span></td>
    </tr>
    <tr>
      <td><strong>Structure & Clarity</strong></td>
      <td>${comp.attempt1_scores.structure}/10</td>
      <td>${comp.attempt2_scores.structure}/10</td>
      <td><span class="score-delta">+${comp.deltas.structure_clarity || comp.deltas.structure}</span></td>
    </tr>
    <tr style="background-color: var(--primary-light);">
      <td><strong>Overall Rating</strong></td>
      <td><strong>${comp.attempt1_scores.overall}/10</strong></td>
      <td><strong>${comp.attempt2_scores.overall}/10</strong></td>
      <td><strong style="color: var(--primary); font-size: 1.1rem;">+${comp.deltas.overall}</strong></td>
    </tr>
  `;

  const impList = document.getElementById("compare-improvements");
  if (impList && comp.improvements) {
    impList.innerHTML = comp.improvements.map(i => `<li>${i}</li>`).join("");
  }
}

// Longitudinal Progress Chart
async function loadLongitudinalProgress() {
  try {
    const res = await fetch(`/api/progress?persona_id=${activePersona}`);
    const data = await res.json();

    const ctx = document.getElementById("progressChart");
    if (!ctx) return;

    const labels = data.trajectory.map(t => t.attempt_label);
    const overallScores = data.trajectory.map(t => t.overall_score);
    const evidenceScores = data.trajectory.map(t => t.evidence_score);

    if (progressChartInstance) {
      progressChartInstance.destroy();
    }

    progressChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Overall Score (0-10)",
            data: overallScores,
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.1)",
            tension: 0.3,
            fill: true,
            borderWidth: 3
          },
          {
            label: "Evidence & Outcome Score (0-10)",
            data: evidenceScores,
            borderColor: "#ea580c",
            backgroundColor: "transparent",
            borderDash: [5, 5],
            tension: 0.3,
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0,
            max: 10,
            title: { display: true, text: "Rubric Rating" }
          }
        }
      }
    });

    const wList = document.getElementById("prog-weaknesses");
    if (wList && data.profile.recurring_weaknesses) {
      wList.innerHTML = data.profile.recurring_weaknesses.map(w => `<li>${w}</li>`).join("");
    }

    const focusEl = document.getElementById("prog-focus");
    if (focusEl) {
      focusEl.innerText = `${data.current_focus_area}. ${data.action_advice}`;
    }

  } catch (err) {
    console.error("Progress fetch error:", err);
  }
}

// ==========================================
// 5. PROTOTYPE B (FULL REAL-TIME VOICE SIMULATION)
// ==========================================
let simConversationHistory = [];

function goToScreenB(screenId) {
  const secB = document.getElementById("section-proto-b");
  if (secB && secB.style.display === "none") {
    switchMainTab("B");
  }
  const screens = ["screen-b1", "screen-b2", "screen-b3", "screen-b6", "screen-b8"];
  screens.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === `screen-${screenId}`) ? "block" : "none";
  });
  stopAllAudio();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function startSessionB() {
  simulationTurn = 1;
  simConversationHistory = [];
  simTurnAnswers = {
    question1: "",
    turn1Answer: "",
    followupQuestion: "",
    turn2Answer: "",
    adaptiveTrigger: ""
  };

  const nameVal = document.getElementById("b-name") ? document.getElementById("b-name").value.trim() : "";
  const roleVal = document.getElementById("b-role") ? document.getElementById("b-role").value.trim() : "Software Engineer";
  const companyVal = document.getElementById("b-company") ? document.getElementById("b-company").value.trim() : "";
  const levelVal = document.getElementById("b-level") ? document.getElementById("b-level").value : "Mid-Level";
  const diffVal = document.getElementById("b-difficulty") ? document.getElementById("b-difficulty").value : "Rigorous";
  const cvText = document.getElementById("b-cv") ? document.getElementById("b-cv").value.trim() : "";
  const jdText = document.getElementById("b-jd") ? document.getElementById("b-jd").value.trim() : "";

  syncCandidateName(nameVal);
  syncCandidateRole(roleVal);
  syncCandidateCompany(companyVal);
  syncCandidateLevel(levelVal);

  const startBtnB = document.getElementById("btn-start-b") || document.querySelector("#screen-b2 button.btn-primary");
  const b2Notice = document.getElementById("b2-loading-notice");
  if (startBtnB) {
    startBtnB.disabled = true;
    startBtnB.innerText = "⏳ Initializing Simulation Room...";
  }
  if (b2Notice) {
    b2Notice.style.display = "flex";
  }

  const companyRef = candidateProfile.company ? ` at ${candidateProfile.company}` : "";
  let initialQuestion = `Good morning, ${candidateProfile.name}! Welcome to your official mock interview for the ${candidateProfile.role} position${companyRef}. I'm Dr. Marcus Vance, lead hiring evaluator for the team today. Thanks for taking the time to join me. To kick off our conversation, could you please introduce yourself, walk me through your background, and share what brings you to this role?`;

  try {
    const res = await fetch("/api/setup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prototype_type: "B",
        candidate_name: candidateProfile.name,
        job_role: candidateProfile.role,
        target_company: candidateProfile.company,
        experience_level: candidateProfile.level,
        interview_type: "Behavioral & Technical",
        difficulty: diffVal,
        cv_text: cvText,
        job_description: jdText,
        persona_id: "custom"
      })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    if (data.first_question && data.first_question.text) {
      initialQuestion = data.first_question.text;
      currentQuestionId = data.first_question.id;
      currentQuestionText = data.first_question.text;
    }
  } catch (e) {
    console.warn("Simulation setup notice:", e);
  } finally {
    if (startBtnB) {
      startBtnB.disabled = false;
      startBtnB.innerText = "🎙️ Begin Voice Simulation";
    }
    if (b2Notice) {
      b2Notice.style.display = "none";
    }
  }

  currentQuestionText = initialQuestion;
  simTurnAnswers.question1 = initialQuestion;
  simConversationHistory.push({ role: "assistant", content: initialQuestion });

  const chat = document.getElementById("b-chat-container");
  chat.innerHTML = `
    <div class="chat-bubble interviewer">
      <div class="chat-meta">DR. MARCUS VANCE • OFFICIAL INTERVIEW (STAGE 1: INTRODUCTION)</div>
      <p id="b-q1-text">“${escapeHtml(initialQuestion)}”</p>
      <div style="margin-top: 0.4rem;">
        <button class="btn btn-secondary btn-sm" onclick="speakText('${escapeHtml(initialQuestion).replace(/["“”]/g, '')}')">🔊 Hear Audio</button>
      </div>
    </div>
  `;
  document.getElementById("sim-status-badge").innerText = "Stage 1: Introduction & Background";
  const histPillStart = document.getElementById("sim-history-pill");
  if (histPillStart) histPillStart.innerHTML = "🧠 History Buffer: <strong>Ready (Stage 1)</strong>";
  document.getElementById("b-answer").value = "";
  goToScreenB("b3");

  if (autoSpeakEnabled) {
    setTimeout(() => {
      speakText(initialQuestion);
    }, 500);
  }
}

function loadSampleAnswerB() {
  const ta = document.getElementById("b-answer");
  if (!ta) return;
  const role = (candidateProfile.role || "Software Engineer").toLowerCase();
  const name = candidateProfile.name || "Candidate";

  if (simulationTurn === 1) {
    // Stage 1: Authentic Self-Introduction
    if (role.includes("product") || role.includes("apm")) {
      ta.value = `Good morning Dr. Vance! I'm ${name}. Over the past 3 years as an Associate Product Manager, I've driven user onboarding optimization and checkout funnel improvements. I specialize in turning user friction into prioritized engineering roadmaps, and I'm excited about this opportunity to scale our core product offerings.`;
    } else if (role.includes("ux") || role.includes("design")) {
      ta.value = `Good morning Dr. Vance! I'm ${name}. I'm a UX Researcher with a background in cognitive human-computer interaction and mixed-methods research. I specialize in translating qualitative field studies and usability metrics into validated product features.`;
    } else {
      ta.value = `Good morning Dr. Vance! I'm ${name}. For the past 4 years I've worked as a backend software engineer specializing in distributed systems, microservices decoupling, and high-throughput data pipelines. I'm really excited about this role because I love building resilient architectures that handle mission-critical scale.`;
    }
  } else if (simulationTurn === 2) {
    // Stage 2: Technical Project Deep Dive
    if (role.includes("product") || role.includes("apm")) {
      ta.value = "In our checkout redesign sprint, our engineering lead wanted to defer Apple Pay integration due to technical debt, but our funnel data showed 42% cart abandonments on mobile. I organized an emergency trade-off workshop, quantified engineering debt against lost revenue, and designed a phased rollout that recovered 31% in checkout completion within three weeks.";
    } else if (role.includes("ux") || role.includes("design")) {
      ta.value = "During our enterprise filter redesign, engineers wanted to remove secondary filters to optimize query performance, while user research showed 4 of 5 participants relied on them. I created annotated usability clips demonstrating navigational failure, and negotiated a collapsible accordion filter pattern that achieved 100% task completion with cached subqueries.";
    } else {
      ta.value = "When our transaction volume spiked by 4x, our payment ledger faced cross-region consensus bottlenecks. I led the migration from a legacy single-instance Postgres lock to a distributed Raft consensus pattern for lease management combined with a two-phase commit, reducing end-to-end commit latency from 450ms down to 42ms with zero data inconsistency.";
    }
  } else if (simulationTurn === 3) {
    // Stage 3: Behavioral, Conflict & Trade-Offs
    if (role.includes("product") || role.includes("apm")) {
      ta.value = "We had a sharp disagreement when our VP of Sales wanted a custom feature for a single enterprise client that threatened our quarterly roadmap. I scheduled an alignment session, built an impact vs effort matrix, and created a configurable feature toggle that satisfied the client without derailing the core platform timeline.";
    } else if (role.includes("ux") || role.includes("design")) {
      ta.value = "Our engineering lead wanted to bypass user validation on a redesigned dashboard to meet an aggressive deadline. I proposed an asynchronous unmoderated usability test running in parallel over 48 hours, presented high-priority usability blockers with zero delay to the release schedule, and won the entire team's buy-in.";
    } else {
      ta.value = "Our tech lead insisted on sticking with REST endpoints while I advocated for gRPC internally. Instead of engaging in an ideological debate, I built a quick benchmark harness measuring payload serialization and CPU overhead across 10,000 requests. The data showed gRPC had 3.4x higher throughput and 65% lower CPU usage, which convinced the lead and united the team.";
    }
  } else {
    // Stage 4: Outcomes & Verification
    ta.value = "We tracked the deployment across 90 days. The system maintained 99.995% uptime during our peak Black Friday rush, handling 18,000 transactions per second without a single failover incident. The key lesson I took away was that providing automated telemetry dashboards upfront eliminates subjective debates and aligns cross-functional teams much faster.";
  }
  ta.dispatchEvent(new Event("input"));
}
const loadSampleRahulAnswer = loadSampleAnswerB;
window.loadSampleAnswerB = loadSampleAnswerB;
window.loadSampleRahulAnswer = loadSampleAnswerB;

async function submitSimulationAnswer() {
  const answer = document.getElementById("b-answer").value.trim();
  if (!answer) {
    alert("Please speak or type an answer to continue.");
    return;
  }

  stopActiveRecognition();
  const chat = document.getElementById("b-chat-container");

  // Append candidate response
  chat.innerHTML += `
    <div class="chat-bubble candidate">
      <div class="chat-meta">${escapeHtml(candidateProfile.name || 'YOU').toUpperCase()} (CANDIDATE)</div>
      <p>${escapeHtml(answer)}</p>
    </div>
  `;
  document.getElementById("b-answer").value = "";
  chat.scrollTop = chat.scrollHeight;

  // Add candidate input to local dialogue history
  simConversationHistory.push({ role: "user", content: answer });

  if (simulationTurn === 1) {
    simTurnAnswers.turn1Answer = answer;
  } else if (simulationTurn === 2) {
    simTurnAnswers.turn2Answer = answer;
  }

  // Set hero status to thinking
  const b3Status = document.getElementById("b3-voice-status");
  if (b3Status) {
    b3Status.className = "voice-status-pill thinking";
    b3Status.innerText = "🧠 Interviewer Actively Listening...";
  }

  // Add animated typing indicator inside chat stream
  const typingBubbleHtml = `
    <div class="chat-bubble interviewer typing-bubble" id="b-typing-bubble">
      <div class="chat-meta">DR. MARCUS VANCE • OFFICIAL INTERVIEWER</div>
      <div style="display: flex; align-items: center; gap: 0.6rem; color: #475569; font-size: 0.88rem;">
        <div class="typing-dots"><span></span><span></span><span></span></div>
        <span>Dr. Vance is listening and formulating the next question...</span>
      </div>
    </div>
  `;
  chat.innerHTML += typingBubbleHtml;
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch("/api/interview/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId || "sess_sim",
        user_message: answer,
        turn_index: simulationTurn,
        job_role: candidateProfile.role || "Software Engineer",
        conversation_history: simConversationHistory
      })
    });
    const data = await res.json();

    // Remove typing indicator
    const tb = document.getElementById("b-typing-bubble");
    if (tb) tb.remove();

    const reply = data.interviewer_message || data.followup_question || "Could you tell me more about that?";
    simConversationHistory.push({ role: "assistant", content: reply });
    simulationTurn = data.turn_index || (simulationTurn + 1);

    if (b3Status) {
      b3Status.className = "voice-status-pill speaking";
      b3Status.innerText = "🔊 Interviewer Speaking";
    }

    const stageNames = {
      2: "STAGE 2: TECHNICAL & PROJECT PROBE",
      3: "STAGE 3: BEHAVIORAL & CONFLICT RESOLUTION",
      4: "STAGE 4: MEASURED IMPACT & REFLECTION",
      5: "STAGE 5: INTERVIEW CONCLUSION"
    };
    const stageBadgeNames = {
      2: "Stage 2: Technical Deep Dive",
      3: "Stage 3: Behavioral & Conflict",
      4: "Stage 4: Measured Impact & Reflection",
      5: "Completed • Rubric Evaluation"
    };

    const stageTitle = stageNames[simulationTurn] || `STAGE ${simulationTurn}: INTERVIEW PROBE`;
    const badgeTitle = stageBadgeNames[simulationTurn] || `Stage ${simulationTurn}`;
    const badge = document.getElementById("sim-status-badge");
    if (badge) badge.innerText = badgeTitle;

    const histPill = document.getElementById("sim-history-pill");
    if (histPill) {
      const turnsCount = Math.floor(simConversationHistory.length / 2);
      histPill.innerHTML = `🧠 History Buffer: <strong>${turnsCount} ${turnsCount === 1 ? 'exchange' : 'exchanges'} active</strong>`;
    }

    chat.innerHTML += `
      <div class="chat-bubble interviewer">
        <div class="chat-meta">DR. MARCUS VANCE • OFFICIAL INTERVIEW (${stageTitle})</div>
        <p>${escapeHtml(reply)}</p>
        <div style="margin-top: 0.4rem;">
          <button class="btn btn-secondary btn-sm" onclick="speakText('${escapeHtml(reply).replace(/["“”]/g, '')}')">🔊 Hear Audio</button>
        </div>
      </div>
    `;
    chat.scrollTop = chat.scrollHeight;

    if (autoSpeakEnabled) {
      speakText(reply);
    }

    // If the interview reaches conclusion, transition to final rubric evaluation
    if (data.is_concluded || simulationTurn > 4) {
      setTimeout(() => {
        finishSimulation();
      }, 4000);
    }

  } catch (err) {
    console.error("Turn fetch error:", err);
    const tb = document.getElementById("b-typing-bubble");
    if (tb) tb.remove();
    finishSimulation(answer);
  }
}

let simLastEvaluation = null;

async function finishSimulation(lastAnswerText = "") {
  if (lastAnswerText && (!simConversationHistory.length || simConversationHistory[simConversationHistory.length - 1].content !== lastAnswerText)) {
    simConversationHistory.push({ role: "user", content: lastAnswerText });
  }

  const badge = document.getElementById("sim-status-badge");
  if (badge) badge.innerText = "Completed • Comprehensive Rubric Evaluation";

  goToScreenB("b6");

  // Reset Screen B6 to clear loading state
  const bFinal = document.getElementById("b-final-score");
  if (bFinal) bFinal.innerText = "⏳ Evaluating...";
  const bSummary = document.getElementById("b-overall-summary");
  if (bSummary) bSummary.innerHTML = "Overall Performance: <strong>Evaluating complete interview dialogue against rubric...</strong>";
  const bStrengths = document.getElementById("b-strengths-summary");
  if (bStrengths) bStrengths.innerText = "Analyzing interview strengths...";
  const bFocus = document.getElementById("b-focus-summary");
  if (bFocus) bFocus.innerText = "Identifying priority areas for improvement...";

  const b8List = document.getElementById("b8-detailed-list");
  if (b8List) {
    b8List.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);"><div class="typing-dots" style="margin-bottom: 0.5rem;"><span></span><span></span><span></span></div><br>Generating Comprehensive Multi-Turn AI Rubric Evaluation using NVIDIA Nemotron 3.5...</div>`;
  }

  // Synthesize complete multi-turn conversation
  const fullTranscript = simConversationHistory.map(m => {
    const speaker = m.role === "assistant" ? "DR. MARCUS VANCE (INTERVIEWER)" : `${candidateProfile.name || 'CANDIDATE'}`;
    return `[${speaker}]:\n${m.content}`;
  }).join("\n\n");

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId || "sess_sim",
        question_id: currentQuestionId || 1,
        question_text: `Official Mock Interview for ${candidateProfile.role} with Dr. Marcus Vance`,
        answer_text: fullTranscript || "Candidate completed official mock interview.",
        attempt_number: 1
      })
    });
    const data = await res.json();
    simLastEvaluation = data;
    renderDetailedSimulationFeedback(data);
  } catch (err) {
    console.warn("Simulation evaluation notice:", err);
    renderDetailedSimulationFeedback(null);
  }
}

function renderDetailedSimulationFeedback(evalData = null) {
  const container = document.getElementById("b8-detailed-list");
  if (!container) return;

  if (evalData && evalData.overall_score) {
    const rel = evalData.relevance ? evalData.relevance.score : 8.0;
    const spec = evalData.specificity ? evalData.specificity.score : 7.5;
    const evid = evalData.evidence_outcome ? evalData.evidence_outcome.score : 7.0;
    const struct = evalData.structure_clarity ? evalData.structure_clarity.score : 8.0;
    const overall = evalData.overall_score || 7.5;

    // Update Screen B6 overall banner
    const bFinal = document.getElementById("b-final-score");
    if (bFinal) bFinal.innerText = `${overall.toFixed(1)} / 10`;
    
    const bSummary = document.getElementById("b-overall-summary");
    if (bSummary) {
      bSummary.innerHTML = `Overall Performance: <strong>${escapeHtml(evalData.summary || 'Strong Competency Alignment')}</strong>`;
    }

    const bStrengths = document.getElementById("b-strengths-summary");
    if (bStrengths && evalData.strengths && evalData.strengths.length) {
      bStrengths.innerText = evalData.strengths.slice(0, 3).join(" • ");
    }

    const bFocus = document.getElementById("b-focus-summary");
    if (bFocus && evalData.needs_improvement && evalData.needs_improvement.length) {
      bFocus.innerText = evalData.needs_improvement.slice(0, 2).join(" • ");
    }

    let strengthsHtml = (evalData.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("");
    let weakHtml = (evalData.needs_improvement || []).map(w => `<li>${escapeHtml(w)}</li>`).join("");

    // Build turn-by-turn dialogue inspection
    let dialogueHtml = simConversationHistory.map((m, idx) => {
      const isAI = m.role === "assistant";
      return `
        <div style="margin-bottom: 0.6rem; padding: 0.6rem 0.85rem; border-radius: 6px; background: ${isAI ? '#f1f5f9' : '#eff6ff'}; border-left: 3px solid ${isAI ? 'var(--primary)' : '#6366f1'};">
          <div style="font-size: 0.75rem; font-weight: 700; color: ${isAI ? 'var(--primary)' : '#4338ca'};">${isAI ? 'DR. MARCUS VANCE (INTERVIEWER)' : `${escapeHtml(candidateProfile.name || 'YOU')}`} • TURN ${Math.floor(idx / 2) + 1}</div>
          <p style="margin: 0.2rem 0 0 0; font-size: 0.85rem; color: #334155;">${escapeHtml(m.content)}</p>
        </div>
      `;
    }).join("");

    container.innerHTML = `
      <div style="border: 1px solid var(--border); padding: 1.25rem; border-radius: 8px; margin-bottom: 1.25rem; background: #fff;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
          <h4 style="margin: 0; color: var(--text-main);">Official Interview Evaluation: ${escapeHtml(candidateProfile.role)}</h4>
          <span class="badge badge-success" style="font-size: 0.95rem;">Overall: ${overall.toFixed(1)} / 10</span>
        </div>
        
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem;">
          Relevance: <strong>${rel}/10</strong> • Specificity: <strong>${spec}/10</strong> • Evidence/Outcome: <strong>${evid}/10</strong> • Structure: <strong>${struct}/10</strong>
        </p>

        <!-- Conversational Transcript Review -->
        <div style="margin-top: 1rem; border-top: 1px solid #e2e8f0; padding-top: 0.85rem;">
          <div style="font-size: 0.82rem; font-weight: 700; color: #475569; margin-bottom: 0.5rem;">💬 FULL INTERVIEW TRANSCRIPT & DIALOGUE:</div>
          <div style="max-height: 280px; overflow-y: auto; padding: 0.5rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;">
            ${dialogueHtml || '<p style="color: var(--text-muted); font-size: 0.85rem;">Transcript recorded.</p>'}
          </div>
        </div>

        <div style="margin-top: 0.85rem; font-size: 0.85rem; background-color: var(--primary-light); padding: 0.75rem; border-radius: 6px;">
          <strong>Audit Rationale:</strong> ${escapeHtml(evalData.relevance ? evalData.relevance.reason : 'Candidate demonstrated clear alignment with role competencies.')}
        </div>
        ${strengthsHtml ? `<div style="margin-top: 0.75rem; font-size: 0.85rem; color: #065f46;"><strong>✓ Key Strengths:</strong><ul style="margin: 0.25rem 0 0 1.2rem;">${strengthsHtml}</ul></div>` : ''}
        ${weakHtml ? `<div style="margin-top: 0.75rem; font-size: 0.85rem; color: #9a3412;"><strong>⚠️ Probed Growth Areas:</strong><ul style="margin: 0.25rem 0 0 1.2rem;">${weakHtml}</ul></div>` : ''}
      </div>
    `;
    return;
  }

  // Fallback if offline
  const bFinal = document.getElementById("b-final-score");
  if (bFinal) bFinal.innerText = "7.8 / 10";
  const bSummary = document.getElementById("b-overall-summary");
  if (bSummary) bSummary.innerHTML = "Overall Performance: <strong>Structured Technical Framing with Opportunity for Metric Evidence</strong>";

  container.innerHTML = `
    <div style="border: 1px solid var(--border); padding: 1.25rem; border-radius: 8px; margin-bottom: 1rem; background: #fff;">
      <div style="display: flex; justify-content: space-between; align-items: baseline;">
        <h4>Official Interview Evaluation</h4>
        <span class="badge badge-success">Overall: 7.8 / 10</span>
      </div>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.35rem;">
        Relevance: 8.5/10 • Specificity: 8.0/10 • <strong>Evidence/Outcome: 6.5/10</strong> • Structure: 8.0/10
      </p>
      <div style="margin-top: 0.75rem; font-size: 0.85rem; background-color: var(--primary-light); padding: 0.75rem; border-radius: 6px;">
        <strong>Audit Rationale:</strong> Candidate outlined the business and technical trade-off clearly. Follow STAR framework with quantifiable metrics for optimal results.
      </div>
    </div>
  `;
}

// ==========================================
// 6. CS 435 USER EVALUATION & ETHICS MODULE
// ==========================================
function startEvalTimer() {
  if (evalTimerInterval) clearInterval(evalTimerInterval);
  evalTimerSeconds = 0;
  evalTimerStarted = true;
  evalTimerInterval = setInterval(() => {
    evalTimerSeconds++;
    const m = String(Math.floor(evalTimerSeconds / 60)).padStart(2, '0');
    const s = String(evalTimerSeconds % 60).padStart(2, '0');
    const disp = document.getElementById("eval-timer-display");
    if (disp) disp.innerText = `${m}:${s}`;
  }, 1000);
}

function stopEvalTimer() {
  if (evalTimerInterval) {
    clearInterval(evalTimerInterval);
    evalTimerInterval = null;
  }
}

function setupSusListeners() {
  for (let i = 1; i <= 10; i++) {
    const radios = document.getElementsByName(`sus_q${i}`);
    radios.forEach(r => r.addEventListener("change", calculateLiveSusScore));
  }
}

function calculateLiveSusScore() {
  let oddSum = 0;
  let evenSum = 0;
  let allAnswered = true;

  for (let i = 1; i <= 10; i++) {
    const selected = document.querySelector(`input[name="sus_q${i}"]:checked`);
    if (!selected) {
      allAnswered = false;
      continue;
    }
    const val = parseInt(selected.value, 10);
    if (i % 2 === 1) {
      // Odd items (positive): score - 1
      oddSum += (val - 1);
    } else {
      // Even items (negative): 5 - score
      evenSum += (5 - val);
    }
  }

  const rawScore = (oddSum + evenSum) * 2.5;
  const scoreDisplay = document.getElementById("sus-score-display");
  const gradeBadge = document.getElementById("sus-grade-badge");

  if (scoreDisplay) scoreDisplay.innerText = `${rawScore.toFixed(1)} / 100`;

  if (gradeBadge) {
    if (rawScore >= 85) {
      gradeBadge.className = "badge badge-success";
      gradeBadge.innerText = "Grade: A+ (Exceptional Usability)";
    } else if (rawScore >= 75) {
      gradeBadge.className = "badge badge-success";
      gradeBadge.innerText = "Grade: A (Good Usability)";
    } else if (rawScore >= 68) {
      gradeBadge.className = "badge badge-warning";
      gradeBadge.innerText = "Grade: C (Average Usability - Benchmark: 68.0)";
    } else {
      gradeBadge.className = "badge badge-danger";
      gradeBadge.innerText = "Grade: Marginal / Needs Improvement";
    }
  }

  return rawScore;
}

function loadSampleEvaluationP01() {
  document.getElementById("eval-participant-id").value = "P01";
  document.getElementById("eval-target-role").value = "UX Research Intern";
  document.getElementById("eval-prototype-tested").value = "Both";
  document.getElementById("eval-notes-realism").value = "Voice interaction made the simulation feel like a live interview. Adaptive follow-up challenged my initial vague answer.";
  document.getElementById("eval-notes-learning").value = "The 'Why this feedback' screen made it completely clear why I lost points on Evidence. The side-by-side retry comparison showed my concrete +4.0 score delta.";
  [5, 1, 5, 1, 5, 1, 5, 1, 5, 1].forEach((value, index) => {
    const response = document.querySelector(`input[name="sus_q${index + 1}"][value="${value}"]`);
    if (response) response.checked = true;
  });
  calculateLiveSusScore();
}

async function submitUserEvaluation() {
  const consent = document.getElementById("eval-consent-checkbox").checked;
  if (!consent) {
    alert("Participant consent is required to log usability evaluation data.");
    return;
  }
  if (!evalTimerStarted || evalTimerInterval) {
    alert("Start and stop the usability task timer before submitting an evaluation.");
    return;
  }
  const taskCompleted = document.getElementById("eval-task-completed-checkbox").checked;

  const pId = document.getElementById("eval-participant-id").value.trim() || "P01";
  const role = document.getElementById("eval-target-role").value;
  const proto = document.getElementById("eval-prototype-tested").value;
  const susScore = calculateLiveSusScore();

  const susScores = [];
  for (let i = 1; i <= 10; i++) {
    const sel = document.querySelector(`input[name="sus_q${i}"]:checked`);
    if (!sel) {
      alert("Please answer all 10 SUS questions before submitting.");
      return;
    }
    susScores.push(parseInt(sel.value, 10));
  }

  const payload = {
    participant_id: pId,
    target_role: role,
    prototype_tested: proto,
    task_completed: taskCompleted,
    task_time_seconds: evalTimerSeconds,
    sus_scores: susScores,
    sus_total_score: susScore,
    feedback_realism: document.getElementById("eval-notes-realism").value,
    feedback_learning: document.getElementById("eval-notes-learning").value,
    ethical_consent_signed: true
  };

  try {
    const res = await fetch("/api/evaluation-study", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Failed to save evaluation.");
    }
    const data = await res.json();
    alert(`Participant ${pId} evaluation logged successfully!`);
    loadLoggedEvaluations();
  } catch (err) {
    console.error(err);
    alert("Failed to save evaluation to database.");
  }
}

async function loadLoggedEvaluations() {
  const listEl = document.getElementById("eval-studies-list");
  if (!listEl) return;

  try {
    const res = await fetch("/api/evaluation-study");
    const data = await res.json();

    if (!data || data.length === 0) {
      listEl.innerHTML = "<em>No participant test sessions recorded yet. Complete a study run above.</em>";
      return;
    }

    let html = `
      <table class="sus-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Target Role</th>
            <th>Prototype</th>
            <th>Task Time</th>
            <th>SUS Score</th>
            <th>Consent</th>
            <th>Recorded At</th>
          </tr>
        </thead>
        <tbody>
    `;
    data.forEach(d => {
      html += `
        <tr>
          <td><strong>${escapeHtml(d.participant_id)}</strong></td>
          <td>${escapeHtml(d.target_role)}</td>
          <td>${escapeHtml(d.prototype_tested)}</td>
          <td>${d.task_time_seconds}s</td>
          <td><strong>${d.sus_total_score}</strong>/100</td>
          <td><span class="badge badge-success">✓ Signed</span></td>
          <td>${d.created_at ? d.created_at.substring(0, 16) : 'Now'}</td>
        </tr>
      `;
    });
    html += `</tbody></table>`;
    listEl.innerHTML = html;
  } catch (e) {
    console.warn("Could not load evaluations:", e);
  }
}

function exportEvaluationDataset() {
  fetch("/api/evaluation-study")
    .then(res => res.json())
    .then(data => {
      // Export JSON
      const jsonBlob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const jsonUrl = URL.createObjectURL(jsonBlob);
      const aJson = document.createElement("a");
      aJson.href = jsonUrl;
      aJson.download = "CS435_Evaluation_Data.json";
      aJson.click();

      // Export CSV
      let csv = "participant_id,target_role,prototype_tested,task_time_seconds,sus_total_score,ethical_consent_signed,feedback_realism,feedback_learning\n";
      data.forEach(d => {
        csv += `"${d.participant_id}","${d.target_role}","${d.prototype_tested}",${d.task_time_seconds},${d.sus_total_score},${d.ethical_consent_signed},"${(d.feedback_realism||'').replace(/"/g, '""')}","${(d.feedback_learning||'').replace(/"/g, '""')}"\n`;
      });
      const csvBlob = new Blob([csv], { type: "text/csv" });
      const csvUrl = URL.createObjectURL(csvBlob);
      const aCsv = document.createElement("a");
      aCsv.href = csvUrl;
      aCsv.download = "CS435_Evaluation_Data.csv";
      setTimeout(() => aCsv.click(), 400);
    })
    .catch(err => {
      console.error(err);
      alert("Error generating export dataset.");
    });
}

// ==========================================
// 7. CONFIGURATION MODAL
// ==========================================
function openConfigModal() {
  document.getElementById("modal-config").style.display = "flex";
}

function closeConfigModal() {
  document.getElementById("modal-config").style.display = "none";
}

async function loadConfigSettings() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    const badge = document.getElementById("cfg-engine-badge");
    const orBadge = document.getElementById("cfg-openrouter-badge");

    if (orBadge) {
      if (data.openrouter_active) {
        orBadge.className = "badge badge-success";
        orBadge.innerText = "✓ Nemotron 3.5 Super VL Active";
      } else {
        orBadge.className = "badge badge-outline";
        orBadge.innerText = "Curated Fallback Ready ($0 Free)";
      }
    }

    if (badge) {
      if (data.openrouter_active) {
        badge.className = "badge badge-success";
        badge.innerText = "NVIDIA Nemotron 3.5 Super VL (Free Tier)";
      } else if (data.gemini_active) {
        badge.className = "badge badge-success";
        badge.innerText = "Gemini 1.5 Flash Free Tier Active";
      } else {
        badge.className = "badge badge-primary";
        badge.innerText = "Curated Sample Questions + STAR Evaluator ($0 Free)";
      }
    }
  } catch (err) {
    console.warn("Config load error:", err);
  }
}

async function saveConfigSettings() {
  const openrouterKey = document.getElementById("cfg-openrouter-key") ? document.getElementById("cfg-openrouter-key").value.trim() : "";
  const geminiKey = document.getElementById("cfg-gemini-key") ? document.getElementById("cfg-gemini-key").value.trim() : "";
  const clearApiKeys = document.getElementById("cfg-clear-api-keys").checked;
  const voiceIdx = document.getElementById("cfg-voice-select").value;
  const rateVal = parseFloat(document.getElementById("cfg-voice-rate").value);
  const pitchVal = parseFloat(document.getElementById("cfg-voice-pitch").value);
  autoSpeakEnabled = document.getElementById("cfg-auto-speak").checked;

  speechRate = rateVal;
  speechPitch = pitchVal;

  if (voiceIdx !== "" && userVoices[voiceIdx]) {
    selectedVoice = userVoices[voiceIdx];
  }

  try {
    const payload = {
      voice_speed: speechRate,
      auto_speak: autoSpeakEnabled
    };
    if (clearApiKeys) {
      payload.openrouter_api_key = "";
      payload.gemini_api_key = "";
    } else if (openrouterKey) {
      payload.openrouter_api_key = openrouterKey;
      payload.openrouter_model = "nvidia/nemotron-3.5-super-vl:free";
    }
    if (!clearApiKeys && geminiKey) {
      payload.gemini_api_key = geminiKey;
    }

    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Could not save settings.");
    }
    if (clearApiKeys) {
      document.getElementById("cfg-openrouter-key").value = "";
      document.getElementById("cfg-gemini-key").value = "";
      document.getElementById("cfg-clear-api-keys").checked = false;
    }
    alert("Settings saved successfully! AI Engine is ready.");
    closeConfigModal();
    loadConfigSettings();
  } catch (err) {
    console.error(err);
    alert(`Settings were not saved: ${err.message || "Unknown error"}`);
  }
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// Explicit window bindings for bulletproof browser onclick compatibility
window.switchMainTab = switchMainTab;
window.goToScreenA = goToScreenA;
window.goToScreenB = goToScreenB;
window.startSessionA = startSessionA;
window.startSessionB = startSessionB;
window.submitAnswerA = submitAnswerA;
window.submitSimulationAnswer = submitSimulationAnswer;
window.finishSimulation = finishSimulation;
window.loadSampleAnswerA = loadSampleAnswerA;
window.loadSampleAnswerB = loadSampleAnswerB;
window.loadSampleRahulAnswer = loadSampleAnswerB;
window.toggleVoiceInputUniversal = toggleVoiceInputUniversal;
window.clearAnswerDirect = clearAnswerDirect;
window.toggleWireframeMode = toggleWireframeMode;
window.openConfigModal = openConfigModal;
window.closeConfigModal = closeConfigModal;
window.saveConfigSettings = saveConfigSettings;
window.toggleMuteAudio = toggleMuteAudio;
window.replayLastInterviewerMessage = replayLastInterviewerMessage;
window.speakCurrentQuestionA = speakCurrentQuestionA;
window.speakText = speakText;
window.applyRolePresetA = applyRolePresetA;
window.applyRolePresetB = applyRolePresetB;
window.setRoleFieldA = setRoleFieldA;
window.setRoleFieldB = setRoleFieldB;
window.syncCandidateName = syncCandidateName;
window.syncCandidateCompany = syncCandidateCompany;
window.syncCandidateRole = syncCandidateRole;
window.syncCandidateLevel = syncCandidateLevel;
window.startEvalTimer = startEvalTimer;
window.stopEvalTimer = stopEvalTimer;
window.submitUserEvaluation = submitUserEvaluation;
window.exportEvaluationDataset = exportEvaluationDataset;
window.loadSampleEvaluationP01 = loadSampleEvaluationP01;
window.openWhyFeedbackModal = openWhyFeedbackModal;
window.closeWhyFeedbackModal = closeWhyFeedbackModal;
window.saveReflectionA = saveReflectionA;
window.loadSampleReflectionA = loadSampleReflectionA;
window.testVoicePlayback = testVoicePlayback;
window.searchWebKnowledge = searchWebKnowledge;

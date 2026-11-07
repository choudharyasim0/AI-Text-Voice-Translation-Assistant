const elements = {
    micBtn: document.getElementById("micBtn"),
    inputText: document.getElementById("inputText"),
    outputText: document.getElementById("outputText"),
    voiceInputText: document.getElementById("voiceInputText"),
    voiceOutputText: document.getElementById("voiceOutputText"),
    clearBtn: document.getElementById("clearBtn"),
    translateBtn: document.getElementById("translateBtn"),
    listenBtn: document.getElementById("listenBtn"),
    copyBtn: document.getElementById("copyBtn"),
    swapBtn: document.getElementById("swapBtn"),
    sourceLang: document.getElementById("sourceLang"),
    targetLang: document.getElementById("targetLang"),
    voiceSourceLang: document.getElementById("voiceSourceLang"),
    voiceTargetLang: document.getElementById("voiceTargetLang"),
    themeBtn: document.getElementById("themeBtn"),
    historyBtn: document.getElementById("historyBtn"),
    saveHistory: document.getElementById("saveHistory"),
    historyList: document.getElementById("historyList"),
    clearHistoryBtn: document.getElementById("clearHistoryBtn"),
    historyModal: document.getElementById("historyModal")
};

const state = {
    recognition: null,
    recognizing: false,
    interimTranscript: "",
    finalTranscript: "",
    currentTheme: localStorage.getItem("theme") || "dark",
    saveHistory: localStorage.getItem("saveHistory") !== "false"
};

const speechRecognitionLanguageMap = {
    auto: "en-US", en: "en-US", "en-us": "en-US", ur: "ur-PK", "ur-pk": "ur-PK",
    hi: "hi-IN", "hi-in": "hi-IN", ar: "ar-SA", "ar-sa": "ar-SA",
    fr: "fr-FR", "fr-fr": "fr-FR", de: "de-DE", "de-de": "de-DE",
    es: "es-ES", "es-es": "es-ES", it: "it-IT", "it-it": "it-IT",
    ja: "ja-JP", "ja-jp": "ja-JP", ko: "ko-KR", "ko-kr": "ko-KR",
    zh: "zh-CN", "zh-cn": "zh-CN"
};

const speechSynthesisLanguageMap = {
    en: "en", "en-us": "en", "en-gb": "en", ur: "ur", "ur-pk": "ur",
    hi: "hi", "hi-in": "hi", ar: "ar", "ar-sa": "ar", fr: "fr", "fr-fr": "fr",
    de: "de", "de-de": "de", es: "es", "es-es": "es", it: "it", "it-it": "it",
    ja: "ja", "ja-jp": "ja", ko: "ko", "ko-kr": "ko",
    zh: "zh-cn", "zh-cn": "zh-cn", "zh-tw": "zh-tw"
};

function isLanguageCode(value) {
    return typeof value === "string" && /^[a-z]{2,3}(-[A-Z]{2,3})?$/.test(value);
}

function formatLabel(value) {
    return value.split(/\s+/).map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function getRecognitionLanguage(value) {
    if (!value) return "en-US";
    const normalized = String(value).trim().toLowerCase();
    return speechRecognitionLanguageMap[normalized] || value;
}

function getSpeechSynthesisLanguage(value) {
    if (!value) return "en";
    const normalized = String(value).trim().toLowerCase();
    return speechSynthesisLanguageMap[normalized] || normalized.split("-", 1)[0] || "en";
}

function setButtonLoading(button, label = "Loading...") {
    if (!button) return;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${label}`;
    button.disabled = true;
}

function resetButton(button) {
    if (!button) return;
    if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        delete button.dataset.originalText;
    }
    button.disabled = false;
}

function showToast(message, type = "info") {
    const containerId = "app-toast-container";
    let container = document.getElementById(containerId);
    if (!container) {
        container = document.createElement("div");
        container.id = containerId;
        container.style.position = "fixed";
        container.style.bottom = "20px";
        container.style.right = "20px";
        container.style.zIndex = "9999";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.style.marginTop = "10px";
    toast.style.padding = "10px 14px";
    toast.style.borderRadius = "8px";
    toast.style.color = "#fff";
    toast.style.fontSize = "14px";
    toast.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.2)";
    toast.style.maxWidth = "320px";
    toast.style.backgroundColor = type === "error" ? "#dc3545" : type === "success" ? "#198754" : "#0d6efd";
    toast.textContent = message;
    container.appendChild(toast);
    window.setTimeout(() => {
        toast.remove();
        if (!container.children.length) container.remove();
    }, 3000);
}

function updateSpeechInput() {
    const combined = [state.finalTranscript, state.interimTranscript].filter(Boolean).join(" ").trim();
    if (elements.inputText) elements.inputText.value = combined;
    if (elements.voiceInputText) elements.voiceInputText.value = combined;
}

function stopRecognition() {
    if (state.recognition) {
        try { state.recognition.stop(); } catch (error) { console.warn("Speech recognition stop warning:", error); }
    }
    state.recognizing = false;
    if (elements.micBtn) elements.micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Speak';
    updateSpeechInput();
}

async function loadLanguages() {
    try {
        const response = await fetch("/languages");
        if (!response.ok) throw new Error("Failed to load languages");
        const languages = await response.json();
        const entries = Object.entries(languages || {});
        const normalized = {};
        if (entries.length && isLanguageCode(entries[0][0]) && !isLanguageCode(entries[0][1])) {
            for (const [code, label] of entries) normalized[code] = label;
        } else {
            for (const [name, code] of entries) normalized[code] = name === "auto" ? "Auto Detect" : formatLabel(name);
        }
        const optionList = Object.entries(normalized)
            .filter(([code]) => code && code !== "auto")
            .map(([value, label]) => ({ value, label }));
        const populateSelect = (select, includeAuto = false) => {
            if (!select) return;
            select.innerHTML = "";
            if (includeAuto) {
                const option = document.createElement("option");
                option.value = "auto";
                option.textContent = "Auto Detect";
                select.appendChild(option);
            }
            optionList.forEach(({ value, label }) => {
                const option = document.createElement("option");
                option.value = value;
                option.textContent = label;
                select.appendChild(option);
            });
        };
        populateSelect(elements.sourceLang, true);
        populateSelect(elements.targetLang);
        populateSelect(elements.voiceSourceLang, true);
        populateSelect(elements.voiceTargetLang);
        if (elements.sourceLang) elements.sourceLang.value = "auto";
        if (elements.voiceSourceLang) elements.voiceSourceLang.value = "auto";
        for (const select of [elements.targetLang, elements.voiceTargetLang]) {
            if (select) {
                if (select.querySelector("option[value=en]")) select.value = "en";
                else if (select.options.length) select.selectedIndex = 0;
            }
        }
    } catch (error) {
        console.error("Failed to load languages:", error);
        showToast("Could not load languages", "error");
    }
}

async function loadHistory() {
    try {
        const response = await fetch("/history");
        if (!response.ok) throw new Error("History request failed");
        const history = await response.json();
        window.translationHistory = Array.isArray(history) ? history : [];
        renderHistory();
    } catch (error) {
        console.warn("History unavailable:", error);
        window.translationHistory = [];
        renderHistory();
    }
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = value == null ? "" : String(value);
    return element.innerHTML;
}

function languageLabel(code) {
    const value = String(code || "").trim();
    if (!value || value.toLowerCase() === "auto") return "Auto Detect";
    try {
        return new Intl.DisplayNames([document.documentElement.lang || "en"], { type: "language" }).of(value) || value.toUpperCase();
    } catch (_error) {
        return value.toUpperCase();
    }
}

function renderHistory() {
    if (!elements.historyList) return;
    const history = Array.isArray(window.translationHistory) ? window.translationHistory : [];
    if (!history.length) {
        elements.historyList.innerHTML = '<p class="history-empty"><i class="fa-regular fa-folder-open"></i> No saved translations yet.</p>';
        return;
    }

    // API stores newest entries first. Support both current and legacy field names.
    elements.historyList.innerHTML = history.map((item) => {
        const source = item.source_lang ?? item.source ?? "auto";
        const target = item.target_lang ?? item.target ?? "";
        const original = item.source_text ?? item.original ?? "";
        const translation = item.translated_text ?? item.translated ?? "";
        const timestamp = item.timestamp ?? "";

        return `
            <article class="history-item">
                <div class="history-meta">
                    <span>${escapeHtml(languageLabel(source))} ➔ ${escapeHtml(languageLabel(target))}</span>
                    <time>${escapeHtml(timestamp)}</time>
                </div>
                <p style="white-space: pre-wrap; overflow-wrap: anywhere;"><strong>Original:</strong> ${escapeHtml(original)}</p>
                <p style="white-space: pre-wrap; overflow-wrap: anywhere;"><strong>Translation:</strong> ${escapeHtml(translation)}</p>
            </article>
        `;
    }).join("");
}

async function showHistory() {
    await loadHistory();
    if (elements.historyModal && window.bootstrap) bootstrap.Modal.getOrCreateInstance(elements.historyModal).show();
}

async function clearTranslationHistory() {
    try {
        const response = await fetch("/clear-history", { method: "DELETE" });
        if (!response.ok) throw new Error("Could not clear history");
        window.translationHistory = [];
        renderHistory();
        showToast("History cleared", "success");
    } catch (error) {
        console.warn("History clear failed:", error);
    }
}

function applyTheme(theme) {
    if (!document.body) return;
    document.body.classList.remove("light-theme", "pro-theme");
    if (theme === "light") {
        document.body.classList.add("light-theme");
        if (elements.themeBtn) { elements.themeBtn.innerHTML = '<i class="fa-solid fa-moon"></i>'; elements.themeBtn.title = "Switch to Pro theme"; }
    } else if (theme === "pro") {
        document.body.classList.add("pro-theme");
        if (elements.themeBtn) { elements.themeBtn.innerHTML = '<i class="fa-solid fa-star"></i>'; elements.themeBtn.title = "Switch to Dark theme"; }
    } else if (elements.themeBtn) {
        elements.themeBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
        elements.themeBtn.title = "Switch to Light theme";
    }
    state.currentTheme = theme;
    localStorage.setItem("theme", theme);
}

async function handleSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { showToast("Browser speech recognition is not supported in this browser.", "error"); return; }
    if (state.recognizing) { stopRecognition(); return; }
    state.finalTranscript = "";
    state.interimTranscript = "";
    updateSpeechInput();
    const recognition = new SpeechRecognition();
    recognition.lang = getRecognitionLanguage(elements.voiceSourceLang?.value || elements.sourceLang?.value || "auto");
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.onresult = (event) => {
        let latestInterim = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
            const transcript = event.results[index][0].transcript.trim();
            if (event.results[index].isFinal) state.finalTranscript = [state.finalTranscript, transcript].filter(Boolean).join(" ").trim();
            else latestInterim = transcript;
        }
        state.interimTranscript = latestInterim;
        updateSpeechInput();
    };
    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        showToast(event.error === "not-allowed" ? "Microphone access was denied. Please allow microphone permission and try again." : `Speech recognition error: ${event.error || "unknown error"}`, "error");
        stopRecognition();
    };
    recognition.onend = () => {
        state.recognizing = false;
        if (elements.micBtn) elements.micBtn.innerHTML = '<i class="fa-solid fa-microphone"></i> Speak';
        updateSpeechInput();
    };
    try {
        recognition.start();
        state.recognition = recognition;
        state.recognizing = true;
        if (elements.micBtn) elements.micBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop';
        showToast("Listening...");
    } catch (error) {
        console.error("Failed to start speech recognition:", error);
        showToast("Speech recognition could not start", "error");
    }
}

async function handleTranslation() {
    const text = elements.inputText?.value.trim() || "";
    if (!text) { showToast("Enter text to translate", "error"); return; }
    if (elements.outputText) elements.outputText.value = "Translating...";
    setButtonLoading(elements.translateBtn, "Translating...");
    try {
        const response = await fetch("/translate", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, source: elements.sourceLang?.value || "auto", target: elements.targetLang?.value || "en", save_history: state.saveHistory })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) throw new Error(payload.error || "Translation failed");
        if (elements.outputText) elements.outputText.value = payload.translation || "";
        await loadHistory();
        showToast("Translation complete", "success");
    } catch (error) {
        if (elements.outputText) elements.outputText.value = "";
        showToast(error.message || "Translation failed", "error");
    } finally { resetButton(elements.translateBtn); }
}

async function handleVoiceTranslation() {
    const text = elements.voiceInputText?.value.trim() || "";
    if (!text) { showToast("Speak or type something in the voice transcript box", "error"); return; }
    if (elements.voiceOutputText) elements.voiceOutputText.value = "Translating...";
    try {
        const response = await fetch("/translate", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, source: elements.voiceSourceLang?.value || "auto", target: elements.voiceTargetLang?.value || "en", save_history: state.saveHistory })
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || !payload.success) throw new Error(payload.error || "Voice translation failed");
        if (elements.voiceOutputText) elements.voiceOutputText.value = payload.translation || "";
        await loadHistory();
        showToast("Voice translation complete", "success");
    } catch (error) {
        if (elements.voiceOutputText) elements.voiceOutputText.value = "";
        showToast(error.message || "Voice translation failed", "error");
    }
}

async function handleTextToSpeech() {
    const text = (elements.outputText?.value || elements.inputText?.value || "").trim();
    if (!text) { showToast("No text to speak", "error"); return; }
    setButtonLoading(elements.listenBtn, "Playing...");
    try {
        const response = await fetch("/text-to-speech", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, lang: getSpeechSynthesisLanguage(elements.targetLang?.value || "en") })
        });
        const contentType = response.headers.get("content-type") || "";
        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.error || "Speech playback failed");
        }
        if (!contentType.includes("audio")) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.error || "Speech playback failed");
        }
        const blob = await response.blob();
        const mediaUrl = URL.createObjectURL(blob);
        const audio = new Audio(mediaUrl);
        await audio.play();
        audio.addEventListener("ended", () => URL.revokeObjectURL(mediaUrl), { once: true });
    } catch (error) { showToast(error.message || "Speech playback failed", "error"); }
    finally { resetButton(elements.listenBtn); }
}

async function handleCopyText() {
    const textToCopy = elements.outputText?.value || "";
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(textToCopy);
        else {
            const field = document.createElement("textarea");
            field.value = textToCopy;
            document.body.appendChild(field);
            field.select();
            document.execCommand("copy");
            field.remove();
        }
        showToast("Copied to clipboard", "success");
    } catch (error) { console.error("Copy failed:", error); showToast("Copy failed", "error"); }
}

function handleSwap() {
    if (elements.sourceLang && elements.targetLang) {
        const previousSource = elements.sourceLang.value;
        elements.sourceLang.value = elements.targetLang.value;
        elements.targetLang.value = previousSource;
    }
    if (elements.voiceSourceLang && elements.voiceTargetLang) {
        const previousSource = elements.voiceSourceLang.value;
        elements.voiceSourceLang.value = elements.voiceTargetLang.value;
        elements.voiceTargetLang.value = previousSource;
    }
    const previousInput = elements.inputText?.value || "";
    if (elements.inputText && elements.outputText) {
        elements.inputText.value = elements.outputText.value;
        elements.outputText.value = previousInput;
    }
    showToast("Swapped", "success");
}

function initializeApp() {
    applyTheme(state.currentTheme);
    if (elements.saveHistory) elements.saveHistory.checked = state.saveHistory;
    if (elements.micBtn) elements.micBtn.addEventListener("click", handleSpeechRecognition);
    if (elements.voiceInputText) elements.voiceInputText.addEventListener("input", (event) => { if (elements.inputText) elements.inputText.value = event.target.value; });
    const voiceTranslateBtn = document.getElementById("voiceTranslateBtn");
    if (voiceTranslateBtn) voiceTranslateBtn.addEventListener("click", handleVoiceTranslation);
    if (elements.clearBtn) elements.clearBtn.addEventListener("click", () => {
        if (elements.inputText) elements.inputText.value = "";
        if (elements.voiceInputText) elements.voiceInputText.value = "";
        if (elements.voiceOutputText) elements.voiceOutputText.value = "";
        if (elements.outputText) elements.outputText.value = "";
        state.finalTranscript = "";
        state.interimTranscript = "";
        showToast("Cleared", "success");
    });
    if (elements.clearHistoryBtn) elements.clearHistoryBtn.addEventListener("click", async () => {
        try {
            const response = await fetch("/clear-history", { method: "DELETE" });
            if (!response.ok) throw new Error("Could not clear history");
            window.translationHistory = [];
            renderHistory();
            if (window.bootstrap && elements.historyModal) bootstrap.Modal.getOrCreateInstance(elements.historyModal).hide();
            showToast("History cleared", "success");
        } catch (error) { showToast(error.message || "History clear failed", "error"); }
    });
    if (elements.translateBtn) elements.translateBtn.addEventListener("click", handleTranslation);
    if (elements.listenBtn) elements.listenBtn.addEventListener("click", handleTextToSpeech);
    if (elements.copyBtn) elements.copyBtn.addEventListener("click", handleCopyText);
    if (elements.swapBtn) elements.swapBtn.addEventListener("click", handleSwap);
    if (elements.themeBtn) elements.themeBtn.addEventListener("click", () => applyTheme(state.currentTheme === "light" ? "dark" : state.currentTheme === "dark" ? "pro" : "light"));
    if (elements.historyBtn) elements.historyBtn.addEventListener("click", showHistory);
    if (elements.saveHistory) elements.saveHistory.addEventListener("change", () => {
        state.saveHistory = elements.saveHistory.checked;
        localStorage.setItem("saveHistory", String(state.saveHistory));
        showToast(state.saveHistory ? "History saving enabled" : "History saving disabled");
    });
    loadLanguages();
    loadHistory();
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initializeApp);
else initializeApp();

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const videoUrlInput = document.getElementById("videoUrl");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const analyzeSpinner = document.getElementById("analyzeSpinner");
    const demoChips = document.querySelectorAll(".demo-chip");

    const videoDetailsCard = document.getElementById("videoDetailsCard");
    const videoThumb = document.getElementById("videoThumb");
    const videoTitle = document.getElementById("videoTitle");
    const videoAuthor = document.getElementById("videoAuthor");
    const videoDuration = document.getElementById("videoDuration");
    const momentsGrid = document.getElementById("momentsGrid");

    const startTimeInput = document.getElementById("startTime");
    const endTimeInput = document.getElementById("endTime");
    const currentDurationSpan = document.getElementById("currentDuration");
    const snapBtns = document.querySelectorAll(".snap-btn");

    const customizerSection = document.getElementById("customizerSection");
    const layoutCards = document.querySelectorAll(".opt-card");
    const stylePills = document.querySelectorAll(".style-pill");
    const topHookInput = document.getElementById("topHookInput");
    const shieldToggle = document.getElementById("shieldToggle");

    const generateBtn = document.getElementById("generateBtn");
    const genSpinner = document.getElementById("genSpinner");

    const progressCard = document.getElementById("progressCard");
    const progressStatusText = document.getElementById("progressStatusText");
    const progressBarFill = document.getElementById("progressBarFill");
    const stepItems = [
        document.getElementById("step1"),
        document.getElementById("step2"),
        document.getElementById("step3"),
        document.getElementById("step4")
    ];

    const resultCard = document.getElementById("resultCard");
    const resultVideo = document.getElementById("resultVideo");
    const downloadBtn = document.getElementById("downloadBtn");
    const openFolderBtn = document.getElementById("openFolderBtn");
    const suggestedTitleInput = document.getElementById("suggestedTitle");
    const suggestedDescArea = document.getElementById("suggestedDesc");
    const suggestedTagsInput = document.getElementById("suggestedTags");
    const copyBtns = document.querySelectorAll(".copy-btn");

    if (openFolderBtn) {
        openFolderBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/open-folder", { method: "POST" });
            } catch (err) {
                console.error("Open folder error:", err);
            }
        });
    }


    // State
    let selectedLayout = "blur";
    let selectedStyle = "hormozi";
    let currentVideoData = null;

    // Helper: parse MM:SS or seconds
    function parseToSec(str) {
        if (!str) return 0;
        const parts = str.trim().split(":");
        if (parts.length === 1) return parseFloat(parts[0]) || 0;
        if (parts.length === 2) return (parseFloat(parts[0]) || 0) * 60 + (parseFloat(parts[1]) || 0);
        if (parts.length === 3) return (parseFloat(parts[0]) || 0) * 3600 + (parseFloat(parts[1]) || 0) * 60 + (parseFloat(parts[2]) || 0);
        return 0;
    }

    function formatSec(sec) {
        sec = Math.round(sec);
        const m = Math.floor(sec / 60);
        const s = sec % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function updateDurationDisplay() {
        const start = parseToSec(startTimeInput.value);
        const end = parseToSec(endTimeInput.value);
        const dur = Math.max(0, Math.round(end - start));
        currentDurationSpan.textContent = `${dur}s`;

        // Update snap button active state
        snapBtns.forEach(btn => {
            const targetSec = parseInt(btn.dataset.sec, 10);
            if (targetSec === dur) {
                btn.classList.add("active");
            } else {
                btn.classList.remove("active");
            }
        });
    }

    startTimeInput.addEventListener("input", updateDurationDisplay);
    endTimeInput.addEventListener("input", updateDurationDisplay);

    // Quick Snaps
    snapBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const sec = parseInt(btn.dataset.sec, 10);
            const start = parseToSec(startTimeInput.value);
            endTimeInput.value = formatSec(start + sec);
            updateDurationDisplay();
        });
    });

    // Demo Chips
    demoChips.forEach(chip => {
        chip.addEventListener("click", () => {
            videoUrlInput.value = chip.dataset.url;
            analyzeVideo();
        });
    });

    // Layout Selector
    layoutCards.forEach(card => {
        card.addEventListener("click", () => {
            layoutCards.forEach(c => c.classList.remove("active"));
            card.classList.add("active");
            selectedLayout = card.dataset.layout;
        });
    });

    // Style Selector
    stylePills.forEach(pill => {
        pill.addEventListener("click", () => {
            stylePills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            selectedStyle = pill.dataset.style;
        });
    });

    // Copy to clipboard
    copyBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.dataset.target;
            const targetEl = document.getElementById(targetId);
            if (targetEl) {
                navigator.clipboard.writeText(targetEl.value).then(() => {
                    const originalText = btn.textContent;
                    btn.textContent = "Copied! ✓";
                    setTimeout(() => { btn.textContent = originalText; }, 2000);
                });
            }
        });
    });

    // Analyze Video Action
    async function analyzeVideo() {
        const url = videoUrlInput.value.trim();
        if (!url) {
            alert("Please paste a valid YouTube video URL!");
            return;
        }

        analyzeBtn.disabled = true;
        analyzeSpinner.classList.remove("hidden");
        analyzeBtn.querySelector(".btn-text").textContent = "Analyzing Heatmap...";

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });

            const data = await response.json();
            if (data.error) {
                alert("Error analyzing video: " + data.error);
                return;
            }

            currentVideoData = data;

            // Update UI
            videoThumb.src = data.thumbnail;
            videoTitle.textContent = data.title;
            videoAuthor.textContent = data.uploader;
            videoDuration.textContent = `⏱️ ${data.duration_fmt}`;

            // Populate Viral Moments
            momentsGrid.innerHTML = "";
            if (data.viral_moments && data.viral_moments.length > 0) {
                data.viral_moments.forEach((mom, idx) => {
                    const card = document.createElement("div");
                    card.className = `moment-card ${idx === 0 ? 'selected' : ''}`;
                    card.innerHTML = `
                        <span class="moment-badge">${mom.hook_badge}</span>
                        <div class="moment-title">${mom.title}</div>
                        <div class="moment-time-row">
                            <span>⏱️ ${mom.start_fmt} - ${mom.end_fmt}</span>
                            <span style="color: var(--accent); font-weight: 800;">${mom.virality_score}% Viral</span>
                        </div>
                        <div class="virality-bar-bg">
                            <div class="virality-bar-fill" style="width: ${mom.virality_score}%"></div>
                        </div>
                    `;

                    card.addEventListener("click", () => {
                        document.querySelectorAll(".moment-card").forEach(c => c.classList.remove("selected"));
                        card.classList.add("selected");
                        startTimeInput.value = mom.start_fmt;
                        endTimeInput.value = mom.end_fmt;
                        updateDurationDisplay();
                    });

                    momentsGrid.appendChild(card);
                });

                // Auto-select first moment
                startTimeInput.value = data.viral_moments[0].start_fmt;
                endTimeInput.value = data.viral_moments[0].end_fmt;
                updateDurationDisplay();
            }

            videoDetailsCard.classList.remove("hidden");
            customizerSection.classList.remove("hidden");
            resultCard.classList.add("hidden");

        } catch (err) {
            alert("Failed to connect to studio server: " + err.message);
        } finally {
            analyzeBtn.disabled = false;
            analyzeSpinner.classList.add("hidden");
            analyzeBtn.querySelector(".btn-text").textContent = "✨ Find Viral Moments";
        }
    }

    analyzeBtn.addEventListener("click", analyzeVideo);

    // Generate 9:16 Short
    generateBtn.addEventListener("click", async () => {
        const url = videoUrlInput.value.trim();
        const startTime = startTimeInput.value.trim();
        const endTime = endTimeInput.value.trim();
        const topHook = topHookInput.value.trim();
        const copyrightShield = shieldToggle.checked;

        if (!url) {
            alert("Please provide a video URL");
            return;
        }

        // Show Progress Card
        progressCard.classList.remove("hidden");
        resultCard.classList.add("hidden");
        generateBtn.disabled = true;
        genSpinner.classList.remove("hidden");
        generateBtn.querySelector(".btn-text").textContent = "Processing Short...";

        // Animate progress simulation
        let stepIdx = 0;
        const progressInterval = setInterval(() => {
            if (stepIdx < 3) {
                stepIdx++;
                stepItems.forEach((st, i) => {
                    if (i <= stepIdx) st.classList.add("active");
                });
                progressBarFill.style.width = `${(stepIdx + 1) * 25}%`;
                const msgs = [
                    "Downloading targeted 30-40s segment...",
                    "Generating animated word-by-word subtitles...",
                    "Rendering 1080x1920 9:16 vertical Short in FFmpeg...",
                    "Finalizing MP4 video..."
                ];
                progressStatusText.textContent = msgs[stepIdx];
            }
        }, 3000);

        try {
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url,
                    start_time: startTime,
                    end_time: endTime,
                    layout: selectedLayout,
                    subtitle_style: selectedStyle,
                    top_hook: topHook,
                    copyright_shield: copyrightShield
                })
            });

            clearInterval(progressInterval);
            progressBarFill.style.width = "100%";
            stepItems.forEach(st => st.classList.add("active"));

            const data = await response.json();
            if (data.error) {
                alert("Error during video generation: " + data.error);
                return;
            }

            // Populate Result Card
            resultVideo.src = data.download_url;
            downloadBtn.href = data.download_url;
            downloadBtn.download = data.video_filename;

            suggestedTitleInput.value = data.suggested_title;
            suggestedDescArea.value = data.suggested_description;
            suggestedTagsInput.value = data.suggested_tags.join(" ");

            progressCard.classList.add("hidden");
            resultCard.classList.remove("hidden");
            resultVideo.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            clearInterval(progressInterval);
            alert("Generation failed: " + err.message);
        } finally {
            generateBtn.disabled = false;
            genSpinner.classList.add("hidden");
            generateBtn.querySelector(".btn-text").textContent = "🚀 Generate 9:16 Short (MP4)";
        }
    });

    // Trigger initial demo video on load if input has URL
    if (videoUrlInput.value) {
        analyzeVideo();
    }
});

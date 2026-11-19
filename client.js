document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements - Tabs & Inputs
    const tabUrl = document.getElementById("tabUrl");
    const tabUpload = document.getElementById("tabUpload");
    const panelUrl = document.getElementById("panelUrl");
    const panelUpload = document.getElementById("panelUpload");

    const videoUrlInput = document.getElementById("videoUrl");
    const pasteClipboardBtn = document.getElementById("pasteClipboardBtn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const analyzeSpinner = document.getElementById("analyzeSpinner");
    const demoChips = document.querySelectorAll(".demo-chip");

    const dropZone = document.getElementById("dropZone");
    const videoFileInput = document.getElementById("videoFileInput");
    const browseFilesLink = document.getElementById("browseFilesLink");
    const dropZonePrompt = document.getElementById("dropZonePrompt");
    const fileSelectedBox = document.getElementById("fileSelectedBox");
    const selectedFileName = document.getElementById("selectedFileName");
    const selectedFileSize = document.getElementById("selectedFileSize");
    const selectedFileStatus = document.getElementById("selectedFileStatus");
    const changeFileBtn = document.getElementById("changeFileBtn");
    const analyzeFileBtn = document.getElementById("analyzeFileBtn");
    const uploadAnalyzeSpinner = document.getElementById("uploadAnalyzeSpinner");

    const uploadProgressContainer = document.getElementById("uploadProgressContainer");
    const uploadStatusText = document.getElementById("uploadStatusText");
    const uploadPercentText = document.getElementById("uploadPercentText");
    const uploadBarFill = document.getElementById("uploadBarFill");

    const localPathInput = document.getElementById("localPathInput");
    const loadLocalPathBtn = document.getElementById("loadLocalPathBtn");

    const durationPills = document.querySelectorAll(".dur-pill");
    const countPills = document.querySelectorAll(".count-pill");

    const videoDetailsCard = document.getElementById("videoDetailsCard");
    const videoThumb = document.getElementById("videoThumb");
    const videoTitle = document.getElementById("videoTitle");
    const videoAuthor = document.getElementById("videoAuthor");
    const videoDuration = document.getElementById("videoDuration");
    const detectedMomentsCount = document.getElementById("detectedMomentsCount");
    const momentsGrid = document.getElementById("momentsGrid");
    const selectAllMomentsBtn = document.getElementById("selectAllMomentsBtn");
    const selectTop4MomentsBtn = document.getElementById("selectTop4MomentsBtn");
    const selectedCounterBadge = document.getElementById("selectedCounterBadge");

    const startTimeInput = document.getElementById("startTime");
    const endTimeInput = document.getElementById("endTime");
    const currentDurationSpan = document.getElementById("currentDuration");
    const snapBtns = document.querySelectorAll(".snap-btn");

    const customizerSection = document.getElementById("customizerSection");
    const layoutCards = document.querySelectorAll(".opt-card");
    const stylePills = document.querySelectorAll(".style-pill");
    const topHookInput = document.getElementById("topHookInput");
    const headerLine1 = document.getElementById("headerLine1");
    const headerLine2 = document.getElementById("headerLine2");
    const headerLine3 = document.getElementById("headerLine3");
    const previewLine1 = document.getElementById("previewLine1");
    const previewLine2 = document.getElementById("previewLine2");
    const previewLine3 = document.getElementById("previewLine3");
    const presetChips = document.querySelectorAll(".preset-chip");
    const sfxSelect = document.getElementById("sfxSelect");
    const sfxToggle = document.getElementById("sfxToggle");
    const testSfxBtn = document.getElementById("testSfxBtn");
    const zoomToggle = document.getElementById("zoomToggle");
    const qualityToggle = document.getElementById("qualityToggle");
    const shieldToggle = document.getElementById("shieldToggle");

    const batchGenerateBtn = document.getElementById("batchGenerateBtn");
    const batchCountText = document.getElementById("batchCountText");
    const batchGenSpinner = document.getElementById("batchGenSpinner");
    const generateBtn = document.getElementById("generateBtn");
    const genSpinner = document.getElementById("genSpinner");

    const progressCard = document.getElementById("progressCard");
    const progressStatusText = document.getElementById("progressStatusText");
    const progressBatchIndicator = document.getElementById("progressBatchIndicator");
    const progressBarFill = document.getElementById("progressBarFill");
    const progressPercentBadge = document.getElementById("progressPercentBadge");
    const progressTime = document.getElementById("progressTime");
    const cancelJobBtn = document.getElementById("cancelJobBtn");
    const stepItems = [
        document.getElementById("step1"),
        document.getElementById("step2"),
        document.getElementById("step3"),
        document.getElementById("step4")
    ];

    const resultCard = document.getElementById("resultCard");
    const resultHeaderTitle = document.getElementById("resultHeaderTitle");
    const downloadAllZipBtn = document.getElementById("downloadAllZipBtn");
    const openFolderBtn = document.getElementById("openFolderBtn");
    const shortsTabStrip = document.getElementById("shortsTabStrip");
    const resultVideo = document.getElementById("resultVideo");
    const downloadBtn = document.getElementById("downloadBtn");
    const activeShortMetaTitle = document.getElementById("activeShortMetaTitle");
    const activeShortBadge = document.getElementById("activeShortBadge");
    const suggestedTitleInput = document.getElementById("suggestedTitle");
    const suggestedDescArea = document.getElementById("suggestedDesc");
    const suggestedTagsInput = document.getElementById("suggestedTags");
    const copyBtns = document.querySelectorAll(".copy-btn");

    // State
    let activeTab = "url"; // "url" | "upload"
    let currentVideoSource = videoUrlInput.value.trim();
    let selectedLayout = "blur";
    let selectedStyle = "3d_hormozi";
    let targetDuration = 35;
    let targetClipCount = 5;
    let currentVideoData = null;
    let selectedMomentIds = new Set();
    let generatedShortsData = [];
    let activeShortIndex = 0;
    let uploadedFilePath = null;
    let currentJobId = null;
    let jobPollTimer = null;
    let jobStartTime = null;
    let jobTimeTimer = null;

    // Tab Switching
    function switchTab(tabName) {
        activeTab = tabName;
        if (tabName === "url") {
            tabUrl.classList.add("active");
            tabUpload.classList.remove("active");
            panelUrl.classList.remove("hidden");
            panelUpload.classList.add("hidden");
        } else {
            tabUpload.classList.add("active");
            tabUrl.classList.remove("active");
            panelUpload.classList.remove("hidden");
            panelUrl.classList.add("hidden");
        }
    }

    if (tabUrl && tabUpload) {
        tabUrl.addEventListener("click", () => switchTab("url"));
        tabUpload.addEventListener("click", () => switchTab("upload"));
    }

    // Open Output Folder in Explorer
    if (openFolderBtn) {
        openFolderBtn.addEventListener("click", async () => {
            try {
                await fetch("/api/open-folder", { method: "POST" });
            } catch (err) {
                console.error("Open folder error:", err);
            }
        });
    }

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

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function updateDurationDisplay() {
        const start = parseToSec(startTimeInput.value);
        const end = parseToSec(endTimeInput.value);
        const dur = Math.max(0, Math.round(end - start));
        currentDurationSpan.textContent = `${dur}s`;

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

    // Quick Snaps in Trimmer
    snapBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const sec = parseInt(btn.dataset.sec, 10);
            const start = parseToSec(startTimeInput.value);
            endTimeInput.value = formatSec(start + sec);
            updateDurationDisplay();
        });
    });

    // Duration Target Pills (15s-25s, 30s-40s, 45s-60s)
    durationPills.forEach(pill => {
        pill.addEventListener("click", () => {
            durationPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            targetDuration = parseInt(pill.dataset.sec, 10);
            if (currentVideoSource) {
                analyzeVideo(currentVideoSource);
            }
        });
    });

    // Clip Count Pills (4, 5, 6)
    countPills.forEach(pill => {
        pill.addEventListener("click", () => {
            countPills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            targetClipCount = parseInt(pill.dataset.count, 10);
            if (currentVideoSource) {
                analyzeVideo(currentVideoSource);
            }
        });
    });

    // Demo Chips
    demoChips.forEach(chip => {
        chip.addEventListener("click", () => {
            videoUrlInput.value = chip.dataset.url;
            switchTab("url");
            analyzeVideo(chip.dataset.url);
        });
    });

    // Enter key listener on videoUrlInput
    if (videoUrlInput) {
        videoUrlInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const val = videoUrlInput.value.trim();
                if (val) analyzeVideo(val);
            }
        });
    }

    // Paste URL Button inside Input
    if (pasteClipboardBtn) {
        pasteClipboardBtn.addEventListener("click", async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text) {
                    videoUrlInput.value = text.trim();
                    analyzeVideo(text.trim());
                }
            } catch (err) {
                console.warn("Clipboard read error:", err);
            }
        });
    }

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

    // 2-3 Line Viral Header Preview Sync
    function updateHeaderPreview() {
        const l1 = headerLine1 ? headerLine1.value.trim() : "";
        const l2 = headerLine2 ? headerLine2.value.trim() : "";
        const l3 = headerLine3 ? headerLine3.value.trim() : "";

        if (previewLine1) {
            previewLine1.textContent = l1 || "THE HARSH TRUTH ⚠️";
            previewLine1.style.display = l1 ? "inline-block" : "none";
        }
        if (previewLine2) {
            previewLine2.textContent = l2 || "THAT NOBODY ADMITS...";
            previewLine2.style.display = l2 ? "block" : "none";
        }
        if (previewLine3) {
            previewLine3.textContent = l3 || "";
            previewLine3.style.display = l3 ? "block" : "none";
        }

        if (topHookInput) {
            topHookInput.value = [l1, l2, l3].filter(Boolean).join("\n");
        }
    }

    if (headerLine1) headerLine1.addEventListener("input", updateHeaderPreview);
    if (headerLine2) headerLine2.addEventListener("input", updateHeaderPreview);
    if (headerLine3) headerLine3.addEventListener("input", updateHeaderPreview);

    // Preset Chips for 2-3 Line Viral Headers
    presetChips.forEach(chip => {
        chip.addEventListener("click", () => {
            presetChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            if (headerLine1 && chip.dataset.l1) headerLine1.value = chip.dataset.l1;
            if (headerLine2 && chip.dataset.l2) headerLine2.value = chip.dataset.l2;
            if (headerLine3) headerLine3.value = chip.dataset.l3 || "";
            updateHeaderPreview();
        });
    });

    // SFX Test Audio Player
    if (testSfxBtn && sfxSelect) {
        testSfxBtn.addEventListener("click", () => {
            const sound = sfxSelect.value;
            if (!sound || sound === "none") {
                alert("Please select a valid sound effect from the dropdown!");
                return;
            }
            try {
                const audio = new Audio(`/assets/sfx/${sound}.wav`);
                audio.volume = 0.95;
                audio.play().catch(e => {
                    console.log("Audio preview error:", e);
                });
            } catch (err) {
                console.error("SFX preview error:", err);
            }
        });
    }

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

    function updateBatchSelectionUI() {
        const count = selectedMomentIds.size;
        if (selectedCounterBadge) {
            selectedCounterBadge.textContent = `${count} Selected`;
        }
        if (batchCountText) {
            batchCountText.textContent = count;
        }
        if (batchGenerateBtn) {
            batchGenerateBtn.disabled = count === 0;
        }
    }

    if (selectAllMomentsBtn) {
        selectAllMomentsBtn.addEventListener("click", () => {
            if (!currentVideoData || !currentVideoData.viral_moments) return;
            currentVideoData.viral_moments.forEach(m => selectedMomentIds.add(m.id));
            document.querySelectorAll(".moment-checkbox").forEach(cb => cb.checked = true);
            updateBatchSelectionUI();
        });
    }

    if (selectTop4MomentsBtn) {
        selectTop4MomentsBtn.addEventListener("click", () => {
            if (!currentVideoData || !currentVideoData.viral_moments) return;
            selectedMomentIds.clear();
            const top4 = currentVideoData.viral_moments.slice(0, 4);
            top4.forEach(m => selectedMomentIds.add(m.id));
            document.querySelectorAll(".moment-checkbox").forEach(cb => {
                const id = parseInt(cb.dataset.id, 10);
                cb.checked = selectedMomentIds.has(id);
            });
            updateBatchSelectionUI();
        });
    }

    // ==========================================
    // FILE UPLOAD & DRAG/DROP & LOCAL PATH
    // ==========================================
    if (browseFilesLink && videoFileInput) {
        browseFilesLink.addEventListener("click", (e) => {
            e.stopPropagation();
            videoFileInput.click();
        });
    }

    if (dropZone && videoFileInput) {
        dropZone.addEventListener("click", (e) => {
            if (e.target.closest("#fileSelectedBox") || e.target.closest("button")) return;
            videoFileInput.click();
        });

        // Drag & Drop event listeners
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                handleFileUpload(files[0]);
            }
        });

        videoFileInput.addEventListener('change', function () {
            if (this.files && this.files.length > 0) {
                handleFileUpload(this.files[0]);
            }
        });
    }

    if (changeFileBtn && videoFileInput) {
        changeFileBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            videoFileInput.click();
        });
    }

    if (analyzeFileBtn) {
        analyzeFileBtn.addEventListener("click", () => {
            if (uploadedFilePath) {
                analyzeVideo(uploadedFilePath);
            }
        });
    }

    // Direct Local Path Load (Instant PC file access)
    if (loadLocalPathBtn && localPathInput) {
        loadLocalPathBtn.addEventListener("click", () => {
            const val = localPathInput.value.trim();
            if (!val) {
                alert("Please enter a local video file path!");
                return;
            }
            analyzeVideo(val);
        });

        localPathInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const val = localPathInput.value.trim();
                if (val) analyzeVideo(val);
            }
        });
    }

    // Global Clipboard Paste (Ctrl+V) anywhere on page
    window.addEventListener("paste", (e) => {
        // If user is typing in a text field, let default paste happen
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
        
        // 1. Check if files are copied in clipboard
        if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length > 0) {
            const file = e.clipboardData.files[0];
            if (file.type.startsWith("video/") || /\.(mp4|mov|mkv|avi|webm|m4v|ts|wmv|flv)$/i.test(file.name)) {
                e.preventDefault();
                switchTab("upload");
                handleFileUpload(file);
                return;
            }
        }

        // 2. Check if text pasted is URL or local path
        if (e.clipboardData && activeTag !== "input" && activeTag !== "textarea") {
            const pastedText = e.clipboardData.getData("text").trim();
            if (pastedText) {
                const isLocal = /^[a-zA-Z]:[\\\/]|\.(mp4|mov|mkv|avi|webm|m4v|ts|wmv|flv)$/i.test(pastedText);
                if (isLocal) {
                    e.preventDefault();
                    switchTab("upload");
                    localPathInput.value = pastedText;
                    analyzeVideo(pastedText);
                } else if (pastedText.startsWith("http://") || pastedText.startsWith("https://") || pastedText.includes("youtube.com") || pastedText.includes("youtu.be")) {
                    e.preventDefault();
                    switchTab("url");
                    videoUrlInput.value = pastedText;
                    analyzeVideo(pastedText);
                }
            }
        }
    });

    // Upload File Function with real-time XHR Progress
    function handleFileUpload(file) {
        if (!file) return;

        // UI Updates
        dropZonePrompt.classList.add("hidden");
        fileSelectedBox.classList.remove("hidden");
        uploadProgressContainer.classList.remove("hidden");

        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        selectedFileStatus.textContent = "Uploading to local studio...";
        selectedFileStatus.style.color = "var(--cyan)";

        uploadBarFill.style.width = "0%";
        uploadPercentText.textContent = "0%";
        uploadStatusText.textContent = `Uploading ${file.name}...`;

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload", true);
        xhr.setRequestHeader("X-Filename", encodeURIComponent(file.name));

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadBarFill.style.width = `${percent}%`;
                uploadPercentText.textContent = `${percent}%`;
                uploadStatusText.textContent = `Uploading: ${formatBytes(e.loaded)} / ${formatBytes(e.total)} (${percent}%)`;
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (data.error) {
                        alert("Upload error: " + data.error);
                        selectedFileStatus.textContent = "Upload Failed";
                        selectedFileStatus.style.color = "var(--danger)";
                        return;
                    }

                    uploadedFilePath = data.file_path;
                    currentVideoSource = data.file_path;

                    selectedFileStatus.textContent = "Uploaded ✓";
                    selectedFileStatus.style.color = "var(--success)";
                    uploadStatusText.textContent = "Upload Complete! Finding viral moments...";
                    uploadBarFill.style.width = "100%";

                    setTimeout(() => {
                        uploadProgressContainer.classList.add("hidden");
                    }, 1200);

                    // Auto-trigger video analysis on the uploaded file
                    analyzeVideo(data.file_path);

                } catch (err) {
                    alert("Error parsing server response: " + err.message);
                }
            } else {
                alert("Upload failed with status " + xhr.status);
                selectedFileStatus.textContent = "Upload Failed";
            }
        };

        xhr.onerror = () => {
            alert("Network error during file upload");
            selectedFileStatus.textContent = "Upload Failed";
        };

        xhr.send(file);
    }

    // ==========================================
    // UNIFIED VIDEO ANALYSIS ACTION (URL or File)
    // ==========================================
    async function analyzeVideo(customTarget = null) {
        const target = customTarget || (activeTab === "url" ? videoUrlInput.value.trim() : (uploadedFilePath || localPathInput.value.trim()));
        if (!target) {
            alert("Please provide a video URL or select a video file!");
            return;
        }

        currentVideoSource = target;

        analyzeBtn.disabled = true;
        if (analyzeFileBtn) analyzeFileBtn.disabled = true;
        analyzeSpinner.classList.remove("hidden");
        if (uploadAnalyzeSpinner) uploadAnalyzeSpinner.classList.remove("hidden");
        analyzeBtn.querySelector(".btn-text").textContent = "Analyzing Moments...";

        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: target,
                    file_path: target,
                    target_duration: targetDuration,
                    min_moments: targetClipCount
                })
            });

            const data = await response.json();
            if (data.error) {
                alert("Error analyzing video: " + data.error);
                return;
            }

            currentVideoData = data;

            // Update Header Meta
            if (data.thumbnail) {
                videoThumb.src = data.thumbnail;
                videoThumb.classList.remove("hidden");
            } else {
                videoThumb.classList.add("hidden");
            }
            videoTitle.textContent = data.title;
            videoAuthor.textContent = data.uploader;
            videoDuration.textContent = `⏱️ ${data.duration_fmt}`;
            if (detectedMomentsCount) {
                detectedMomentsCount.textContent = data.viral_moments ? data.viral_moments.length : 0;
            }

            // Populate Viral Moments
            momentsGrid.innerHTML = "";
            selectedMomentIds.clear();

            if (data.viral_moments && data.viral_moments.length > 0) {
                data.viral_moments.forEach((mom, idx) => {
                    selectedMomentIds.add(mom.id);
                    const card = document.createElement("div");
                    card.className = `moment-card ${idx === 0 ? 'selected' : ''}`;
                    card.dataset.id = mom.id;
                    card.innerHTML = `
                        <div class="moment-header-row">
                            <label class="moment-check-wrapper" onclick="event.stopPropagation()">
                                <input type="checkbox" class="moment-checkbox" data-id="${mom.id}" checked>
                                <span class="moment-badge">${mom.hook_badge}</span>
                            </label>
                            <span class="virality-score-pill">${mom.virality_score}% Viral</span>
                        </div>
                        <div class="moment-title">${mom.title}</div>
                        <div class="moment-hook-meta">
                            <span class="hook-driver-tag">🎯 ${mom.attention_point || 'High Retention Peak'}</span>
                            <span class="hook-sfx-tag">🔊 ${mom.recommended_sfx ? mom.recommended_sfx.toUpperCase().replace('_', ' ') : 'VINE BOOM'}</span>
                        </div>
                        <div class="moment-time-row">
                            <span>⏱️ ${mom.start_fmt} - ${mom.end_fmt} (${mom.duration}s)</span>
                        </div>
                        <div class="virality-bar-bg">
                            <div class="virality-bar-fill" style="width: ${mom.virality_score}%"></div>
                        </div>
                    `;

                    const cb = card.querySelector(".moment-checkbox");
                    cb.addEventListener("change", (e) => {
                        const id = parseInt(e.target.dataset.id, 10);
                        if (e.target.checked) {
                            selectedMomentIds.add(id);
                        } else {
                            selectedMomentIds.delete(id);
                        }
                        updateBatchSelectionUI();
                    });

                    card.addEventListener("click", () => {
                        document.querySelectorAll(".moment-card").forEach(c => c.classList.remove("selected"));
                        card.classList.add("selected");
                        startTimeInput.value = mom.start_fmt;
                        endTimeInput.value = mom.end_fmt;
                        
                        if (headerLine1 && mom.hook_line1) headerLine1.value = mom.hook_line1;
                        if (headerLine2 && mom.hook_line2) headerLine2.value = mom.hook_line2;
                        if (headerLine3 && mom.hook_line3) headerLine3.value = mom.hook_line3;
                        if (sfxSelect && mom.recommended_sfx) sfxSelect.value = mom.recommended_sfx;
                        updateHeaderPreview();
                        updateDurationDisplay();
                    });

                    momentsGrid.appendChild(card);
                });

                // Auto-select first moment for single preview
                const firstMom = data.viral_moments[0];
                startTimeInput.value = firstMom.start_fmt;
                endTimeInput.value = firstMom.end_fmt;
                if (headerLine1 && firstMom.hook_line1) headerLine1.value = firstMom.hook_line1;
                if (headerLine2 && firstMom.hook_line2) headerLine2.value = firstMom.hook_line2;
                if (headerLine3 && firstMom.hook_line3) headerLine3.value = firstMom.hook_line3;
                if (sfxSelect && firstMom.recommended_sfx) sfxSelect.value = firstMom.recommended_sfx;
                updateHeaderPreview();
                updateDurationDisplay();
                updateBatchSelectionUI();
            }

            videoDetailsCard.classList.remove("hidden");
            customizerSection.classList.remove("hidden");
            resultCard.classList.add("hidden");

        } catch (err) {
            alert("Failed to connect to studio server: " + err.message);
        } finally {
            analyzeBtn.disabled = false;
            if (analyzeFileBtn) analyzeFileBtn.disabled = false;
            analyzeSpinner.classList.add("hidden");
            if (uploadAnalyzeSpinner) uploadAnalyzeSpinner.classList.add("hidden");
            analyzeBtn.querySelector(".btn-text").textContent = "✨ Find Viral Moments";
        }
    }

    analyzeBtn.addEventListener("click", () => analyzeVideo());

    // Switch active short in the multi-short showcase
    function displayActiveShort(index) {
        if (!generatedShortsData || generatedShortsData.length === 0) return;
        activeShortIndex = Math.max(0, Math.min(index, generatedShortsData.length - 1));
        const activeShort = generatedShortsData[activeShortIndex];

        // Update tab buttons
        document.querySelectorAll(".tab-btn").forEach((t, i) => {
            if (i === activeShortIndex) {
                t.classList.add("active");
            } else {
                t.classList.remove("active");
            }
        });

        // Update Player & Download
        resultVideo.src = activeShort.download_url;
        downloadBtn.href = activeShort.download_url;
        downloadBtn.download = activeShort.video_filename;
        downloadBtn.textContent = `⬇️ Download Short #${activeShortIndex + 1} (${activeShort.duration}s MP4)`;

        // Update Metadata
        activeShortMetaTitle.textContent = `🔥 Short #${activeShortIndex + 1}: ${activeShort.title || 'Viral Clip'}`;
        if (activeShortBadge) {
            activeShortBadge.textContent = activeShort.hook_badge || `${activeShort.duration}s • 1080x1920`;
        }
        suggestedTitleInput.value = activeShort.suggested_title || "";
        suggestedDescArea.value = activeShort.suggested_description || "";
        suggestedTagsInput.value = (activeShort.suggested_tags || []).join(" ");
    }

    // Render result tabs
    function populateResultShowcase(shortsList, zipDownloadUrl) {
        generatedShortsData = shortsList;
        shortsTabStrip.innerHTML = "";

        if (shortsList.length > 1 && zipDownloadUrl) {
            downloadAllZipBtn.classList.remove("hidden");
            downloadAllZipBtn.href = zipDownloadUrl;
            downloadAllZipBtn.textContent = `📦 Download All ${shortsList.length} Shorts (.ZIP)`;
        } else {
            downloadAllZipBtn.classList.add("hidden");
        }

        resultHeaderTitle.textContent = shortsList.length > 1
            ? `🎉 ${shortsList.length} Viral Shorts Ready!`
            : `🎉 Viral Short Generated!`;

        shortsList.forEach((s, idx) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `tab-btn ${idx === 0 ? 'active' : ''}`;
            btn.innerHTML = `
                <span>Short #${idx + 1}</span>
                <span class="tab-badge">${s.duration}s</span>
            `;
            btn.addEventListener("click", () => displayActiveShort(idx));
            shortsTabStrip.appendChild(btn);
        });

        displayActiveShort(0);
        progressCard.classList.add("hidden");
        resultCard.classList.remove("hidden");
        resultCard.scrollIntoView({ behavior: 'smooth' });
    }

    // Job Polling & UI Helpers
    function stopJobPolling() {
        if (jobPollTimer) {
            clearInterval(jobPollTimer);
            jobPollTimer = null;
        }
        if (jobTimeTimer) {
            clearInterval(jobTimeTimer);
            jobTimeTimer = null;
        }
    }

    function resetGenerationButtons() {
        generateBtn.disabled = false;
        if (batchGenerateBtn) batchGenerateBtn.disabled = false;
        genSpinner.classList.add("hidden");
        if (batchGenSpinner) batchGenSpinner.classList.add("hidden");
        if (cancelJobBtn) {
            cancelJobBtn.disabled = false;
            cancelJobBtn.textContent = "✖ Cancel Job";
        }
    }

    function updateStepIndicators(progress) {
        stepItems.forEach((st, i) => {
            if (!st) return;
            if (progress >= 95) {
                st.classList.add("active");
            } else if (i === 0 && progress >= 5) {
                st.classList.add("active");
            } else if (i === 1 && progress >= 25) {
                st.classList.add("active");
            } else if (i === 2 && progress >= 50) {
                st.classList.add("active");
            } else if (i === 3 && progress >= 85) {
                st.classList.add("active");
            } else if (i > 0 && progress < (i * 25)) {
                st.classList.remove("active");
            }
        });
    }

    function startJobTracking(jobId, jobType, initialStatusText, batchDetail) {
        currentJobId = jobId;
        stopJobPolling();

        progressCard.classList.remove("hidden");
        resultCard.classList.add("hidden");
        generateBtn.disabled = true;
        if (batchGenerateBtn) batchGenerateBtn.disabled = true;
        if (jobType === "batch") {
            batchGenSpinner.classList.remove("hidden");
        } else {
            genSpinner.classList.remove("hidden");
        }
        if (cancelJobBtn) {
            cancelJobBtn.disabled = false;
            cancelJobBtn.textContent = "✖ Cancel Job";
        }

        progressStatusText.textContent = initialStatusText;
        if (progressBatchIndicator && batchDetail) {
            progressBatchIndicator.textContent = batchDetail;
        }
        progressBarFill.style.width = "5%";
        if (progressPercentBadge) progressPercentBadge.textContent = "5%";

        stepItems.forEach((st, idx) => {
            if (st) {
                if (idx === 0) st.classList.add("active");
                else st.classList.remove("active");
            }
        });

        // Elapsed time ticker
        jobStartTime = Date.now();
        if (progressTime) {
            progressTime.textContent = "0s elapsed";
            jobTimeTimer = setInterval(() => {
                if (!jobStartTime) return;
                const elapsedSec = Math.floor((Date.now() - jobStartTime) / 1000);
                const m = Math.floor(elapsedSec / 60);
                const s = elapsedSec % 60;
                progressTime.textContent = m > 0 ? `${m}m ${s}s elapsed` : `${s}s elapsed`;
            }, 1000);
        }

        // Poll every 2 seconds
        jobPollTimer = setInterval(async () => {
            if (!currentJobId) return;
            try {
                const res = await fetch(`/api/jobs/${currentJobId}`);
                if (!res.ok) {
                    if (res.status === 404) {
                        stopJobPolling();
                        resetGenerationButtons();
                        progressCard.classList.add("hidden");
                        alert("Job not found on server.");
                        return;
                    }
                    return;
                }
                const job = await res.json();

                // Update progress percentage and stage
                const pct = Math.max(5, Math.min(100, job.progress || 0));
                progressBarFill.style.width = `${pct}%`;
                if (progressPercentBadge) progressPercentBadge.textContent = `${pct}%`;

                if (job.stage) {
                    progressStatusText.textContent = job.stage;
                    if (jobType === "batch" && job.stage.includes("Short ")) {
                        progressBatchIndicator.textContent = job.stage;
                    }
                }

                updateStepIndicators(pct);

                if (job.status === "completed") {
                    stopJobPolling();
                    progressBarFill.style.width = "100%";
                    if (progressPercentBadge) progressPercentBadge.textContent = "100%";
                    stepItems.forEach(st => st && st.classList.add("active"));

                    setTimeout(() => {
                        resetGenerationButtons();
                        const outputs = job.outputs || [];
                        const zipUrl = job.zip_download_url || job.secure_zip_download_url;
                        populateResultShowcase(outputs, zipUrl);
                    }, 500);

                } else if (job.status === "failed") {
                    stopJobPolling();
                    resetGenerationButtons();
                    progressCard.classList.add("hidden");
                    alert("Video generation failed: " + (job.error_message || "Unknown processing error"));

                } else if (job.status === "cancelled") {
                    stopJobPolling();
                    resetGenerationButtons();
                    progressCard.classList.add("hidden");
                    alert("Job was cancelled.");
                }

            } catch (pollErr) {
                console.warn("[JobQueue] Polling error:", pollErr);
            }
        }, 2000);
    }

    // Cancel Active Background Job
    if (cancelJobBtn) {
        cancelJobBtn.addEventListener("click", async () => {
            if (!currentJobId) return;
            cancelJobBtn.disabled = true;
            cancelJobBtn.textContent = "Cancelling...";
            try {
                const res = await fetch(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
                const data = await res.json();
                console.log("[JobQueue] Cancel request:", data);
                if (data.status === "cancelled") {
                    stopJobPolling();
                    resetGenerationButtons();
                    progressCard.classList.add("hidden");
                    alert("Job cancelled successfully.");
                }
            } catch (err) {
                console.error("Cancel request failed:", err);
            }
        });
    }

    // Generate Single 9:16 Short (Asynchronous Background Job)
    generateBtn.addEventListener("click", async () => {
        const target = currentVideoSource || videoUrlInput.value.trim();
        const startTime = startTimeInput.value.trim();
        const endTime = endTimeInput.value.trim();

        const l1 = headerLine1 ? headerLine1.value.trim() : "";
        const l2 = headerLine2 ? headerLine2.value.trim() : "";
        const l3 = headerLine3 ? headerLine3.value.trim() : "";
        const headerLines = [l1, l2, l3].filter(Boolean);
        const topHook = headerLines.join("\n") || (topHookInput ? topHookInput.value.trim() : "WAIT TILL THE END 😱");

        const sfxEnabled = sfxToggle ? sfxToggle.checked : true;
        const sfxHook = sfxSelect ? sfxSelect.value : "vine_boom";
        const dynamicZoom = zoomToggle ? zoomToggle.checked : true;
        const highQuality = qualityToggle ? qualityToggle.checked : true;
        const copyrightShield = shieldToggle ? shieldToggle.checked : true;

        if (!target) {
            alert("Please provide a video URL or local file");
            return;
        }

        try {
            const response = await fetch("/api/jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    type: "single",
                    url: target,
                    file_path: target,
                    start_time: startTime,
                    end_time: endTime,
                    layout: selectedLayout,
                    subtitle_style: selectedStyle,
                    top_hook: topHook,
                    header_lines: headerLines,
                    sfx_enabled: sfxEnabled,
                    sfx_hook: sfxHook,
                    dynamic_zoom: dynamicZoom,
                    high_quality: highQuality,
                    copyright_shield: copyrightShield
                })
            });

            const data = await response.json();
            if (!response.ok || data.error) {
                alert("Error submitting generation job: " + (data.error || "Server error"));
                resetGenerationButtons();
                progressCard.classList.add("hidden");
                return;
            }

            const jobId = data.job_id || (data.job && data.job.id);
            startJobTracking(
                jobId,
                "single",
                "Queued: Rendering 9:16 Short with 3D Subtitles...",
                `Target: ${startTime} -> ${endTime} | 3D: ${selectedStyle.toUpperCase()} | SFX: ${sfxEnabled ? sfxHook.toUpperCase() : 'OFF'}`
            );

        } catch (err) {
            alert("Failed to submit job to studio: " + err.message);
            resetGenerationButtons();
            progressCard.classList.add("hidden");
        }
    });

    // Batch Generate All Selected Shorts (Asynchronous Background Job)
    if (batchGenerateBtn) {
        batchGenerateBtn.addEventListener("click", async () => {
            const target = currentVideoSource || videoUrlInput.value.trim();
            if (!target) {
                alert("Please provide a video URL or local file");
                return;
            }

            if (!currentVideoData || !currentVideoData.viral_moments) {
                alert("Please find viral moments first!");
                return;
            }

            const selectedClips = currentVideoData.viral_moments.filter(m => selectedMomentIds.has(m.id));
            if (selectedClips.length === 0) {
                alert("Please select at least 1 moment to generate!");
                return;
            }

            const l1 = headerLine1 ? headerLine1.value.trim() : "";
            const l2 = headerLine2 ? headerLine2.value.trim() : "";
            const l3 = headerLine3 ? headerLine3.value.trim() : "";
            const headerLines = [l1, l2, l3].filter(Boolean);

            const sfxEnabled = sfxToggle ? sfxToggle.checked : true;
            const sfxHook = sfxSelect ? sfxSelect.value : "vine_boom";
            const dynamicZoom = zoomToggle ? zoomToggle.checked : true;
            const highQuality = qualityToggle ? qualityToggle.checked : true;
            const copyrightShield = shieldToggle ? shieldToggle.checked : true;

            const total = selectedClips.length;

            try {
                const response = await fetch("/api/jobs", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        type: "batch",
                        url: target,
                        file_path: target,
                        clips: selectedClips,
                        layout: selectedLayout,
                        subtitle_style: selectedStyle,
                        header_lines: headerLines,
                        sfx_enabled: sfxEnabled,
                        sfx_hook: sfxHook,
                        dynamic_zoom: dynamicZoom,
                        high_quality: highQuality,
                        copyright_shield: copyrightShield
                    })
                });

                const data = await response.json();
                if (!response.ok || data.error) {
                    alert("Error submitting batch job: " + (data.error || "Server error"));
                    resetGenerationButtons();
                    progressCard.classList.add("hidden");
                    return;
                }

                const jobId = data.job_id || (data.job && data.job.id);
                startJobTracking(
                    jobId,
                    "batch",
                    `Queued: Batch Rendering ${total} Viral Shorts...`,
                    `Short 1 of ${total}: "${selectedClips[0].title}" (${selectedClips[0].duration}s)`
                );

            } catch (err) {
                alert("Batch submission error: " + err.message);
                resetGenerationButtons();
                progressCard.classList.add("hidden");
            }
        });
    }

    // Auto-analyze initial video on load if default URL present
    if (videoUrlInput.value) {
        analyzeVideo(videoUrlInput.value.trim());
    }
});

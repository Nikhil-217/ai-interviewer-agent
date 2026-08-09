/* -----------------------------------------------------------------------------
   AI Interview Agent - Single Page Application Frontend orchestrator
   ----------------------------------------------------------------------------- */

(function() {
    // 1. Core State
    let state = {
        apiBaseUrl: localStorage.getItem("api_base_url") || window.location.origin,
        sessionId: "",
        candidate: null,
        loading: false,
        candidatesList: []
    };

    // 2. DOM Selectors
    const viewLanding = document.getElementById("view-landing");
    const viewChat = document.getElementById("view-chat");
    const viewFeedback = document.getElementById("view-feedback");
    
    const candidateSelect = document.getElementById("candidate-select");
    const customJsonInput = document.getElementById("custom-json-input");
    const candidateSummary = document.getElementById("candidate-summary");
    const startInterviewBtn = document.getElementById("start-interview-btn");
    const landingError = document.getElementById("landing-error");
    
    // Summary info nodes
    const candRole = document.getElementById("cand-role");
    const candExp = document.getElementById("cand-exp");
    const candEdu = document.getElementById("cand-edu");
    const candMissions = document.getElementById("cand-missions");
    const candCommits = document.getElementById("cand-commits");

    // Chat nodes
    const chatMessages = document.getElementById("chat-messages");
    const chatInput = document.getElementById("chat-input");
    const chatForm = document.getElementById("chat-form");
    const sendBtn = document.getElementById("send-btn");
    const chatError = document.getElementById("chat-error");
    const typingIndicator = document.getElementById("typing-indicator");
    const statusBadge = document.getElementById("status-badge");

    // Feedback nodes
    const feedbackSummaryText = document.getElementById("feedback-summary-text");
    const overallScoreText = document.getElementById("overall-score");
    const topicsMasteredList = document.getElementById("topics-mastered-list");
    const topicsReviewList = document.getElementById("topics-review-list");
    const strengthsList = document.getElementById("strengths-list");
    const gapsList = document.getElementById("gaps-list");
    const nextList = document.getElementById("next-list");
    const restartBtn = document.getElementById("restart-btn");

    // Settings nodes
    const openSettingsBtn = document.getElementById("open-settings-btn");
    const closeSettingsBtn = document.getElementById("close-settings-btn");
    const settingsModal = document.getElementById("settings-modal");
    const settingsApiUrl = document.getElementById("settings-api-url");
    const saveSettingsBtn = document.getElementById("save-settings-btn");

    // 3. Helper Functions
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    function switchView(panel) {
        [viewLanding, viewChat, viewFeedback].forEach(p => {
            p.classList.add("hidden");
            p.classList.remove("active");
        });
        panel.classList.remove("hidden");
        panel.classList.add("active");
    }

    function clearErrors() {
        landingError.classList.add("hidden");
        landingError.textContent = "";
        chatError.classList.add("hidden");
        chatError.textContent = "";
    }

    // 4. API Requests
    async function loadCandidates() {
        try {
            const res = await fetch(`${state.apiBaseUrl}/api/candidates`);
            if (!res.ok) throw new Error("Failed to retrieve candidate profiles.");
            
            const candidates = await res.json();
            state.candidatesList = candidates;
            
            candidateSelect.innerHTML = '<option value="" disabled selected>Choose a profile...</option>';
            candidates.forEach((c, idx) => {
                const opt = document.createElement("option");
                opt.value = idx;
                opt.textContent = `${c.member.name} (${c.member.jobRole})`;
                candidateSelect.appendChild(opt);
            });
        } catch (e) {
            console.error(e);
            candidateSelect.innerHTML = '<option value="" disabled>Error loading candidates</option>';
            landingError.textContent = `Unable to connect to backend at ${state.apiBaseUrl}. Please check settings.`;
            landingError.classList.remove("hidden");
        }
    }

    function renderMessage(role, text) {
        const bubble = document.createElement("div");
        bubble.className = `msg-bubble ${role}`;
        
        const meta = document.createElement("div");
        meta.className = "bubble-meta";
        meta.textContent = role === "assistant" ? "AI Technical Interviewer" : "Candidate Response";
        
        const content = document.createElement("div");
        content.className = "bubble-content";
        content.textContent = text;
        
        bubble.appendChild(meta);
        bubble.appendChild(content);
        chatMessages.appendChild(bubble);
        
        // Auto Scroll to newest
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 5. Handlers
    candidateSelect.addEventListener("change", function() {
        clearErrors();
        customJsonInput.value = ""; // clear custom input
        
        const idx = parseInt(this.value, 10);
        const cand = state.candidatesList[idx];
        if (!cand) return;
        
        state.candidate = cand;
        
        // Populate display summary
        candRole.textContent = cand.member.jobRole;
        candExp.textContent = `${cand.member.yearsExperience} Year(s)`;
        candEdu.textContent = cand.member.education;
        candMissions.textContent = cand.missions ? cand.missions.length : 0;
        candCommits.textContent = cand.signals ? cand.signals.commitDays : 0;
        
        candidateSummary.classList.remove("hidden");
    });

    customJsonInput.addEventListener("input", function() {
        clearErrors();
        if (this.value.trim() !== "") {
            candidateSelect.value = ""; // reset dropdown selection
            candidateSummary.classList.add("hidden");
            state.candidate = null;
        }
    });

    startInterviewBtn.addEventListener("click", async function() {
        clearErrors();
        
        let candidateProfile = null;
        
        // Check dropdown select first
        if (state.candidate) {
            candidateProfile = state.candidate;
        } else {
            // Read from custom JSON textbox
            const rawJson = customJsonInput.value.trim();
            if (!rawJson) {
                landingError.textContent = "Please select a candidate profile or paste a custom JSON profile.";
                landingError.classList.remove("hidden");
                return;
            }
            
            try {
                candidateProfile = JSON.parse(rawJson);
            } catch (e) {
                landingError.textContent = "Invalid Candidate JSON formatting. Please check syntax.";
                landingError.classList.remove("hidden");
                return;
            }
        }
        
        // Reset and generate session variables
        state.sessionId = generateUUID();
        state.loading = true;
        
        startInterviewBtn.disabled = true;
        startInterviewBtn.classList.add("loading");
        
        // Post Start request to backend
        try {
            const response = await fetch(`${state.apiBaseUrl}/api/interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sessionId: state.sessionId,
                    candidate: candidateProfile
                })
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "HTTP start request failed.");
            }
            
            const data = await response.json();
            
            // Clean view list and switch
            chatMessages.innerHTML = "";
            renderMessage("assistant", data.reply);
            
            switchView(viewChat);
            statusBadge.textContent = "Interview Active";
            statusBadge.classList.add("active");
            
            chatInput.focus();
        } catch (e) {
            console.error(e);
            landingError.textContent = `Start failed: ${e.message}`;
            landingError.classList.remove("hidden");
        } finally {
            state.loading = false;
            startInterviewBtn.disabled = false;
            startInterviewBtn.classList.remove("loading");
        }
    });

    chatForm.addEventListener("submit", async function(event) {
        event.preventDefault();
        if (state.loading) return;
        
        clearErrors();
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Render user answer bubble
        renderMessage("user", message);
        chatInput.value = "";
        
        state.loading = true;
        chatInput.disabled = true;
        sendBtn.disabled = true;
        typingIndicator.classList.remove("hidden");
        
        try {
            const response = await fetch(`${state.apiBaseUrl}/api/interview`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sessionId: state.sessionId,
                    message: message
                })
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server communication failed.");
            }
            
            const data = await response.json();
            
            // Render interviewer answer bubble
            renderMessage("assistant", data.reply);
            
            if (data.done) {
                // Shift to feedback
                renderFeedback(data.feedback);
                setTimeout(() => {
                    switchView(viewFeedback);
                    statusBadge.textContent = "Interview Completed";
                    statusBadge.classList.remove("active");
                }, 2000); // 2 second delay to let the candidate see the final message bubble
            }
        } catch (e) {
            console.error(e);
            chatError.textContent = `Connection error: ${e.message}`;
            chatError.classList.remove("hidden");
        } finally {
            state.loading = false;
            chatInput.disabled = false;
            sendBtn.disabled = false;
            typingIndicator.classList.add("hidden");
            chatInput.focus();
        }
    });

    function renderFeedback(feedback) {
        if (!feedback) return;
        
        feedbackSummaryText.textContent = feedback.concise_interviewer_summary || "No summary provided.";
        overallScoreText.textContent = feedback.overall_score !== undefined ? feedback.overall_score : "-";
        
        // Helper to fill list
        const populateList = (element, items) => {
            element.innerHTML = "";
            if (!items || items.length === 0) {
                const li = document.createElement("li");
                li.textContent = "No specific items recorded.";
                element.appendChild(li);
            } else {
                items.forEach(item => {
                    const li = document.createElement("li");
                    li.textContent = item;
                    element.appendChild(li);
                });
            }
        };

        // Helper to fill pills
        const populatePills = (element, items, typeClass) => {
            element.innerHTML = "";
            if (!items || items.length === 0) {
                element.innerHTML = "<em>None</em>";
            } else {
                items.forEach(item => {
                    const span = document.createElement("span");
                    span.className = `topic-pill ${typeClass}`;
                    span.textContent = item;
                    element.appendChild(span);
                });
            }
        };
        
        populatePills(topicsMasteredList, feedback.topics_mastered, "pill-mastered");
        populatePills(topicsReviewList, feedback.topics_needing_review, "pill-review");

        populateList(strengthsList, feedback.strengths);
        populateList(gapsList, feedback.weaknesses);
        populateList(nextList, feedback.recommended_next_steps);
    }

    restartBtn.addEventListener("click", function() {
        state.sessionId = "";
        state.candidate = null;
        state.loading = false;
        
        candidateSelect.value = "";
        customJsonInput.value = "";
        candidateSummary.classList.add("hidden");
        statusBadge.textContent = "Simulator Idle";
        
        clearErrors();
        switchView(viewLanding);
        loadCandidates();
    });

    // 6. Settings Modal Handlers
    openSettingsBtn.addEventListener("click", function() {
        settingsApiUrl.value = state.apiBaseUrl;
        settingsModal.classList.remove("hidden");
    });

    const closeModal = () => settingsModal.classList.add("hidden");
    closeSettingsBtn.addEventListener("click", closeModal);
    
    saveSettingsBtn.addEventListener("click", function() {
        let val = settingsApiUrl.value.trim();
        if (val.endsWith("/")) {
            val = val.slice(0, -1);
        }
        if (!val) {
            val = window.location.origin;
        }
        
        state.apiBaseUrl = val;
        localStorage.setItem("api_base_url", val);
        closeModal();
        clearErrors();
        loadCandidates();
    });

    // 7. Initial Startup Execution
    settingsApiUrl.value = state.apiBaseUrl;
    loadCandidates();
})();

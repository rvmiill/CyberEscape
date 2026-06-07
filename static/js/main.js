let score = 0;
let hintsUsed = 0;
let timer = 120;
let timerInterval = null;
let gate1Correct = 0;
let gate2Correct = 0;
let gate3Correct = 0;
let stageStarted = false;

let level1Rewards = {
    extra_password_hint: 0,
    level1_time_boost: 0,
    level1_mistake_shield: 0
};

let mistakeShieldActive = false;
let timeBoostUsedThisRun = false;

/* =========================
   SOUND SYSTEM
========================= */

const gameSounds = {
    click: new Audio("/static/audio/click.mp3"),
    correct: new Audio("/static/audio/correct.mp3"),
    wrong: new Audio("/static/audio/wrong.mp3"),
    coin: new Audio("/static/audio/coin.mp3"),
    reward: new Audio("/static/audio/reward.mp3"),
    complete: new Audio("/static/audio/complete.mp3"),
    shield: new Audio("/static/audio/shield.mp3"),
    alert: new Audio("/static/audio/alert.mp3"),
    success: new Audio("/static/audio/success.mp3")
};

function playSound(name) {
    if (!gameSounds[name]) return;

    try {
        gameSounds[name].currentTime = 0;
        gameSounds[name].volume = 0.45;
        gameSounds[name].play().catch(() => {});
    } catch (error) {
        console.log("Sound error:", error);
    }
}

/* Plays click sound for normal buttons */
document.addEventListener("click", function (event) {
    if (event.target.closest("button") || event.target.closest("a")) {
        playSound("click");
    }
});

const hints = [
    "Longer passwords are harder to crack.",
    "Common words make passwords weaker.",
    "Easy number patterns like 123 are risky.",
    "A strong password should mix character types.",
    "Strong passwords avoid predictable words and sequences."
];

function togglePassword(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (!input || !iconElement) return;

    const icon = iconElement.querySelector("i");

    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    } else {
        input.type = "password";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const title = document.querySelector(".game-title");

    if (title) {
        setInterval(() => {
            title.style.opacity = "0.96";
            setTimeout(() => {
                title.style.opacity = "1";
            }, 120);
        }, 2200);
    }

    const isLevel1Page =
        document.getElementById("introScreen") ||
        document.getElementById("stage1Screen") ||
        document.getElementById("completeGate1Btn");

    if (isLevel1Page) {
        loadLevel1Rewards();
    }
});

function setLearningNote(noteId, message) {
    const noteEl = document.getElementById(noteId);
    if (noteEl) {
        noteEl.innerHTML = `<strong>Learning:</strong> ${message}`;
    }
}

function setSideLesson(message) {
    const sideLesson = document.getElementById("sideLessonText");
    if (sideLesson) {
        sideLesson.textContent = message;
    }
}

/* =========================
   LEVEL 1 REWARD SYSTEM
========================= */

function loadLevel1Rewards() {
    fetch("/api/level_rewards/1")
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                level1Rewards = data.rewards;
                createLevel1RewardPanel();
                updateLevel1RewardPanel();
            }
        })
        .catch(error => {
            console.error("Error loading Level 1 rewards:", error);
        });
}

function createLevel1RewardPanel() {
    const isLevel1Page =
        document.getElementById("introScreen") ||
        document.getElementById("stage1Screen") ||
        document.getElementById("completeGate1Btn");

    if (!isLevel1Page) return;
    if (document.getElementById("level1RewardPanel")) return;

    const panel = document.createElement("div");
    panel.id = "level1RewardPanel";

    panel.innerHTML = `
        <div class="reward-panel-title">
            <i class="fa-solid fa-store"></i>
            Level 1 Reward Items
        </div>

        <button class="reward-use-btn" id="extraHintRewardBtn" onclick="useExtraPasswordHint()">
            💡 Extra Hint Token
            <span id="extraHintCount">0</span>
        </button>

        <button class="reward-use-btn" id="timeBoostRewardBtn" onclick="useTimeBoost()">
            ⏱️ Time Boost +20s
            <span id="timeBoostCount">0</span>
        </button>

        <button class="reward-use-btn" id="mistakeShieldRewardBtn" onclick="useMistakeShield()">
            🛡️ Mistake Shield
            <span id="mistakeShieldCount">0</span>
        </button>
    `;

    const sidebar =
        document.querySelector(".side-panel") ||
        document.querySelector(".mission-panel") ||
        document.querySelector(".game-sidebar") ||
        document.querySelector(".level-sidebar");

    if (sidebar) {
        sidebar.appendChild(panel);
    } else {
        document.body.appendChild(panel);
        panel.classList.add("floating-reward-panel");
    }

    if (!document.getElementById("level1RewardStyle")) {
        const style = document.createElement("style");
        style.id = "level1RewardStyle";

        style.textContent = `
            #level1RewardPanel {
                margin-top: 16px;
                background: rgba(5, 12, 30, 0.95);
                border: 1px solid rgba(255, 216, 107, 0.55);
                border-radius: 18px;
                padding: 14px;
                box-shadow: 0 0 22px rgba(255, 216, 107, 0.12);
                position: relative;
                z-index: 5;
            }

            #level1RewardPanel.floating-reward-panel {
                position: fixed;
                right: 18px;
                top: 95px;
                width: 285px;
                z-index: 2000;
            }

            .reward-panel-title {
                color: #ffd86b;
                font-weight: 900;
                font-size: 18px;
                margin-bottom: 12px;
            }

            .reward-use-btn {
                width: 100%;
                border: 1px solid rgba(0, 207, 255, 0.35);
                border-radius: 12px;
                padding: 11px 12px;
                margin-bottom: 8px;
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                font-weight: 800;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 8px;
            }

            .reward-use-btn:hover {
                background: rgba(0, 207, 255, 0.14);
            }

            .reward-use-btn:disabled {
                opacity: 0.45;
                cursor: not-allowed;
            }

            .reward-use-btn span {
                background: rgba(255, 216, 107, 0.16);
                border: 1px solid rgba(255, 216, 107, 0.55);
                color: #ffd86b;
                border-radius: 999px;
                padding: 4px 9px;
                min-width: 34px;
                text-align: center;
            }

            .reward-toast {
                position: fixed;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                background:
                    radial-gradient(circle at top, rgba(255,216,107,0.22), transparent 42%),
                    rgba(5, 12, 30, 0.98);
                border: 2px solid rgba(255, 216, 107, 0.85);
                border-radius: 22px;
                padding: 22px 28px;
                color: white;
                text-align: center;
                z-index: 99999;
                box-shadow: 0 0 40px rgba(255,216,107,0.25);
                animation: rewardToastPop 0.3s ease forwards;
                max-width: calc(100% - 40px);
            }

            .reward-toast h3 {
                margin: 0 0 8px;
                color: #00ff88;
            }

            .reward-toast p {
                margin: 0;
                color: #b8d7e8;
                line-height: 1.5;
            }

            @keyframes rewardToastPop {
                from {
                    opacity: 0;
                    transform: translate(-50%, -50%) scale(0.82);
                }
                to {
                    opacity: 1;
                    transform: translate(-50%, -50%) scale(1);
                }
            }
        `;

        document.head.appendChild(style);
    }
}

function updateLevel1RewardPanel() {
    const extraHintCount = document.getElementById("extraHintCount");
    const timeBoostCount = document.getElementById("timeBoostCount");
    const mistakeShieldCount = document.getElementById("mistakeShieldCount");

    const extraHintBtn = document.getElementById("extraHintRewardBtn");
    const timeBoostBtn = document.getElementById("timeBoostRewardBtn");
    const mistakeShieldBtn = document.getElementById("mistakeShieldRewardBtn");

    if (extraHintCount) extraHintCount.textContent = level1Rewards.extra_password_hint || 0;
    if (timeBoostCount) timeBoostCount.textContent = level1Rewards.level1_time_boost || 0;
    if (mistakeShieldCount) mistakeShieldCount.textContent = level1Rewards.level1_mistake_shield || 0;

    if (extraHintBtn) extraHintBtn.disabled = (level1Rewards.extra_password_hint || 0) <= 0;
    if (timeBoostBtn) timeBoostBtn.disabled = (level1Rewards.level1_time_boost || 0) <= 0 || timeBoostUsedThisRun;
    if (mistakeShieldBtn) mistakeShieldBtn.disabled = (level1Rewards.level1_mistake_shield || 0) <= 0 || mistakeShieldActive;
}

function consumeReward(itemKey, onSuccess) {
    fetch("/use_reward", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            item_key: itemKey
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            level1Rewards[itemKey] = data.remaining;
            updateLevel1RewardPanel();

            if (typeof onSuccess === "function") {
                onSuccess();
            }
        } else {
            playSound("wrong");
            showRewardToast("Reward Not Available", data.message || "You do not own this reward.");
            loadLevel1Rewards();
        }
    })
    .catch(error => {
        console.error("Error using reward:", error);
        playSound("wrong");
        showRewardToast("Reward Error", "Could not use this reward right now.");
    });
}

function useExtraPasswordHint() {
    if ((level1Rewards.extra_password_hint || 0) <= 0) return;

    consumeReward("extra_password_hint", () => {
        playSound("reward");

        const hintBox = document.getElementById("hintBox");
        const hintCountEl = document.getElementById("hintCount");

        const premiumHints = [
            "Premium Hint: A strong password should be at least 12 characters long.",
            "Premium Hint: Avoid using names, birthdays, and common words.",
            "Premium Hint: Mix uppercase letters, lowercase letters, numbers, and symbols.",
            "Premium Hint: Avoid easy patterns like 123, abc, qwerty, and password.",
            "Premium Hint: Use unique passwords for different accounts."
        ];

        const randomHint = premiumHints[Math.floor(Math.random() * premiumHints.length)];

        if (hintBox) {
            hintBox.textContent = randomHint;
            hintBox.style.display = "block";
        }

        hintsUsed += 1;

        if (hintCountEl) {
            hintCountEl.textContent = hintsUsed;
        }

        setSideLesson(randomHint);
        showRewardToast("Extra Hint Used", randomHint);
        updateLevel1RewardPanel();
    });
}

function useTimeBoost() {
    if ((level1Rewards.level1_time_boost || 0) <= 0 || timeBoostUsedThisRun) return;

    consumeReward("level1_time_boost", () => {
        playSound("reward");

        timeBoostUsedThisRun = true;
        timer += 20;

        const timerEl = document.getElementById("timer");
        if (timerEl) timerEl.textContent = timer;

        updateLevel1RewardPanel();
        showRewardToast("Time Boost Activated", "20 seconds have been added to the timer.");
        setSideLesson("Time boost used. Take a moment to think carefully about strong password rules.");
    });
}

function useMistakeShield() {
    if ((level1Rewards.level1_mistake_shield || 0) <= 0 || mistakeShieldActive) return;

    consumeReward("level1_mistake_shield", () => {
        playSound("shield");

        mistakeShieldActive = true;
        updateLevel1RewardPanel();
        showRewardToast("Mistake Shield Activated", "Your next wrong choice will not reduce your score.");
        setSideLesson("Mistake shield activated. It protects you from one wrong password decision penalty.");
    });
}

function applyWrongPenalty(points) {
    if (mistakeShieldActive) {
        mistakeShieldActive = false;
        playSound("shield");
        updateLevel1RewardPanel();
        showRewardToast("Shield Protected You", "Mistake Shield blocked the score penalty.");
        return;
    }

    score = Math.max(0, score - points);
}

function showRewardToast(title, message) {
    const oldToast = document.getElementById("rewardToast");
    if (oldToast) oldToast.remove();

    const toast = document.createElement("div");
    toast.id = "rewardToast";
    toast.className = "reward-toast";
    toast.innerHTML = `
        <h3>${title}</h3>
        <p>${message}</p>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 2200);
}

/* =========================
   LEVEL 1 GAMEPLAY
========================= */

function startStage1() {
    playSound("success");

    switchScreen("introScreen", "stage1Screen");
    setGateProgress("1 / 3");
    setObjective("Learn how to strengthen a weak password by choosing secure upgrades.");
    setSideLesson("Strong passwords should be long, unique, and difficult to guess.");

    if (!stageStarted) {
        stageStarted = true;
        startTimer();
    }
}

function startTimer() {
    timerInterval = setInterval(() => {
        timer--;
        const timerEl = document.getElementById("timer");
        if (timerEl) timerEl.textContent = timer;

        if (timer <= 0) {
            clearInterval(timerInterval);
            finishWithTimeout();
        }
    }, 1000);
}

function showHint() {
    const hintBox = document.getElementById("hintBox");
    const hintCountEl = document.getElementById("hintCount");

    if (!hintBox || !hintCountEl) return;

    playSound("reward");

    const randomHint = hints[Math.floor(Math.random() * hints.length)];
    hintBox.textContent = randomHint;

    hintsUsed += 1;
    score = Math.max(0, score - 5);

    hintCountEl.textContent = hintsUsed;
    updateScore();

    setSideLesson("Hints can help, but remembering password rules yourself builds stronger cybersecurity awareness.");
}

function selectUpgrade(button, isCorrect, message) {
    if (!button || button.classList.contains("selected-correct") || button.classList.contains("selected-wrong")) return;

    const feedback = document.getElementById("feedbackText");
    const lessonText = document.getElementById("lessonText1");
    const strengthFill = document.getElementById("strengthFill");
    const weakPassword = document.getElementById("weakPassword");

    if (isCorrect) {
        playSound("correct");

        button.classList.add("selected-correct");
        gate1Correct += 1;
        score += 20;

        if (feedback) feedback.textContent = "Correct. " + message;
        if (lessonText) {
            lessonText.textContent = "A strong password becomes safer when it uses more length and a better mix of uppercase letters, lowercase letters, numbers, and symbols.";
        }

        setSideLesson("Strong passwords are harder to guess because they avoid simple words and predictable patterns.");

        const width = Math.min(10 + gate1Correct * 18, 100);
        if (strengthFill) strengthFill.style.width = width + "%";

        if (gate1Correct >= 4) {
            if (weakPassword) weakPassword.textContent = "Dr@gon#X9!Secure";
            if (strengthFill) {
                strengthFill.style.background = "linear-gradient(90deg, #00ff5e, #00cfff)";
            }

            const btn = document.getElementById("completeGate1Btn");
            if (btn) btn.disabled = false;
        }
    } else {
        playSound("wrong");

        button.classList.add("selected-wrong");
        applyWrongPenalty(5);

        if (feedback) feedback.textContent = "Wrong. " + message;
        if (lessonText) {
            lessonText.textContent = "Weak choices such as repeated letters or simple patterns make passwords easier for attackers to guess or crack.";
        }

        setSideLesson("Avoid passwords that attackers can predict easily, such as repeated characters or common sequences.");
    }

    updateScore();
}

function goToStage2() {
    playSound("success");

    switchScreen("stage1Screen", "stage2Screen");
    setGateProgress("2 / 3");
    setObjective("Identify which passwords are safe and which ones are dangerous.");
    setSideLesson("A password can look complex but still be weak if it uses common words or keyboard patterns.");
}

function selectDoor(button, isSafe, message) {
    if (!button || button.classList.contains("selected-safe") || button.classList.contains("selected-trap")) return;

    const feedback = document.getElementById("feedbackText2");
    const lessonText = document.getElementById("lessonText2");

    if (isSafe) {
        playSound("correct");

        button.classList.add("selected-safe");
        gate2Correct += 1;
        score += 20;

        if (feedback) feedback.textContent = "Correct. " + message;
        if (lessonText) {
            lessonText.textContent = "Safe passwords avoid dictionary words, repeated patterns, and easy sequences like 123, abc, or qwerty.";
        }

        setSideLesson("Recognizing weak password patterns helps users make better real-life security decisions.");

        if (gate2Correct >= 3) {
            const btn = document.getElementById("completeGate2Btn");
            if (btn) btn.disabled = false;
        }
    } else {
        playSound("wrong");

        button.classList.add("selected-trap");
        applyWrongPenalty(5);

        if (feedback) feedback.textContent = "Trap door. " + message;
        if (lessonText) {
            lessonText.textContent = "Predictable passwords are risky because attackers often try the most common words and keyboard patterns first.";
        }

        setSideLesson("Common-looking passwords are often the first targets in guessing and dictionary attacks.");
    }

    updateScore();
}

function goToStage3() {
    playSound("success");

    switchScreen("stage2Screen", "stage3Screen");
    setGateProgress("3 / 3");
    setObjective("Build the strongest master password by avoiding personal and predictable information.");
    setSideLesson("Strong passwords should avoid names, birth years, and simple patterns.");
}

function selectPiece(button, isGood, message) {
    if (!button || button.classList.contains("selected-good") || button.classList.contains("selected-bad")) return;

    const feedback = document.getElementById("feedbackText3");
    const lessonText = document.getElementById("lessonText3");
    const masterKeyBox = document.getElementById("masterKeyBox");

    if (isGood) {
        playSound("correct");

        button.classList.add("selected-good");
        gate3Correct += 1;
        score += 20;

        if (feedback) feedback.textContent = "Correct. " + message;
        if (lessonText) {
            lessonText.textContent = "Strong passwords avoid personal details and combine unpredictable words, symbols, and mixed characters.";
        }

        setSideLesson("The strongest passwords do not use names, birthdays, or simple number patterns.");

        if (gate3Correct === 1 && masterKeyBox) masterKeyBox.textContent = "Tiger _ _ _";
        if (gate3Correct === 2 && masterKeyBox) masterKeyBox.textContent = "Tiger # _ _";
        if (gate3Correct === 3 && masterKeyBox) masterKeyBox.textContent = "Tiger # A!9 _";
        if (gate3Correct === 4 && masterKeyBox) masterKeyBox.textContent = "Tiger # A!9 Vault";

        if (gate3Correct >= 4) {
            const btn = document.getElementById("finishLevelBtn");
            if (btn) btn.disabled = false;
        }
    } else {
        playSound("wrong");

        button.classList.add("selected-bad");
        applyWrongPenalty(5);

        if (feedback) feedback.textContent = "Wrong. " + message;
        if (lessonText) {
            lessonText.textContent = "Names, birth years, common words, and easy number patterns make passwords easier to guess.";
        }

        setSideLesson("A password is weaker when it contains personal or predictable information.");
    }

    updateScore();
}

function completeLevel1() {
    clearInterval(timerInterval);

    playSound("complete");

    if (timer > 0) {
        score += Math.min(timer, 25);
        updateScore();
    }

    const completionTime = Math.max(0, 120 - timer);

    fetch("/save_level1_progress", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            score: score,
            hints_used: hintsUsed,
            completion_time: completionTime
        })
    })
    .then(response => response.json())
    .then(data => {
        switchScreen("stage3Screen", "resultScreen");

        const resultSummary = document.getElementById("resultSummary");
        const coinsEarned = data.coins_earned || 0;

        if (resultSummary) {
            if (data.success) {
                resultSummary.textContent =
                    `You completed all 3 gates with a final score of ${score}. Hints used: ${hintsUsed}. Time left: ${timer} seconds. Level 2 is now unlocked.`;
            } else {
                resultSummary.textContent =
                    `You completed all 3 gates with a final score of ${score}, but progress could not be saved. You still learned important password security rules.`;
            }
        }

        if (data.success && coinsEarned > 0) {
            showCoinPopup(coinsEarned);
        }

        setSideLesson("Real-life rule: use unique passwords for important accounts and avoid common words, names, and easy number patterns.");
    })
    .catch(error => {
        console.error("Error saving progress:", error);
        playSound("wrong");

        switchScreen("stage3Screen", "resultScreen");

        const resultSummary = document.getElementById("resultSummary");
        if (resultSummary) {
            resultSummary.textContent =
                `You completed all 3 gates with a final score of ${score}, but progress could not be saved. You still learned important password security rules.`;
        }

        setSideLesson("Real-life rule: use unique passwords for important accounts and avoid common words, names, and easy number patterns.");
    });
}

function showCoinPopup(coinsEarned) {
    playSound("coin");

    let popup = document.getElementById("coinRewardPopup");

    if (!popup) {
        popup = document.createElement("div");
        popup.id = "coinRewardPopup";
        popup.innerHTML = `
            <div class="coin-popup-card">
                <div class="coin-popup-icon">
                    <i class="fa-solid fa-coins"></i>
                </div>
                <h2>Cyber Coins Earned!</h2>
                <p>You received <strong>${coinsEarned}</strong> Cyber Coins.</p>
                <button onclick="closeCoinPopup()">Continue</button>
            </div>
        `;
        document.body.appendChild(popup);
    } else {
        popup.querySelector("p").innerHTML = `You received <strong>${coinsEarned}</strong> Cyber Coins.`;
    }

    popup.style.display = "flex";

    if (!document.getElementById("coinPopupStyle")) {
        const style = document.createElement("style");
        style.id = "coinPopupStyle";
        style.textContent = `
            #coinRewardPopup {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.72);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
                animation: coinOverlayFade 0.25s ease forwards;
            }

            .coin-popup-card {
                width: 420px;
                max-width: calc(100% - 40px);
                background:
                    radial-gradient(circle at top, rgba(255, 216, 107, 0.22), transparent 42%),
                    rgba(5, 12, 30, 0.98);
                border: 2px solid rgba(255, 216, 107, 0.75);
                border-radius: 26px;
                padding: 34px 26px;
                text-align: center;
                box-shadow: 0 0 45px rgba(255, 216, 107, 0.28);
                animation: coinPopupPop 0.35s ease forwards;
            }

            .coin-popup-icon {
                width: 82px;
                height: 82px;
                margin: 0 auto 16px;
                border-radius: 24px;
                background: rgba(255, 216, 107, 0.14);
                border: 1px solid rgba(255, 216, 107, 0.65);
                color: #ffd86b;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 38px;
                box-shadow: 0 0 28px rgba(255, 216, 107, 0.2);
            }

            .coin-popup-card h2 {
                margin: 0 0 12px;
                color: #00ff88;
                font-size: 30px;
            }

            .coin-popup-card p {
                margin: 0 0 22px;
                color: #b8d7e8;
                font-size: 18px;
                line-height: 1.5;
            }

            .coin-popup-card strong {
                color: #ffd86b;
                font-size: 24px;
            }

            .coin-popup-card button {
                border: none;
                border-radius: 14px;
                padding: 13px 24px;
                background: linear-gradient(135deg, #00ff88, #00cfff);
                color: #031126;
                font-weight: 900;
                font-size: 16px;
                cursor: pointer;
            }

            @keyframes coinOverlayFade {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes coinPopupPop {
                from {
                    opacity: 0;
                    transform: scale(0.84) translateY(18px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

function closeCoinPopup() {
    const popup = document.getElementById("coinRewardPopup");
    if (popup) {
        popup.style.display = "none";
    }
}

function finishWithTimeout() {
    playSound("alert");

    hideAllStageScreens();

    const result = document.getElementById("resultScreen");
    const resultSummary = document.getElementById("resultSummary");

    if (result) result.classList.add("active");

    if (resultSummary) {
        resultSummary.textContent =
            `Time is over. Your final score is ${score}. Try again and strengthen the fortress faster while remembering the password safety rules.`;
    }

    setSideLesson("Running out of time shows that recognizing strong password rules quickly is an important security skill.");
}

function resetStage2() {
    playSound("click");

    gate2Correct = 0;

    document.querySelectorAll(".door-card").forEach(card => {
        card.classList.remove("selected-safe", "selected-trap");
    });

    const feedback = document.getElementById("feedbackText2");
    const btn = document.getElementById("completeGate2Btn");
    const lessonText = document.getElementById("lessonText2");

    if (feedback) feedback.textContent = "Find all safe doors to move forward.";
    if (btn) btn.disabled = true;
    if (lessonText) {
        lessonText.textContent = "A password may look complex at first, but it can still be weak if it contains common words, famous keyboard patterns, or predictable combinations.";
    }

    setSideLesson("Safe passwords avoid common words, simple sequences, and predictable patterns.");
}

function resetStage3() {
    playSound("click");

    gate3Correct = 0;

    document.querySelectorAll(".piece-card").forEach(card => {
        card.classList.remove("selected-good", "selected-bad");
    });

    const feedback = document.getElementById("feedbackText3");
    const btn = document.getElementById("finishLevelBtn");
    const masterKeyBox = document.getElementById("masterKeyBox");
    const lessonText = document.getElementById("lessonText3");

    if (feedback) feedback.textContent = "Choose only the strongest password parts to unlock the fortress core.";
    if (btn) btn.disabled = true;
    if (masterKeyBox) masterKeyBox.textContent = "_ _ _ _";
    if (lessonText) {
        lessonText.textContent = "Strong passwords should avoid names, birth years, and simple number patterns. They should use less predictable words, symbols, and mixed character combinations.";
    }

    setSideLesson("Strong passwords should avoid names, birth years, and simple patterns.");
}

function resetLevel1() {
    playSound("click");

    gate1Correct = 0;
    gate2Correct = 0;
    gate3Correct = 0;
    score = 0;
    hintsUsed = 0;
    timer = 120;
    stageStarted = false;
    mistakeShieldActive = false;
    timeBoostUsedThisRun = false;

    clearInterval(timerInterval);

    document.querySelectorAll(".upgrade-card").forEach(card => {
        card.classList.remove("selected-correct", "selected-wrong");
    });

    document.querySelectorAll(".door-card").forEach(card => {
        card.classList.remove("selected-safe", "selected-trap");
    });

    document.querySelectorAll(".piece-card").forEach(card => {
        card.classList.remove("selected-good", "selected-bad");
    });

    const hintBox = document.getElementById("hintBox");
    const hintCount = document.getElementById("hintCount");
    const timerEl = document.getElementById("timer");
    const scoreEl = document.getElementById("score");
    const feedback1 = document.getElementById("feedbackText");
    const feedback2 = document.getElementById("feedbackText2");
    const feedback3 = document.getElementById("feedbackText3");
    const strengthFill = document.getElementById("strengthFill");
    const weakPassword = document.getElementById("weakPassword");
    const btn1 = document.getElementById("completeGate1Btn");
    const btn2 = document.getElementById("completeGate2Btn");
    const btn3 = document.getElementById("finishLevelBtn");
    const masterKeyBox = document.getElementById("masterKeyBox");
    const lessonText1 = document.getElementById("lessonText1");
    const lessonText2 = document.getElementById("lessonText2");
    const lessonText3 = document.getElementById("lessonText3");

    if (hintBox) hintBox.textContent = "Hint will appear here.";
    if (hintCount) hintCount.textContent = "0";
    if (timerEl) timerEl.textContent = "120";
    if (scoreEl) scoreEl.textContent = "0";
    if (feedback1) feedback1.textContent = "Choose upgrades to strengthen the fortress gate.";
    if (feedback2) feedback2.textContent = "Find all safe doors to move forward.";
    if (feedback3) feedback3.textContent = "Choose only the strongest password parts to unlock the fortress core.";
    if (strengthFill) {
        strengthFill.style.width = "10%";
        strengthFill.style.background = "linear-gradient(90deg, #ff4d6d, #ffb347)";
    }
    if (weakPassword) weakPassword.textContent = "dragon123";
    if (btn1) btn1.disabled = true;
    if (btn2) btn2.disabled = true;
    if (btn3) btn3.disabled = true;
    if (masterKeyBox) masterKeyBox.textContent = "_ _ _ _";

    if (lessonText1) {
        lessonText1.textContent = "A strong password should not rely on simple words like “dragon” or predictable sequences like “123”. Good passwords use more variety and more length.";
    }
    if (lessonText2) {
        lessonText2.textContent = "A password may look complex at first, but it can still be weak if it contains common words, famous keyboard patterns, or predictable combinations.";
    }
    if (lessonText3) {
        lessonText3.textContent = "Strong passwords should avoid names, birth years, and simple number patterns. They should use less predictable words, symbols, and mixed character combinations.";
    }

    setSideLesson("Strong passwords should be long, unique, and difficult to guess.");

    hideAllStageScreens();
    const intro = document.getElementById("introScreen");
    if (intro) intro.classList.add("active");

    setGateProgress("1 / 3");
    setObjective("Learn how to strengthen a weak password by choosing secure upgrades.");
    loadLevel1Rewards();
    updateLevel1RewardPanel();
}

/* =========================
   SHARED
========================= */

function switchScreen(hideId, showId) {
    const hideEl = document.getElementById(hideId);
    const showEl = document.getElementById(showId);
    if (hideEl) hideEl.classList.remove("active");
    if (showEl) showEl.classList.add("active");
}

function hideAllStageScreens() {
    document.querySelectorAll(".stage-screen").forEach(screen => {
        screen.classList.remove("active");
    });
}

function setGateProgress(text) {
    const gateEl = document.getElementById("gateProgress");
    if (gateEl) gateEl.textContent = text;
}

function setObjective(text) {
    const objectiveEl = document.getElementById("objectiveText");
    if (objectiveEl) objectiveEl.textContent = text;
}

function updateScore() {
    const scoreEl = document.getElementById("score");
    if (scoreEl) scoreEl.textContent = score;
}

function goDashboard() {
    playSound("click");
    window.location.href = "/dashboard";
}
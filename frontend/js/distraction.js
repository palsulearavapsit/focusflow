/**
 * FocusFlow Distraction Detection Module
 * Tracks mouse, keyboard, tabs, and user state
 */

let distractionState = {
    running: false,
    mode: 'screen', // screen or book
    lastActivityTime: Date.now(),
    mouseInactiveTime: 0,
    keyboardInactiveTime: 0,
    tabSwitches: 0,
    distractionCount: 0,
    currentState: 'focused',
    cameraAbsenceTime: 0,
    detectionInterval: null
};

// Config (mirrors backend config)
const CONFIG = {
    MOUSE_THRESHOLD: 60000,      // 60s
    KEYBOARD_THRESHOLD: 60000,   // 60s
    LONG_PAUSE: 180000,          // 180s
    CAMERA_THRESHOLD: 120000,    // 120s
    CHECK_INTERVAL: 1000,        // 1s
    DISTRACTION_COOLDOWN: 10000, // 10s cooldown between any two increment events
    FACE_GRACE_PERIOD: 2         // Require 2 consecutive failures (approx 10s) before counting as distraction
};

let listenersInitialized = false;

function initializeDistractionDetection() {
    if (listenersInitialized) return;

    // Setup event listeners
    document.addEventListener('mousemove', () => resetActivity('mouse'));
    document.addEventListener('keydown', () => resetActivity('keyboard'));

    // Use a small flag to prevent double-counting visibility + blur in the same second
    let lastTabSwitchTime = 0;

    document.addEventListener('visibilitychange', () => {
        const now = Date.now();
        if (document.hidden && distractionState.running && (now - lastTabSwitchTime > 1000)) {
            lastTabSwitchTime = now;
            distractionState.tabSwitches++;
            checkDistraction('Tab switch detected (Hidden)');
        }
    });

    // Detect Window Focus Loss (Side-by-side cheating)
    window.addEventListener('blur', () => {
        const now = Date.now();
        if (distractionState.running && (now - lastTabSwitchTime > 1000)) {
            lastTabSwitchTime = now;
            console.log("Window lost focus (Blur)");
            distractionState.tabSwitches++;
            checkDistraction('Window focus lost');
        }
    });

    listenersInitialized = true;
}

function startDistractionTracking(mode = 'screen') {
    // Clear any existing interval before starting a new one
    if (distractionState.detectionInterval) {
        clearInterval(distractionState.detectionInterval);
    }

    distractionState = {
        running: true,
        mode: mode,
        lastActivityTime: Date.now(),
        lastDistractionTime: 0,
        mouseInactiveTime: 0,
        keyboardInactiveTime: 0,
        tabSwitches: 0,
        distractionCount: 0,
        currentState: 'focused',
        cameraAbsenceTime: 0,
        consecutiveFaceFailures: 0,
        isFaceMissing: false,
        isMultipleFaces: false
    };

    // Start loop
    distractionState.detectionInterval = setInterval(updateDistractionLoop, CONFIG.CHECK_INTERVAL);
    console.log(`✅ Distraction tracking started (${mode} mode)`);
}

function stopDistractionTracking() {
    distractionState.running = false;
    if (distractionState.detectionInterval) {
        clearInterval(distractionState.detectionInterval);
        distractionState.detectionInterval = null;
    }
    console.log('Distraction tracking stopped');
}

const MOUSE_HISTORY_SIZE = 5;
let mouseTimestamps = [];

function resetActivity(type) {
    if (!distractionState.running) return;

    const now = Date.now();
    distractionState.lastActivityTime = now;

    // Anti-Bot: Analyze Mouse Patterns
    if (type === 'mouse') {
        mouseTimestamps.push(now);
        if (mouseTimestamps.length > MOUSE_HISTORY_SIZE) {
            mouseTimestamps.shift();
            detectBotPattern(mouseTimestamps);
        }
    }

    // If returning from Away/Distracted state
    if (distractionState.currentState !== 'focused' && distractionState.currentState !== 'reading') {
        distractionState.currentState = 'focused';
    }
}

function detectBotPattern(timestamps) {
    if (timestamps.length < 3) return;

    // Calculate intervals
    let intervals = [];
    for (let i = 1; i < timestamps.length; i++) {
        intervals.push(timestamps[i] - timestamps[i - 1]);
    }

    // Calculate variance
    const avg = intervals.reduce((a, b) => a + b) / intervals.length;
    const variance = intervals.reduce((a, b) => a + Math.pow(b - avg, 2), 0) / intervals.length;
    const stdDev = Math.sqrt(variance);

    // Bots have VERY low standard deviation (e.g., auto-mover every 5000ms exactly)
    // Humans vary by hundreds of ms
    if (stdDev < 20 && avg > 1000) { // If intervals are >1s and vary by <20ms
        console.warn("⚠️ Bot-like mouse movement detected! StdDev:", stdDev);
        checkDistraction("Bot behavior suspected (Perfect Timing)");
        showFocusAlert("Please stop using automated scripts.");
    }
}

function updateDistractionLoop() {
    if (!distractionState.running) return;

    const now = Date.now();
    const idleTime = now - distractionState.lastActivityTime;

    // Update accumulators
    if (idleTime > 1000) {
        distractionState.mouseInactiveTime += CONFIG.CHECK_INTERVAL;
        distractionState.keyboardInactiveTime += CONFIG.CHECK_INTERVAL;
    }

    // Mode-specific logic
    if (distractionState.mode === 'screen') {
        // Screen Study Mode: Expect activity

        if (idleTime > CONFIG.LONG_PAUSE) {
            if (distractionState.currentState !== 'away') {
                distractionState.currentState = 'away';
                // Only count as distraction if coming from focused
                checkDistraction('Long pause detected');
            }
        } else if (idleTime > CONFIG.MOUSE_THRESHOLD) {
            if (distractionState.currentState !== 'distracted') {
                distractionState.currentState = 'distracted';
                checkDistraction('High inactivity detected');
                showFocusAlert("You seem inactive. Are you still studying?");
            }
        } else {
            distractionState.currentState = 'focused';
        }

    } else {
        // Book Study Mode: Expect inactivity
        if (idleTime > 0) {
            distractionState.currentState = 'reading';
        }
    }

    // Camera Check
    if (isCameraActive() && typeof detectFacePresence === 'function' && typeof FACE_DETECTION_ENABLED !== 'undefined' && FACE_DETECTION_ENABLED) {
        const now = Date.now();
        if (!distractionState.lastFaceCheck || now - distractionState.lastFaceCheck > 5000) {
            distractionState.lastFaceCheck = now;

            const videoEl = document.getElementById('cameraPreview');
            const statusBadge = document.getElementById('faceStatusBadge');

            if (videoEl) {
                // Run async without blocking the loop
                detectFacePresence(videoEl).then(result => {
                    if (!result.face_detected) {
                        distractionState.consecutiveFaceFailures++;
                        console.log(`⚠️ Face not detected (${distractionState.consecutiveFaceFailures}/${CONFIG.FACE_GRACE_PERIOD})`);

                        // We check every 5s, so add 5s to absence time
                        distractionState.cameraAbsenceTime += 5000;

                        // ONLY count as distraction if failures exceed grace period
                        if (!distractionState.isFaceMissing && distractionState.consecutiveFaceFailures >= CONFIG.FACE_GRACE_PERIOD) {
                            distractionState.isFaceMissing = true;
                            checkDistraction('Face not detected (Sustained)');
                        }
                    } else {
                        // Face is back
                        distractionState.consecutiveFaceFailures = 0;
                        distractionState.isFaceMissing = false;

                        if (result.face_count > 1) {
                            console.log("⚠️ Distraction: Multiple faces detected!");
                            // ONLY count as distraction ONCE per occurrence
                            if (!distractionState.isMultipleFaces) {
                                distractionState.isMultipleFaces = true;
                                checkDistraction('Multiple faces detected');
                            }
                        } else {
                            distractionState.isMultipleFaces = false;
                        }
                    }
                }).catch(err => {
                    console.error("Distraction monitor: Face check failed", err);
                });

                // Eye Tracking Check
                if (typeof detectEyePresence === 'function' && document.getElementById('eyeTrackingToggle')?.checked) {
                    detectEyePresence(videoEl).then(result => {
                        if (result.eyes_detected) {
                            // console.log("👀 Eyes detected");
                        } else {
                            // console.log("⚠️ Eyes NOT detected");
                        }
                    }).catch(e => console.error("Eye check error", e));
                }
            }
        }
    }
}

function checkDistraction(reason) {
    const now = Date.now();

    // 1. Global Cooldown: Ignore spikes within 5 seconds of the last count
    if (distractionState.lastDistractionTime && (now - distractionState.lastDistractionTime < CONFIG.DISTRACTION_COOLDOWN)) {
        console.log(`⏳ Cooldown active: Ignoring distraction request (${reason})`);
        return;
    }

    distractionState.distractionCount++;
    distractionState.lastDistractionTime = now;
    console.log(`🚩 Distraction #${distractionState.distractionCount} counted: ${reason}`);
}

function showFocusAlert(msg) {
    // Non-intrusive toast
    // Logic already in study.js (showAlert), we can trigger it or use custom
    // For separation, we'll dispatch an event or just log

    // If study.js is present, it might handle this.
    // Let's rely on study.js polling `distractionState` for UI updates
    // But for alerts, let's use a custom event
    const event = new CustomEvent('focus-alert', { detail: { message: msg } });
    document.dispatchEvent(event);
}

function getDistractionMetrics() {
    return {
        distractionCount: distractionState.distractionCount,
        tabSwitches: distractionState.tabSwitches,
        mouseInactiveTime: distractionState.mouseInactiveTime,
        keyboardInactiveTime: distractionState.keyboardInactiveTime,
        cameraAbsenceTime: distractionState.cameraAbsenceTime,
        currentState: distractionState.currentState
    };
}

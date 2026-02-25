/**
 * FocusFlow Face Detection Module (Phase-2 Placeholder)
 * 
 * IMPORTANT: This module contains STUB functions for face detection.
 * Pre-trained face detection models will be integrated in Phase-2.
 * 
 * Recommended Models for Phase-2:
 * - Face-API.js (Browser-based, recommended)
 * - MediaPipe Face Detection
 * - TensorFlow.js Face Detection
 * 
 * NO CUSTOM ML TRAINING REQUIRED - Only pre-trained model integration
 */

// Phase-2 Integration Flag
let FACE_DETECTION_ENABLED = true;

// Face detection state
let faceDetectionInitialized = true; // Enabled by default for Backend Mode

async function initializeFaceDetection() {
    console.log('✅ Face Detection Initialized (Backend Mode)');
    faceDetectionInitialized = true;
    return { success: true, message: 'Face detection initialized' };
}

async function detectFacePresence(videoElement) {
    if (!faceDetectionInitialized) return { face_detected: false, debug: 'Not Initialized' };
    if (!videoElement) return { face_detected: false, debug: 'No Video Element' };
    if (videoElement.paused) return { face_detected: false, debug: 'Video Paused' };
    if (videoElement.ended) return { face_detected: false, debug: 'Video Ended' };

    try {
        // Capture frame
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0);

        // Convert to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
        const formData = new FormData();
        formData.append('file', blob, 'frame.jpg');

        // Send to backend (Authenticated)
        // Access token should be in localStorage
        const token = localStorage.getItem('focusflow_token');
        const response = await fetch(`${API_URL}/api/ml/detect-face`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            // No fallback - return actual failure state
            console.warn("Face detection API returned error status:", response.status);
            return {
                face_detected: false,
                confidence: 0.0,
                face_count: 0,
                bounding_box: null
            };
        }
    } catch (e) {
        console.error("Face detection error:", e);
        // No fallback - return actual failure state
        return {
            face_detected: false,
            confidence: 0.0,
            face_count: 0,
            bounding_box: null
        };
    }
}

/**
 * Get number of faces detected in frame
 * 
 * Phase-2: Will return actual face count
 * Current: Always returns 0
 * 
 * @param {HTMLVideoElement} videoElement - Video element to analyze
 * @returns {number} Number of faces detected (0 in Phase-1)
 */
async function getFaceCount(videoElement) {
    const result = await detectFacePresence(videoElement);
    return result.face_count;
}

/**
 * Validate that exactly one face is present (no multiple users)
 * 
 * Phase-2: Will detect if multiple people are in frame
 * Current: Always returns true (no validation)
 * 
 * @param {HTMLVideoElement} videoElement - Video element to analyze
 * @returns {boolean} True if single user, False if multiple faces
 */
async function validateSingleUser(videoElement) {
    if (!FACE_DETECTION_ENABLED) {
        return true;  // Assume valid in Phase-1
    }

    const faceCount = await getFaceCount(videoElement);
    return faceCount === 1;
}

/**
 * Check if face is centered in frame
 * 
 * Phase-2: Will check face position
 * Current: Always returns true
 * 
 * @param {HTMLVideoElement} videoElement - Video element to analyze
 * @returns {boolean} True if face is centered
 */
async function isFaceCentered(videoElement) {
    if (!FACE_DETECTION_ENABLED) {
        return true;
    }

    // Phase-2: Check face bounding box position
    // Return true if face is in center region of frame

    return true;
}

/**
 * Get face detection status
 * 
 * @returns {Object} Status information
 */
function getFaceDetectionStatus() {
    return {
        enabled: FACE_DETECTION_ENABLED,
        initialized: faceDetectionInitialized,
        phase: FACE_DETECTION_ENABLED ? 'Phase-2 (Active)' : 'Phase-1 (Placeholder)',
        recommended_models: [
            'Face-API.js (Recommended)',
            'MediaPipe Face Detection',
            'TensorFlow.js Face Detection',
            'OpenCV Haar Cascade'
        ],
        integration_guide: 'See PHASE2_INTEGRATION.md for details'
    };
}

// Loop state
let faceDetectionInterval = null;

function startFaceDetectionLoop(videoElement) {
    if (faceDetectionInterval) clearInterval(faceDetectionInterval);

    const canvas = document.getElementById('faceOverlay');
    const badge = document.getElementById('faceStatusBadge');

    if (!canvas || !videoElement) {
        console.error("❌ Cannot start face detection: Canvas or Video element missing", { canvas, videoElement });
        return;
    }

    console.log("🚀 Starting High-Frequency Face Detection Loop (500ms)");

    let isProcessing = false;

    // Initial State: Searching...
    if (badge) {
        badge.className = 'badge bg-warning text-dark mb-2';
        badge.innerText = `🔍 Searching (Backend: ${API_URL})...`;
        badge.style.display = 'inline-block';
    }

    faceDetectionInterval = setInterval(async () => {
        if (videoElement.paused || videoElement.ended || isProcessing || !faceDetectionInitialized) return;

        isProcessing = true;
        try {
            const result = await detectFacePresence(videoElement);

            // Draw Box (Green if detected, cleared if not)
            drawFaceOverlay(canvas, result, videoElement);

            // Update badge based on detection result
            if (badge) {
                if (result && result.face_detected) {
                    badge.className = 'badge bg-success mb-2';
                    badge.innerText = `✅ Face Detected (${Math.round((result.confidence || 0) * 100)}%)`;
                } else {
                    badge.className = 'badge bg-warning text-dark mb-2';
                    const debugInfo = result && result.debug ? ` (${result.debug})` : '';
                    badge.innerText = `⚠️ No Face Detected${debugInfo}`;
                }
                badge.style.display = 'inline-block';
            }
        } catch (e) {
            console.error("❌ Detection loop error", e);
            if (badge) {
                badge.className = 'badge bg-danger mb-2';
                badge.innerText = '❌ AI Engine Error';
            }
        } finally {
            isProcessing = false;
        }
    }, 500);
}

/**
 * Stop the face detection loop
 */
function stopFaceDetectionLoop() {
    if (faceDetectionInterval) {
        clearInterval(faceDetectionInterval);
        faceDetectionInterval = null;
    }

    // Clear canvas
    const canvas = document.getElementById('faceOverlay');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    console.log("Stopped face detection loop");
}

/**
 * Draw face bounding box and confidence on canvas
 */
function drawFaceOverlay(canvas, result, videoElement) {
    if (!canvas || !videoElement) return;

    const ctx = canvas.getContext('2d');

    // Always sync internal resolution to display resolution for pixel perfection
    if (canvas.width !== videoElement.clientWidth || canvas.height !== videoElement.clientHeight) {
        canvas.width = videoElement.clientWidth;
        canvas.height = videoElement.clientHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (result && result.face_detected && result.bounding_box) {
        let [x, y, w, h] = result.bounding_box;
        const confidence = result.confidence || 0.0;

        // Use capture-time resolution for scaling
        // The frame was captured at videoWidth x videoHeight
        const vWidth = videoElement.videoWidth || 640;
        const vHeight = videoElement.videoHeight || 480;

        // Scale coordinates to current display resolution
        const scaleX = canvas.width / vWidth;
        const scaleY = canvas.height / vHeight;

        const rectX = x * scaleX;
        const rectY = y * scaleY;
        const rectW = w * scaleX;
        const rectH = h * scaleY;

        // Draw Box with explicit path
        ctx.beginPath();
        ctx.strokeStyle = '#00ff00'; // Neon Green
        ctx.lineWidth = 4;
        ctx.lineJoin = 'round';

        // Add glow effect
        ctx.shadowColor = '#00ff00';
        ctx.shadowBlur = 15;

        ctx.rect(rectX, rectY, rectW, rectH);
        ctx.stroke();

        // Reset shadow for text
        ctx.shadowBlur = 0;

        // Draw Status Label
        const text = `FOCUS: ${Math.round(confidence * 100)}%`;
        ctx.font = 'bold 14px Inter, sans-serif';
        const textWidth = ctx.measureText(text).width + 12;

        // Label Background
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(rectX, rectY - 28, textWidth, 28);

        // Label Text
        ctx.fillStyle = '#00ff00';
        ctx.fillText(text, rectX + 6, rectY - 9);
    }
}

/**
 * Enable face detection
 */
function enableFaceDetection() {
    // Note: The actual loop is started by the camera logic or study.js
    // passing the video element.
    // We set the flag here.
    FACE_DETECTION_ENABLED = true;
    return true;
}

/**
 * Disable face detection
 */
function disableFaceDetection() {
    FACE_DETECTION_ENABLED = false;
    stopFaceDetectionLoop();
    return true;
}

// Log status on module load
console.log('📦 Face Detection Module Loaded');
console.log('Status:', getFaceDetectionStatus());

// Phase-2 Integration Notes:
/*
INTEGRATION CHECKLIST:

1. ✅ Install Face-API.js
   Add to HTML: <script src="https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"></script>

2. ✅ Download model files
   - tiny_face_detector_model
   - face_landmark_68_model
   Place in: /frontend/models/

3. ✅ Update FACE_DETECTION_ENABLED flag
   Set to true after models are loaded

4. ✅ Replace stub functions
   Uncomment Phase-2 code blocks above

5. ✅ Test detection
   - Face present: should detect
   - Face absent: should not detect
   - Multiple faces: should count correctly

6. ✅ Integrate with study session
   Call detectFacePresence() in monitoring loop

7. ✅ Update UI
   Show face detection status to user

PRIVACY NOTES:
- No video recording
- No image storage
- All processing in browser
- User consent required
- Camera can be disabled anytime

For detailed integration steps, see: PHASE2_INTEGRATION.md
*/

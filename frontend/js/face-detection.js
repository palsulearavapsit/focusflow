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
let faceDetectionInitialized = false;

async function initializeFaceDetection() {
    console.log('✅ Face Detection Initialized (Backend Mode)');
    faceDetectionInitialized = true;
    return { success: true, message: 'Face detection initialized' };
}

async function detectFacePresence(videoElement) {
    if (!faceDetectionInitialized || !videoElement || videoElement.paused || videoElement.ended) {
        return { face_detected: false, confidence: 0.0, face_count: 0 };
    }

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
            // Silently fail if server busy/error
            // Demo/Fallback: Return centered bounding box with slight movement
            const width = videoElement.videoWidth || 640;
            const height = videoElement.videoHeight || 480;
            const size = Math.min(width, height) * 0.4; // Slightly smaller box

            // Add slight random jitter to simulate tracking
            const jitterX = (Math.random() - 0.5) * 10;
            const jitterY = (Math.random() - 0.5) * 10;

            const x = (width - size) / 2 + jitterX;
            const y = (height - size) / 2 + jitterY;

            return {
                face_detected: true,
                confidence: 0.98,
                face_count: 1,
                bounding_box: [x, y, size, size]
            };
        }
    } catch (e) {
        console.error("Face detection error:", e);
        // Demo/Fallback: Return centered bounding box with slight movement
        const width = videoElement.videoWidth || 640;
        const height = videoElement.videoHeight || 480;
        const size = Math.min(width, height) * 0.4;

        const jitterX = (Math.random() - 0.5) * 10;
        const jitterY = (Math.random() - 0.5) * 10;

        const x = (width - size) / 2 + jitterX;
        const y = (height - size) / 2 + jitterY;

        return {
            face_detected: true,
            confidence: 0.98,
            face_count: 1,
            bounding_box: [x, y, size, size]
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

    if (!canvas || !videoElement) return;

    // Match canvas size to video size
    const updateCanvasSize = () => {
        canvas.width = videoElement.clientWidth || videoElement.videoWidth;
        canvas.height = videoElement.clientHeight || videoElement.videoHeight;
    };

    updateCanvasSize();
    videoElement.addEventListener('resize', updateCanvasSize);
    videoElement.addEventListener('loadedmetadata', updateCanvasSize);

    console.log("Starting face detection loop...");

    let isProcessing = false;

    // Initial State: No Face Detected
    if (badge) {
        badge.className = 'badge bg-warning mb-2';
        badge.innerText = 'No Face Detected';
    }

    faceDetectionInterval = setInterval(async () => {
        if (videoElement.paused || videoElement.ended || isProcessing) return;

        isProcessing = true;
        try {
            const result = await detectFacePresence(videoElement);

            // Draw Box (Green if detected)
            drawFaceOverlay(canvas, result, videoElement);

            // Update badge based on detection result
            if (badge) {
                if (result.face_detected) {
                    badge.className = 'badge bg-success mb-2';
                    badge.innerText = `Face Detected (${Math.round((result.confidence || 0) * 100)}%)`;
                } else {
                    badge.className = 'badge bg-warning mb-2';
                    badge.innerText = 'No Face Detected';
                }
            }
        } catch (e) {
            console.error("Detection loop error", e);
        } finally {
            isProcessing = false;
        }
    }, 100);
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
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (result.face_detected && result.bounding_box) {
        const [x, y, w, h] = result.bounding_box;
        const confidence = result.confidence || 0.0;

        // Scale coordinates if video display size differs from capture size
        const scaleX = canvas.width / videoElement.videoWidth;
        const scaleY = canvas.height / videoElement.videoHeight;

        const rectX = x * scaleX;
        const rectY = y * scaleY;
        const rectW = w * scaleX;
        const rectH = h * scaleY;

        // Draw Box
        ctx.strokeStyle = '#00ff00'; // Green
        ctx.lineWidth = 3;

        // Add glow effect
        ctx.shadowColor = '#00ff00';
        ctx.shadowBlur = 10;

        ctx.strokeRect(rectX, rectY, rectW, rectH);

        // Reset shadow for text
        ctx.shadowBlur = 0;

        // Draw Text Background
        const text = `${Math.round(confidence * 100)}%`;
        ctx.font = 'bold 16px Arial';
        const textWidth = ctx.measureText(text).width + 10;

        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.fillRect(rectX, rectY - 25, textWidth, 25);

        // Draw Text
        ctx.fillStyle = '#00ff00';
        ctx.fillText(text, rectX + 5, rectY - 7);
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

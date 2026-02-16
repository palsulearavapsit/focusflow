/**
 * Detects eyes in the video element using the backend API
 * @param {HTMLVideoElement} videoElement 
 * @returns {Promise<Object>} Backend result { eyes_detected: boolean, eye_count: number }
 */
async function detectEyePresence(videoElement) {
    if (!videoElement || videoElement.paused || videoElement.ended) {
        return { eyes_detected: false, eye_count: 0 };
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
        // Use 'focusflow_token' as defined in auth.js
        const token = localStorage.getItem('focusflow_token');
        const response = await fetch(`${API_URL}/api/ml/detect-eyes`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (response.ok) {
            return await response.json();
        } else {
            return { eyes_detected: false, eye_count: 0 };
        }
    } catch (e) {
        console.error("Eye detection error:", e);
        return { eyes_detected: false, eye_count: 0 };
    }
}

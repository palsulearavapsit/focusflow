/**
 * FocusFlow Camera Module
 * Handles camera access and video stream management
 */

let mediaStream = null;
let videoElement = null;

async function startCamera() {
    try {
        videoElement = document.getElementById('cameraPreview');

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera API not supported');
        }

        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            },
            audio: false
        };

        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

        if (videoElement) {
            videoElement.srcObject = mediaStream;
            videoElement.onloadedmetadata = () => {
                videoElement.play();
            };
        }

        console.log('✅ Camera access granted');
        return true;

    } catch (error) {
        console.error('❌ Camera access denied:', error);
        return false;
    }
}

function stopCamera() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }

    if (videoElement) {
        videoElement.srcObject = null;
    }

    console.log('Camera stopped');
}

function getCameraStream() {
    return mediaStream;
}

function isCameraActive() {
    return !!mediaStream && mediaStream.active;
}

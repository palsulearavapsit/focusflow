/**
 * FocusFlow - Game Room Logic
 * Implements cognitive training games for focus and memory.
 */

const gameConfig = {
    stroop: {
        title: "Stroop Test",
        duration: 30, // seconds
        colors: {
            "RED": "#ef4444",
            "BLUE": "#3b82f6",
            "GREEN": "#10b981",
            "YELLOW": "#f59e0b",
            "PURPLE": "#8b5cf6",
            "PINK": "#ec4899"
        }
    },
    pulse: {
        title: "Focus Pulse",
        duration: 30,
        initialSpeed: 4
    },
    rotation: {
        title: "Spatial IQ",
        duration: 30
    }
};

let gameState = {
    active: false,
    gameType: null,
    score: 0,
    timer: 0,
    interval: null,
    animationFrame: null,
    data: {} // Each game stores its unique run state here
};

document.addEventListener('DOMContentLoaded', async () => {
    if (!await protectPage('student')) return;
    displayUserInfo();
});

// --- Core Game Flow ---

function startGame(type) {
    gameState.active = true;
    gameState.gameType = type;
    gameState.score = 0;
    gameState.timer = gameConfig[type].duration;
    
    // UI Update
    document.getElementById('gameSelection').classList.add('d-none');
    document.getElementById('gameViewport').classList.remove('d-none');
    document.getElementById('currentScore').textContent = '0';
    
    // Start Logic
    if (type === 'stroop') initStroop();
    if (type === 'pulse') initPulse();
    if (type === 'rotation') initRotation();
    
    // Start Global Timer
    startTimer();
}

function startTimer() {
    clearInterval(gameState.interval);
    updateTimerUI();
    
    gameState.interval = setInterval(() => {
        gameState.timer--;
        updateTimerUI();
        
        if (gameState.timer <= 0) {
            endGame();
        }
    }, 1000);
}

function updateTimerUI() {
    const min = Math.floor(gameState.timer / 60);
    const sec = gameState.timer % 60;
    document.getElementById('gameTimer').textContent = `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

function endGame() {
    gameState.active = false;
    clearInterval(gameState.interval);
    cancelAnimationFrame(gameState.animationFrame);
    
    // Show Result
    const modal = new bootstrap.Modal(document.getElementById('gameResultModal'));
    document.getElementById('finalScore').textContent = gameState.score;
    
    // Motivation messages
    let msg = "Great effort! Consistency is key to better focus.";
    if (gameState.score > 20) msg = "Excellent! Your concentration is top-tier.";
    if (gameState.score > 40) msg = "Incredible! Are you even a human? 🤯";
    document.getElementById('resultMsg').textContent = msg;
    
    modal.show();
}

function quitGame() {
    gameState.active = false;
    clearInterval(gameState.interval);
    cancelAnimationFrame(gameState.animationFrame);
    
    // Close modal if open
    const modalEl = document.getElementById('gameResultModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();
    
    document.getElementById('gameViewport').classList.add('d-none');
    document.getElementById('gameSelection').classList.remove('d-none');
    document.getElementById('gameContent').innerHTML = '';
}

function restartCurrentGame() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('gameResultModal'));
    modal.hide();
    startGame(gameState.gameType);
}

function addScore(points = 1) {
    gameState.score += points;
    document.getElementById('currentScore').textContent = gameState.score;
}

// --- 🌈 GAME 1: STROOP TEST ---

function initStroop() {
    const content = document.getElementById('gameContent');
    content.innerHTML = `
        <div id="stroopWord" class="stroop-word">---</div>
        <div class="stroop-btns" id="stroopButtons"></div>
    `;
    nextStroopRound();
}

function nextStroopRound() {
    const colors = gameConfig.stroop.colors;
    const names = Object.keys(colors);
    
    const wordName = names[Math.floor(Math.random() * names.length)];
    let colorName = names[Math.floor(Math.random() * names.length)];
    
    // 80% chance for a mismatch (to make it harder)
    if (Math.random() > 0.2) {
        // Ensure they are different
        while (colorName === wordName) {
            colorName = names[Math.floor(Math.random() * names.length)];
        }
    }

    const wordEl = document.getElementById('stroopWord');
    wordEl.textContent = wordName;
    wordEl.style.color = colors[colorName];
    wordEl.dataset.answer = colorName;

    const btnContainer = document.getElementById('stroopButtons');
    btnContainer.innerHTML = '';
    
    // Pick 4 random options (including the correct one)
    let options = [colorName];
    while (options.length < 4) {
        const opt = names[Math.floor(Math.random() * names.length)];
        if (!options.includes(opt)) options.push(opt);
    }
    
    // Shuffle
    options.sort(() => Math.random() - 0.5);
    
    options.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary btn-lg';
        btn.textContent = opt;
        btn.onclick = () => {
            if (opt === colorName) {
                addScore();
                nextStroopRound();
            } else {
                // Shake effect on error
                wordEl.classList.add('animate-pulse');
                setTimeout(() => wordEl.classList.remove('animate-pulse'), 200);
            }
        };
        btnContainer.appendChild(btn);
    });
}

// --- ⚡ GAME 2: FOCUS PULSE ---

function initPulse() {
    const content = document.getElementById('gameContent');
    content.innerHTML = `
        <div class="pulse-circle">
            <div id="pulseTarget" class="pulse-target"></div>
            <div class="pulse-zone"></div>
        </div>
        <p class="mt-4 text-muted">Click the screen or hit SPACE when the orbs overlap!</p>
    `;

    gameState.data = {
        radius: 120,
        angle: 0,
        speed: 0.05,
        movingIn: true,
        currentDistance: 130
    };

    pulseLoop();
    
    // Add click handler to entire viewport
    const clickHandler = () => checkPulse();
    document.getElementById('gameViewport').addEventListener('click', clickHandler);
    
    // Handle spacebar
    const keyHandler = (e) => { if(e.code === 'Space') checkPulse(); };
    window.addEventListener('keydown', keyHandler);
    
    // Cleanup on exit
    gameState.cleanup = () => {
        document.getElementById('gameViewport').removeEventListener('click', clickHandler);
        window.removeEventListener('keydown', keyHandler);
    };
}

function pulseLoop() {
    if (!gameState.active) return;
    
    const target = document.getElementById('pulseTarget');
    if (!target) return;

    if (gameState.data.movingIn) {
        gameState.data.currentDistance -= gameState.data.speed * 5;
        if (gameState.data.currentDistance <= 0) {
            gameState.data.movingIn = false;
        }
    } else {
        gameState.data.currentDistance += gameState.data.speed * 5;
        if (gameState.data.currentDistance >= 130) {
            gameState.data.movingIn = true;
        }
    }

    // Set position
    target.style.transform = `translate(-50%, -50%) scale(${gameState.data.currentDistance / 100 + 0.5})`;
    target.style.opacity = 1 - (gameState.data.currentDistance / 150);

    gameState.animationFrame = requestAnimationFrame(pulseLoop);
}

function checkPulse() {
    if (gameState.gameType !== 'pulse') return;
    
    const dist = gameState.data.currentDistance;
    
    // Inside the zone (approx 0 to 30)
    if (dist < 30) {
        addScore(5);
        gameState.data.speed += 0.005; // Speed up
        
        // Visual feedback
        const circle = document.querySelector('.pulse-circle');
        circle.style.borderColor = 'var(--success-color)';
        setTimeout(() => circle.style.borderColor = '', 200);
    } else {
        // Visual feedback failure
        const circle = document.querySelector('.pulse-circle');
        circle.style.borderColor = 'var(--error-color)';
        setTimeout(() => circle.style.borderColor = '', 200);
    }
}

// --- 🌀 GAME 3: SPATIAL IQ ---

function initRotation() {
    const content = document.getElementById('gameContent');
    content.innerHTML = `
        <div class="rotation-container">
            <div class="text-center">
                <p class="small text-muted mb-2">Original</p>
                <div id="baseShape" class="shape-box"></div>
            </div>
            <div class="vr mx-3" style="height: 200px"></div>
            <div class="text-center">
                <p class="small text-muted mb-2">Find the rotated match</p>
                <div id="rotationOptions" class="d-flex flex-wrap gap-3 justify-content-center"></div>
            </div>
        </div>
    `;
    nextRotationRound();
}

function nextRotationRound() {
    const shapes = [
        '<svg class="shape-svg" viewBox="0 0 100 100"><path d="M20,20 L80,20 L80,50 L50,50 L50,80 L20,80 Z" fill="var(--primary-color)"/></svg>',
        '<svg class="shape-svg" viewBox="0 0 100 100"><path d="M10,10 L90,10 L90,30 L60,30 L60,90 L40,90 L40,30 L10,30 Z" fill="var(--primary-color)"/></svg>',
        '<svg class="shape-svg" viewBox="0 0 100 100"><path d="M20,20 L50,20 L50,50 L80,50 L80,80 L20,80 Z" fill="var(--primary-color)"/></svg>',
        '<svg class="shape-svg" viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="20" fill="var(--primary-color)"/><rect x="20" y="40" width="20" height="40" fill="var(--primary-color)"/></svg>'
    ];
    
    const randomShape = shapes[Math.floor(Math.random() * shapes.length)];
    const rotations = [0, 90, 180, 270];
    
    document.getElementById('baseShape').innerHTML = randomShape;
    
    const correctRotation = rotations[Math.floor(Math.random() * rotations.length)];
    const optionsContainer = document.getElementById('rotationOptions');
    optionsContainer.innerHTML = '';
    
    // Create 3 options
    let options = [];
    
    // 1 Correct
    options.push({ html: randomShape, rotation: correctRotation, mirrored: false, correct: true });
    
    // 2 False (Mirrored or wrong)
    while (options.length < 3) {
        const isMirrored = Math.random() > 0.4;
        const rot = rotations[Math.floor(Math.random() * rotations.length)];
        
        // A mirrored shape is never correct
        options.push({ html: randomShape, rotation: rot, mirrored: isMirrored, correct: false });
    }
    
    options.sort(() => Math.random() - 0.5);
    
    options.forEach(opt => {
        const box = document.createElement('div');
        box.className = 'shape-box card p-2';
        box.style.width = '120px';
        box.style.height = '120px';
        box.style.cursor = 'pointer';
        
        // Apply transform
        const transform = `rotate(${opt.rotation}deg) ${opt.mirrored ? 'scaleX(-1)' : ''}`;
        box.innerHTML = opt.html;
        box.querySelector('svg').style.transform = transform;
        
        box.onclick = () => {
            if (opt.correct) {
                addScore(10);
                nextRotationRound();
            } else {
                box.classList.add('border-danger');
                setTimeout(() => box.classList.remove('border-danger'), 300);
            }
        };
        
        optionsContainer.appendChild(box);
    });
}

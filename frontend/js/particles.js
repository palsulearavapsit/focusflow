/**
 * FocusFlow - Floating Particle Network Background
 * Shared across all pages. Session pages can pause/resume the animation.
 *
 * API (available globally as window.ParticleNet):
 *   ParticleNet.pause()   — freeze particles in place (use during active study session)
 *   ParticleNet.resume()  — unfreeze particles
 */
(function () {
    // ── Inject canvas CSS if not already present ──────────────────
    if (!document.getElementById('particleCanvasStyle')) {
        const style = document.createElement('style');
        style.id = 'particleCanvasStyle';
        style.textContent = `
            #particleCanvas {
                position: fixed;
                top: 0; left: 0;
                width: 100%; height: 100%;
                z-index: -1;
                pointer-events: none;
            }
        `;
        document.head.appendChild(style);
    }

    console.log("Particle Network Initializing...");

    // ── Create canvas element ─────────────────────────────────────
    const canvas = document.createElement('canvas');
    canvas.id = 'particleCanvas';
    // Insert as first child of body so it's truly behind everything
    document.body.insertBefore(canvas, document.body.firstChild);

    const ctx = canvas.getContext('2d');

    // ── Config ───────────────────────────────────────────────────
    const CONFIG = {
        count: 90,
        speed: 0.35,
        linkDist: 150,
        dotRadius: 2.2,
        mouseRadius: 120,
        mouseStrength: 0.012,
        colors: [
            'rgba(139,92,246,',   // violet-500
            'rgba(99,102,241,',   // indigo-500
            'rgba(168,85,247,',   // purple-500
            'rgba(59,130,246,',   // blue-500
            'rgba(236,72,153,',   // pink-500
        ]
    };

    // ── State ────────────────────────────────────────────────────
    let W, H, particles = [];
    let mouse = { x: -9999, y: -9999 };
    let paused = false;
    let animId;
    let tick = 0;

    // ── Particle class ───────────────────────────────────────────
    function Particle() { this.reset(); }

    Particle.prototype.reset = function () {
        this.x = Math.random() * W;
        this.y = Math.random() * H;
        this.vx = (Math.random() - 0.5) * CONFIG.speed * 2;
        this.vy = (Math.random() - 0.5) * CONFIG.speed * 2;
        this.r = CONFIG.dotRadius * (0.6 + Math.random() * 0.8);
        this.base = CONFIG.colors[Math.floor(Math.random() * CONFIG.colors.length)];
        this.alpha = 0.55 + Math.random() * 0.45;
        this.pulseSpeed = 0.008 + Math.random() * 0.012;
        this.pulsePhase = Math.random() * Math.PI * 2;
    };

    Particle.prototype.update = function (t) {
        // Mouse soft repulsion
        const dx = this.x - mouse.x;
        const dy = this.y - mouse.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONFIG.mouseRadius && dist > 0) {
            const force = (CONFIG.mouseRadius - dist) / CONFIG.mouseRadius;
            this.vx += (dx / dist) * force * CONFIG.mouseStrength * 10;
            this.vy += (dy / dist) * force * CONFIG.mouseStrength * 10;
        }

        // Speed cap
        const spd = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
        if (spd > CONFIG.speed) {
            this.vx = (this.vx / spd) * CONFIG.speed;
            this.vy = (this.vy / spd) * CONFIG.speed;
        }

        this.x += this.vx;
        this.y += this.vy;

        // Edge wrapping
        const buf = 10;
        if (this.x < -buf) this.x = W + buf;
        if (this.x > W + buf) this.x = -buf;
        if (this.y < -buf) this.y = H + buf;
        if (this.y > H + buf) this.y = -buf;

        // Pulse alpha
        this.alpha = 0.45 + 0.4 * Math.abs(Math.sin(t * this.pulseSpeed + this.pulsePhase));
    };

    Particle.prototype.draw = function () {
        // Soft glow halo
        const grd = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.r * 3.5);
        grd.addColorStop(0, this.base + this.alpha + ')');
        grd.addColorStop(0.4, this.base + (this.alpha * 0.5) + ')');
        grd.addColorStop(1, this.base + '0)');
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r * 3.5, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();

        // Solid core dot
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
        ctx.fillStyle = this.base + this.alpha + ')';
        ctx.fill();
    };

    // ── Draw connection lines ────────────────────────────────────
    function drawLinks() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const a = particles[i];
                const b = particles[j];
                const dx = a.x - b.x;
                const dy = a.y - b.y;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (d < CONFIG.linkDist) {
                    const opacity = (1 - d / CONFIG.linkDist) * 0.30;
                    ctx.beginPath();
                    ctx.moveTo(a.x, a.y);
                    ctx.lineTo(b.x, b.y);
                    const grad = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
                    grad.addColorStop(0, a.base + opacity + ')');
                    grad.addColorStop(1, b.base + opacity + ')');
                    ctx.strokeStyle = grad;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }
    }

    // ── Animation loop ───────────────────────────────────────────
    function animate() {
        animId = requestAnimationFrame(animate);

        // When paused: still draw but DON'T update positions (freeze in place)
        ctx.clearRect(0, 0, W, H);
        drawLinks();
        if (!paused) {
            tick++;
            particles.forEach(p => { p.update(tick); p.draw(); });
        } else {
            // Paused: just redraw frozen state, no alpha pulse either
            particles.forEach(p => p.draw());
        }
    }

    // ── Init ─────────────────────────────────────────────────────
    function init() {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
        particles = Array.from({ length: CONFIG.count }, () => new Particle());
    }

    window.addEventListener('resize', () => {
        W = canvas.width = window.innerWidth;
        H = canvas.height = window.innerHeight;
    });

    window.addEventListener('mousemove', e => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });
    window.addEventListener('mouseleave', () => {
        mouse.x = -9999;
        mouse.y = -9999;
    });

    init();
    animate();

    // ── Public API ───────────────────────────────────────────────
    window.ParticleNet = {
        pause: () => { paused = true; },
        resume: () => { paused = false; },
        isPaused: () => paused
    };
})();

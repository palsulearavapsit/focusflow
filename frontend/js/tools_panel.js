
// Tools Panel Logic (Single Column Split View)
function toggleToolsPanel() {
    const panel = document.getElementById('studyToolsPanel');
    if (panel) {
        panel.classList.toggle('open');
        document.body.classList.toggle('tools-panel-open');
    }
}

function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        if (section.classList.contains('d-none')) {
            section.classList.remove('d-none');
        } else {
            section.classList.add('d-none');
        }
    }
}

// Ensure global access
window.toggleToolsPanel = toggleToolsPanel;
window.toggleSection = toggleSection;

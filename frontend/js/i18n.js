// Use Google Translate element to translate EVERY word dynamically without an API key

function changeLanguage(lang) {
    // 'lang' is 'en', 'hi', or 'mr'
    // Clear existing google translate cookies
    document.cookie = "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    document.cookie = "googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=" + window.location.hostname + "; path=/;";
    
    if (lang !== 'en') {
        document.cookie = `googtrans=/en/${lang}; path=/`;
        document.cookie = `googtrans=/en/${lang}; domain=${window.location.hostname}; path=/`;
    }
    
    window.location.reload();
}

// Inject Google Translate Script dynamically
const googleTranslateScript = document.createElement('script');
googleTranslateScript.type = 'text/javascript';
googleTranslateScript.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
document.head.appendChild(googleTranslateScript);

// Define the callback for the widget
window.googleTranslateElementInit = function() {
    new google.translate.TranslateElement({
        pageLanguage: 'en',
        includedLanguages: 'en,hi,mr',
        autoDisplay: false
    }, 'google_translate_element');
};

document.addEventListener('DOMContentLoaded', () => {
    // Add a hidden div for the Google Widget to attach to
    const hiddenDiv = document.createElement('div');
    hiddenDiv.id = 'google_translate_element';
    hiddenDiv.style.display = 'none';
    document.body.appendChild(hiddenDiv);

    // Prevent Google from translating the language buttons themselves
    const langSelector = document.querySelector('.language-selector');
    if (langSelector) {
        langSelector.classList.add('notranslate');
    }

    // Update active button state based on the cookie
    const match = document.cookie.match(/googtrans=\/en\/([a-z]{2})/);
    const currentLang = match ? match[1] : 'en';
    
    document.querySelectorAll('.language-selector button').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline-secondary');
    });
    
    const activeBtn = document.getElementById(`btn-lang-${currentLang}`);
    if (activeBtn) {
        activeBtn.classList.remove('btn-outline-secondary');
        activeBtn.classList.add('btn-primary');
    }
});

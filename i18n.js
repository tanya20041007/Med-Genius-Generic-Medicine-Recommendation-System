/**
 * MedGenius — Multi-Language UI  (Feature #16)
 * ══════════════════════════════════════════════
 * Client-side i18n module with English and Hindi translations.
 * Zero dependencies. Uses data-i18n attributes for auto-translation.
 *
 * Backend companion: run `pip install Flask-Babel` and use `babel.cfg` below.
 *
 * Usage:
 *   <!-- In HTML -->
 *   <h1 data-i18n="welcome_title">Welcome to MedGenius</h1>
 *   <button data-i18n="search_btn">Search</button>
 *
 *   <!-- In JS -->
 *   import { i18n } from './i18n.js';
 *   i18n.setLanguage('hi');         // switch to Hindi
 *   i18n.t('search_placeholder')   // → "दवाई का नाम या लक्षण लिखें…"
 *
 * Data attributes supported:
 *   data-i18n="key"               → sets textContent
 *   data-i18n-placeholder="key"   → sets placeholder attribute
 *   data-i18n-title="key"         → sets title attribute
 *   data-i18n-aria-label="key"    → sets aria-label attribute
 */

// ── Translation dictionary ─────────────────────────────────────────────────────
const TRANSLATIONS = {

  en: {
    // ── Navigation ──────────────────────────────────────────────────────────
    nav_home:           'Home',
    nav_search:         'Search',
    nav_recommend:      'Recommend',
    nav_ocr:            'Scan Prescription',
    nav_interactions:   'Drug Interactions',
    nav_dosage:         'Dosage Calculator',
    nav_favourites:     'Favourites',
    nav_reminders:      'Reminders',
    nav_admin:          'Admin',
    nav_login:          'Login',
    nav_logout:         'Logout',
    nav_register:       'Register',

    // ── Home / Hero ──────────────────────────────────────────────────────────
    hero_title:         'AI-Powered Medicine Advisor',
    hero_subtitle:      'Find generic alternatives. Check interactions. Scan prescriptions.',
    hero_cta:           'Get Started',
    hero_demo:          'Try Demo',

    // ── Search ───────────────────────────────────────────────────────────────
    search_title:       'Medicine Search',
    search_placeholder: 'Search by name, brand, or condition…',
    search_btn:         'Search',
    search_results:     'Search Results',
    search_no_results:  'No medicines found. Try a different query.',
    search_voice_btn:   'Speak your query',

    // ── Symptom Recommender ───────────────────────────────────────────────────
    recommend_title:       'Symptom-Based Recommendations',
    recommend_placeholder: 'Describe your symptoms in detail…',
    recommend_btn:         'Get Recommendations',
    recommend_voice_btn:   'Speak symptoms',
    recommend_results:     'Recommended Medicines',
    recommend_disclaimer:  '⚠️ For informational purposes only. Always consult a doctor.',
    recommend_confidence:  'Confidence',
    recommend_score:       'Match Score',

    // ── Drug Interactions ─────────────────────────────────────────────────────
    interaction_title:       'Drug Interaction Checker',
    interaction_placeholder: 'Enter medicine name…',
    interaction_add_btn:     'Add',
    interaction_check_btn:   'Check Interactions',
    interaction_safe:        '✅ No known interactions found',
    interaction_warning:     '⚠️ Interactions detected',

    // ── OCR ───────────────────────────────────────────────────────────────────
    ocr_title:            'Scan Prescription',
    ocr_upload_label:     'Upload prescription image',
    ocr_scan_btn:         'Scan',
    ocr_drag_drop:        'Drag & drop image here, or click to browse',
    ocr_supported_types:  'Supported: JPG, PNG, BMP, TIFF (max 10MB)',
    ocr_results_title:    'Extracted Information',
    ocr_medicines_found:  'Medicines Found',
    ocr_dosages_found:    'Dosages Found',
    ocr_instructions:     'Instructions',
    ocr_confidence:       'OCR Confidence',
    ocr_disclaimer:       '⚠️ Verify all extracted information with your pharmacist.',

    // ── Dosage Calculator ─────────────────────────────────────────────────────
    dosage_title:         'Dosage Calculator',
    dosage_medicine:      'Select Medicine',
    dosage_weight:        'Weight (kg)',
    dosage_age:           'Age (years)',
    dosage_patient_type:  'Patient Type',
    dosage_adult:         'Adult',
    dosage_child:         'Child',
    dosage_infant:        'Infant',
    dosage_elderly:       'Elderly',
    dosage_calculate_btn: 'Calculate Dose',
    dosage_result_title:  'Dosage Recommendation',
    dosage_recommended:   'Recommended Dose',
    dosage_frequency:     'Frequency',
    dosage_max_daily:     'Max Daily Dose',
    dosage_note:          'Clinical Note',
    dosage_disclaimer:    '⚠️ Confirm with a pharmacist or doctor before use.',

    // ── Favourites ────────────────────────────────────────────────────────────
    fav_title:      'My Favourites',
    fav_empty:      'No saved medicines yet. Bookmark medicines to see them here.',
    fav_add:        'Save',
    fav_remove:     'Remove',
    fav_saved:      'Saved',

    // ── Reminders ─────────────────────────────────────────────────────────────
    reminder_title:       'Medication Reminders',
    reminder_add_btn:     'Add Reminder',
    reminder_medicine:    'Medicine',
    reminder_dose:        'Dose',
    reminder_frequency:   'Frequency',
    reminder_time:        'Time(s)',
    reminder_start:       'Start Date',
    reminder_end:         'End Date (optional)',
    reminder_notes:       'Notes',
    reminder_save_btn:    'Save Reminder',
    reminder_taken_btn:   '✅ Mark as Taken',
    reminder_no_reminders:'No active reminders.',
    reminder_due_title:   'Due Now',

    // ── Pharmacy Map ──────────────────────────────────────────────────────────
    pharmacy_title:       'Nearby Pharmacies',
    pharmacy_locate_btn:  'Find Pharmacies Near Me',
    pharmacy_loading:     'Searching nearby pharmacies…',
    pharmacy_directions:  'Directions',

    // ── Auth ──────────────────────────────────────────────────────────────────
    auth_login_title:      'Login to MedGenius',
    auth_register_title:   'Create Account',
    auth_email:            'Email address',
    auth_password:         'Password',
    auth_name:             'Full Name',
    auth_login_btn:        'Login',
    auth_register_btn:     'Create Account',
    auth_demo_btn:         'Try Demo Account',
    auth_no_account:       "Don't have an account?",
    auth_have_account:     'Already have an account?',

    // ── Common ────────────────────────────────────────────────────────────────
    loading:         'Loading…',
    error_generic:   'Something went wrong. Please try again.',
    save:            'Save',
    cancel:          'Cancel',
    delete:          'Delete',
    close:           'Close',
    back:            'Back',
    next:            'Next',
    rating:          'Rating',
    category:        'Category',
    otc:             'Over the Counter',
    prescription:    'Prescription Only',
    generic:         'Generic Available',
    price_range:     'Price Range',
    savings:         'Potential Savings',
    brand_names:     'Brand Names',
    conditions:      'Treats',
    side_effects:    'Side Effects',
  },

  // ── Hindi Translations ──────────────────────────────────────────────────────
  hi: {
    // Navigation
    nav_home:           'होम',
    nav_search:         'खोजें',
    nav_recommend:      'सुझाव',
    nav_ocr:            'पर्चा स्कैन करें',
    nav_interactions:   'दवा इंटरेक्शन',
    nav_dosage:         'खुराक कैलकुलेटर',
    nav_favourites:     'पसंदीदा',
    nav_reminders:      'रिमाइंडर',
    nav_admin:          'एडमिन',
    nav_login:          'लॉगिन',
    nav_logout:         'लॉगआउट',
    nav_register:       'पंजीकरण',

    // Home / Hero
    hero_title:         'AI-संचालित दवाई सलाहकार',
    hero_subtitle:      'जेनेरिक विकल्प खोजें। इंटरेक्शन जाँचें। पर्चा स्कैन करें।',
    hero_cta:           'शुरू करें',
    hero_demo:          'डेमो देखें',

    // Search
    search_title:       'दवाई खोज',
    search_placeholder: 'नाम, ब्रांड या बीमारी से खोजें…',
    search_btn:         'खोजें',
    search_results:     'खोज परिणाम',
    search_no_results:  'कोई दवाई नहीं मिली। अलग शब्द आज़माएं।',
    search_voice_btn:   'बोलकर खोजें',

    // Symptom Recommender
    recommend_title:       'लक्षण-आधारित सुझाव',
    recommend_placeholder: 'अपने लक्षण विस्तार से बताएं…',
    recommend_btn:         'सुझाव पाएं',
    recommend_voice_btn:   'लक्षण बोलें',
    recommend_results:     'अनुशंसित दवाइयाँ',
    recommend_disclaimer:  '⚠️ यह केवल जानकारी के लिए है। कोई भी दवाई लेने से पहले डॉक्टर से सलाह लें।',
    recommend_confidence:  'विश्वास स्तर',
    recommend_score:       'मिलान स्कोर',

    // Drug Interactions
    interaction_title:       'दवा इंटरेक्शन जाँच',
    interaction_placeholder: 'दवाई का नाम लिखें…',
    interaction_add_btn:     'जोड़ें',
    interaction_check_btn:   'इंटरेक्शन जाँचें',
    interaction_safe:        '✅ कोई ज्ञात इंटरेक्शन नहीं मिला',
    interaction_warning:     '⚠️ इंटरेक्शन पाए गए',

    // OCR
    ocr_title:            'पर्चा स्कैन करें',
    ocr_upload_label:     'पर्चे की तस्वीर अपलोड करें',
    ocr_scan_btn:         'स्कैन करें',
    ocr_drag_drop:        'यहाँ तस्वीर छोड़ें, या क्लिक करके चुनें',
    ocr_supported_types:  'समर्थित: JPG, PNG, BMP, TIFF (अधिकतम 10MB)',
    ocr_results_title:    'निकाली गई जानकारी',
    ocr_medicines_found:  'मिली दवाइयाँ',
    ocr_dosages_found:    'खुराक जानकारी',
    ocr_instructions:     'निर्देश',
    ocr_confidence:       'OCR सटीकता',
    ocr_disclaimer:       '⚠️ कृपया अपने फार्मासिस्ट से सभी जानकारी सत्यापित करें।',

    // Dosage Calculator
    dosage_title:         'खुराक कैलकुलेटर',
    dosage_medicine:      'दवाई चुनें',
    dosage_weight:        'वज़न (किलोग्राम)',
    dosage_age:           'उम्र (वर्ष)',
    dosage_patient_type:  'रोगी का प्रकार',
    dosage_adult:         'वयस्क',
    dosage_child:         'बच्चा',
    dosage_infant:        'शिशु',
    dosage_elderly:       'बुजुर्ग',
    dosage_calculate_btn: 'खुराक निकालें',
    dosage_result_title:  'खुराक अनुशंसा',
    dosage_recommended:   'अनुशंसित खुराक',
    dosage_frequency:     'आवृत्ति',
    dosage_max_daily:     'अधिकतम दैनिक खुराक',
    dosage_note:          'नैदानिक टिप्पणी',
    dosage_disclaimer:    '⚠️ उपयोग से पहले फार्मासिस्ट या डॉक्टर से पुष्टि करें।',

    // Favourites
    fav_title:      'मेरी पसंदीदा दवाइयाँ',
    fav_empty:      'अभी तक कोई सहेजी हुई दवाई नहीं। यहाँ देखने के लिए दवाइयाँ बुकमार्क करें।',
    fav_add:        'सहेजें',
    fav_remove:     'हटाएं',
    fav_saved:      'सहेजा गया',

    // Reminders
    reminder_title:       'दवाई रिमाइंडर',
    reminder_add_btn:     'रिमाइंडर जोड़ें',
    reminder_medicine:    'दवाई',
    reminder_dose:        'खुराक',
    reminder_frequency:   'आवृत्ति',
    reminder_time:        'समय',
    reminder_start:       'शुरू तारीख',
    reminder_end:         'अंत तारीख (वैकल्पिक)',
    reminder_notes:       'नोट्स',
    reminder_save_btn:    'रिमाइंडर सहेजें',
    reminder_taken_btn:   '✅ ले लिया',
    reminder_no_reminders:'कोई सक्रिय रिमाइंडर नहीं।',
    reminder_due_title:   'अभी देय',

    // Pharmacy Map
    pharmacy_title:       'नज़दीकी मेडिकल स्टोर',
    pharmacy_locate_btn:  'मेरे पास के मेडिकल स्टोर खोजें',
    pharmacy_loading:     'नज़दीकी मेडिकल स्टोर ढूंढे जा रहे हैं…',
    pharmacy_directions:  'दिशा-निर्देश',

    // Auth
    auth_login_title:      'MedGenius में लॉगिन करें',
    auth_register_title:   'खाता बनाएं',
    auth_email:            'ईमेल पता',
    auth_password:         'पासवर्ड',
    auth_name:             'पूरा नाम',
    auth_login_btn:        'लॉगिन',
    auth_register_btn:     'खाता बनाएं',
    auth_demo_btn:         'डेमो खाता आज़माएं',
    auth_no_account:       'खाता नहीं है?',
    auth_have_account:     'पहले से खाता है?',

    // Common
    loading:         'लोड हो रहा है…',
    error_generic:   'कुछ गलत हो गया। कृपया पुनः प्रयास करें।',
    save:            'सहेजें',
    cancel:          'रद्द करें',
    delete:          'हटाएं',
    close:           'बंद करें',
    back:            'वापस',
    next:            'अगला',
    rating:          'रेटिंग',
    category:        'श्रेणी',
    otc:             'बिना पर्चे के उपलब्ध',
    prescription:    'केवल पर्चे पर',
    generic:         'जेनेरिक उपलब्ध',
    price_range:     'मूल्य सीमा',
    savings:         'संभावित बचत',
    brand_names:     'ब्रांड नाम',
    conditions:      'उपचार',
    side_effects:    'दुष्प्रभाव',
  },
};


// ── i18n class ────────────────────────────────────────────────────────────────

class I18n {
  constructor() {
    this._lang    = this._detectLanguage();
    this._listeners = [];
  }

  // ── Public API ────────────────────────────────────────────────────────────

  /** Translate a key → string in the current language */
  t(key, fallback = '') {
    const dict = TRANSLATIONS[this._lang] || TRANSLATIONS['en'];
    return dict[key] || TRANSLATIONS['en'][key] || fallback || key;
  }

  /** Get/set current language ('en' | 'hi') */
  get language() { return this._lang; }

  setLanguage(langCode) {
    if (!TRANSLATIONS[langCode]) {
      console.warn(`[i18n] Language "${langCode}" not available. Using 'en'.`);
      langCode = 'en';
    }
    this._lang = langCode;
    localStorage.setItem('medgenius_lang', langCode);
    document.documentElement.lang = langCode;
    document.documentElement.dir  = langCode === 'ar' ? 'rtl' : 'ltr';
    this._translatePage();
    this._listeners.forEach((fn) => fn(langCode));
  }

  /** Register a callback to fire when language changes */
  onChange(fn) { this._listeners.push(fn); }

  /** Re-translate all data-i18n elements on the page */
  translatePage() { this._translatePage(); }

  /** Return available languages */
  get languages() {
    return [
      { code: 'en', label: 'English',    nativeLabel: 'English' },
      { code: 'hi', label: 'Hindi',      nativeLabel: 'हिंदी'   },
    ];
  }

  // ── Language switcher UI ──────────────────────────────────────────────────

  /**
   * Inject a language toggle button into a container.
   * @param {string|HTMLElement} containerSelector
   */
  injectSwitcher(containerSelector) {
    const container = typeof containerSelector === 'string'
      ? document.querySelector(containerSelector)
      : containerSelector;
    if (!container) return;

    const switcher = document.createElement('div');
    switcher.className = 'lang-switcher';
    switcher.setAttribute('role', 'group');
    switcher.setAttribute('aria-label', 'Language selector');

    this.languages.forEach(({ code, nativeLabel }) => {
      const btn = document.createElement('button');
      btn.type        = 'button';
      btn.dataset.lang = code;
      btn.textContent  = nativeLabel;
      btn.className    = `lang-btn${this._lang === code ? ' active' : ''}`;
      btn.addEventListener('click', () => {
        this.setLanguage(code);
        switcher.querySelectorAll('.lang-btn').forEach((b) =>
          b.classList.toggle('active', b.dataset.lang === code)
        );
      });
      switcher.appendChild(btn);
    });

    container.appendChild(switcher);
    this._injectSwitcherStyles();
  }

  // ── Internals ──────────────────────────────────────────────────────────────

  _detectLanguage() {
    // Priority: localStorage → browser preference → default 'en'
    const saved    = localStorage.getItem('medgenius_lang');
    const browser  = navigator.language?.split('-')[0];
    const detected = saved || (TRANSLATIONS[browser] ? browser : 'en');
    return TRANSLATIONS[detected] ? detected : 'en';
  }

  _translatePage() {
    // data-i18n → textContent
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      el.textContent = this.t(el.dataset.i18n);
    });
    // data-i18n-placeholder → placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
      el.placeholder = this.t(el.dataset.i18nPlaceholder);
    });
    // data-i18n-title → title
    document.querySelectorAll('[data-i18n-title]').forEach((el) => {
      el.title = this.t(el.dataset.i18nTitle);
    });
    // data-i18n-aria-label → aria-label
    document.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
      el.setAttribute('aria-label', this.t(el.dataset.i18nAriaLabel));
    });
  }

  _injectSwitcherStyles() {
    if (document.getElementById('lang-switcher-styles')) return;
    const style = document.createElement('style');
    style.id = 'lang-switcher-styles';
    style.textContent = `
      .lang-switcher {
        display: inline-flex;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        overflow: hidden;
      }
      .lang-btn {
        padding: 5px 14px;
        background: transparent;
        border: none;
        font-size: 13px;
        font-weight: 500;
        color: #374151;
        cursor: pointer;
        transition: background 0.15s, color 0.15s;
      }
      .lang-btn + .lang-btn {
        border-left: 1px solid #d1d5db;
      }
      .lang-btn:hover  { background: #f9fafb; }
      .lang-btn.active {
        background: #3b82f6;
        color: #fff;
      }
    `;
    document.head.appendChild(style);
  }
}

// ── Singleton export ──────────────────────────────────────────────────────────
export const i18n = new I18n();

// Auto-translate on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  i18n.translatePage();
  document.documentElement.lang = i18n.language;
});

// Flask-Babel companion config reference (backend/babel.cfg):
// [python: **.py]
// encoding = utf-8
// [jinja2: **/templates/**.html]
// encoding = utf-8
// [javascript: **/frontend/**.js]
// encoding = utf-8
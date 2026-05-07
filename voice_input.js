/**
 * MedGenius — Voice Symptom Input  (Feature #14)
 * ════════════════════════════════════════════════
 * Uses the browser's built-in Web Speech API (SpeechRecognition).
 * Zero external dependencies. Works in Chrome, Edge, and Safari ≥ 14.7.
 *
 * Usage:
 *   import { VoiceInput } from './voice_input.js';
 *   const voice = new VoiceInput('#symptom-textarea', '#voice-btn');
 *   voice.init();
 */

export class VoiceInput {
  /**
   * @param {string|HTMLElement} targetSelector  - textarea/input to fill
   * @param {string|HTMLElement} buttonSelector  - mic button to toggle
   * @param {object}             options
   * @param {string}  options.lang        - BCP-47 language tag, e.g. 'en-IN', 'hi-IN'
   * @param {boolean} options.continuous  - keep listening until manually stopped
   * @param {function} options.onResult   - callback(transcript: string)
   * @param {function} options.onError    - callback(error: string)
   * @param {function} options.onStart    - callback()
   * @param {function} options.onEnd      - callback()
   */
  constructor(targetSelector, buttonSelector, options = {}) {
    this._target  = typeof targetSelector === 'string'
      ? document.querySelector(targetSelector)
      : targetSelector;
    this._btn     = typeof buttonSelector === 'string'
      ? document.querySelector(buttonSelector)
      : buttonSelector;

    this.lang       = options.lang       || 'en-IN';   // Indian English by default
    this.continuous = options.continuous !== false;     // defaults to true
    this.onResult   = options.onResult   || null;
    this.onError    = options.onError    || null;
    this.onStart    = options.onStart    || null;
    this.onEnd      = options.onEnd      || null;

    this._recognition = null;
    this._listening   = false;
    this._supported   = false;
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  /** Initialise — call once after DOM is ready */
  init() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      console.warn('[VoiceInput] Web Speech API not supported in this browser.');
      this._markUnsupported();
      return false;
    }

    this._recognition = new SpeechRecognition();
    this._recognition.lang           = this.lang;
    this._recognition.continuous     = this.continuous;
    this._recognition.interimResults = true;   // show partial results while speaking
    this._recognition.maxAlternatives = 1;

    this._recognition.onstart  = () => this._handleStart();
    this._recognition.onresult = (e)  => this._handleResult(e);
    this._recognition.onerror  = (e)  => this._handleError(e);
    this._recognition.onend    = ()   => this._handleEnd();

    if (this._btn) {
      this._btn.addEventListener('click', () => this.toggle());
      this._btn.title = 'Click to speak your symptoms';
    }

    this._supported = true;
    return true;
  }

  /** Start listening */
  start() {
    if (!this._recognition) return;
    if (this._listening)    return;
    this._recognition.start();
  }

  /** Stop listening */
  stop() {
    if (!this._recognition) return;
    if (!this._listening)   return;
    this._recognition.stop();
  }

  /** Toggle start/stop */
  toggle() {
    this._listening ? this.stop() : this.start();
  }

  /** Change language on the fly (stops recognition first) */
  setLanguage(langCode) {
    this.lang = langCode;
    if (this._recognition) {
      this.stop();
      this._recognition.lang = langCode;
    }
  }

  get isListening() { return this._listening; }
  get isSupported()  { return this._supported; }

  // ── Internal handlers ────────────────────────────────────────────────────────

  _handleStart() {
    this._listening = true;
    this._updateButton(true);
    this.onStart?.();
    console.log('[VoiceInput] Listening...');
  }

  _handleResult(event) {
    let interim    = '';
    let finalText  = '';

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalText += transcript + ' ';
      } else {
        interim += transcript;
      }
    }

    // Append final results to the textarea; show interim in a lighter colour
    if (finalText && this._target) {
      this._target.value = (this._target.value + ' ' + finalText).trim();
      // Trigger input event so any reactive frameworks pick up the change
      this._target.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // Show interim text as placeholder or data attribute
    if (this._target && interim) {
      this._target.dataset.interim = interim;
    } else if (this._target) {
      delete this._target.dataset.interim;
    }

    this.onResult?.(finalText.trim() || interim);
  }

  _handleError(event) {
    this._listening = false;
    this._updateButton(false);

    const MESSAGES = {
      'no-speech':          'No speech detected. Please try again.',
      'audio-capture':      'Microphone not accessible. Check browser permissions.',
      'not-allowed':        'Microphone permission denied. Please allow microphone access.',
      'network':            'Network error. Check your internet connection.',
      'aborted':            'Voice input was cancelled.',
      'language-not-supported': `Language "${this.lang}" is not supported.`,
    };
    const msg = MESSAGES[event.error] || `Voice error: ${event.error}`;
    console.error('[VoiceInput] Error:', event.error);
    this.onError?.(msg);
  }

  _handleEnd() {
    this._listening = false;
    this._updateButton(false);
    this.onEnd?.();
    console.log('[VoiceInput] Stopped.');
  }

  _updateButton(listening) {
    if (!this._btn) return;
    if (listening) {
      this._btn.classList.add('listening');
      this._btn.setAttribute('aria-label', 'Stop voice input');
      this._btn.title = 'Click to stop recording';
      this._btn.innerHTML = `
        <span class="mic-icon mic-active" aria-hidden="true">🎙️</span>
        <span class="mic-label">Listening…</span>
        <span class="mic-pulse"></span>
      `;
    } else {
      this._btn.classList.remove('listening');
      this._btn.setAttribute('aria-label', 'Start voice input');
      this._btn.title = 'Click to speak your symptoms';
      this._btn.innerHTML = `
        <span class="mic-icon" aria-hidden="true">🎤</span>
        <span class="mic-label">Speak symptoms</span>
      `;
    }
  }

  _markUnsupported() {
    if (!this._btn) return;
    this._btn.disabled = true;
    this._btn.title    = 'Voice input is not supported in this browser. Try Chrome or Edge.';
    this._btn.innerHTML = `<span>🎤 Not supported</span>`;
    this._btn.style.opacity = '0.4';
  }
}


// ── Convenience factory ──────────────────────────────────────────────────────

/**
 * Quick-setup: injects a mic button next to a textarea and wires everything up.
 *
 * @param {string} textareaId     - ID of the symptom textarea
 * @param {object} options
 * @param {string} options.lang               - default 'en-IN'
 * @param {string} options.buttonLabel        - default 'Speak symptoms'
 * @param {string} options.buttonClass        - CSS classes for the button
 * @param {function} options.onTranscript     - callback(text: string)
 * @param {function} options.onError          - callback(errorMsg: string)
 * @returns {VoiceInput}
 */
export function setupVoiceInput(textareaId, options = {}) {
  const textarea = document.getElementById(textareaId);
  if (!textarea) {
    console.error(`[VoiceInput] Textarea #${textareaId} not found`);
    return null;
  }

  // Create button
  const btn = document.createElement('button');
  btn.type        = 'button';
  btn.id          = `${textareaId}-voice-btn`;
  btn.className   = options.buttonClass || 'voice-btn';
  btn.setAttribute('aria-label', 'Start voice input');
  btn.innerHTML   = `<span class="mic-icon" aria-hidden="true">🎤</span><span class="mic-label">${options.buttonLabel || 'Speak symptoms'}</span>`;

  // Insert button right after textarea
  textarea.insertAdjacentElement('afterend', btn);

  // Inject minimal CSS if not already present
  if (!document.getElementById('voice-input-styles')) {
    const style = document.createElement('style');
    style.id = 'voice-input-styles';
    style.textContent = `
      .voice-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 14px;
        margin-top: 6px;
        border: 2px solid #3b82f6;
        border-radius: 8px;
        background: transparent;
        color: #3b82f6;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        position: relative;
      }
      .voice-btn:hover {
        background: #3b82f6;
        color: #fff;
      }
      .voice-btn.listening {
        background: #ef4444;
        border-color: #ef4444;
        color: #fff;
        animation: pulse-border 1.5s infinite;
      }
      .mic-pulse {
        position: absolute;
        inset: -4px;
        border-radius: 10px;
        border: 2px solid #ef4444;
        animation: pulse-ring 1.5s ease-out infinite;
      }
      @keyframes pulse-border {
        0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
        50%       { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
      }
      @keyframes pulse-ring {
        0%   { transform: scale(1);   opacity: 0.8; }
        100% { transform: scale(1.3); opacity: 0; }
      }
      .voice-lang-select {
        margin-top: 4px;
        padding: 4px 8px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        font-size: 12px;
        color: #374151;
      }
    `;
    document.head.appendChild(style);
  }

  // Optional language picker
  if (options.showLangPicker) {
    const select = document.createElement('select');
    select.className = 'voice-lang-select';
    select.innerHTML = `
      <option value="en-IN">English (India)</option>
      <option value="en-US">English (US)</option>
      <option value="hi-IN">हिंदी (Hindi)</option>
      <option value="mr-IN">मराठी (Marathi)</option>
      <option value="ta-IN">தமிழ் (Tamil)</option>
      <option value="te-IN">తెలుగు (Telugu)</option>
      <option value="bn-IN">বাংলা (Bengali)</option>
    `;
    btn.insertAdjacentElement('afterend', select);
    select.addEventListener('change', () => voice.setLanguage(select.value));
  }

  const voice = new VoiceInput(textarea, btn, {
    lang:     options.lang || 'en-IN',
    onResult: options.onTranscript || null,
    onError:  options.onError || ((msg) => {
      console.warn('[VoiceInput]', msg);
      // Surface error to user as a toast or inline message
      const errEl = document.createElement('p');
      errEl.style.cssText = 'color:#ef4444;font-size:12px;margin-top:4px;';
      errEl.textContent = msg;
      btn.insertAdjacentElement('afterend', errEl);
      setTimeout(() => errEl.remove(), 4000);
    }),
  });

  voice.init();
  return voice;
}
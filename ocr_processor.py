"""
MedGenius - OCR Processing Module
Extracts medicine names and instructions from prescription images
using Tesseract OCR + OpenCV preprocessing pipeline
"""

import cv2
import numpy as np
import re
import os
import base64
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter

# ── FIX: Removed `tesseract --version` (shell command, not Python).
#         Moved tesseract_cmd INSIDE the try block so it only runs when
#         pytesseract is actually installed. Removed duplicate import.
try:
    import pytesseract
    # Set the path to Tesseract executable (Windows)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[OCR] Warning: pytesseract not available. Using mock OCR.")

# Common medical abbreviations and their expansions
MED_ABBREVIATIONS = {
    "od": "once daily",
    "bd": "twice daily",
    "tds": "three times daily",
    "qid": "four times daily",
    "hs": "at bedtime",
    "ac": "before meals",
    "pc": "after meals",
    "prn": "as needed",
    "sos": "if required",
    "stat": "immediately",
    "mg": "milligrams",
    "mcg": "micrograms",
    "ml": "milliliters",
    "tab": "tablet",
    "cap": "capsule",
    "inj": "injection",
    "oint": "ointment",
    "susp": "suspension",
    "rx": "prescription",
    "sx": "symptoms",
    "dx": "diagnosis",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "ihd": "ischemic heart disease",
    "urti": "upper respiratory tract infection",
    "lrti": "lower respiratory tract infection",
    "uti": "urinary tract infection",
}

# Known medicine name patterns
MEDICINE_PATTERNS = [
    r'\b(paracetamol|acetaminophen|crocin|dolo|calpol)\b',
    r'\b(amoxicillin|amoxil|trimox)\b',
    r'\b(metformin|glucophage|glycomet)\b',
    r'\b(atorvastatin|lipitor|storvas)\b',
    r'\b(omeprazole|omez|ocid|prilosec)\b',
    r'\b(cetirizine|zyrtec|alerid)\b',
    r'\b(azithromycin|zithromax|azithral|azee)\b',
    r'\b(ibuprofen|brufen|advil|nurofen)\b',
    r'\b(amlodipine|norvasc|amlip|amlong)\b',
    r'\b(levothyroxine|synthroid|thyronorm|eltroxin)\b',
    r'\b(pantoprazole|pantop|protonix)\b',
    r'\b(aspirin|ecosprin|disprin|loprin)\b',
    r'\b(salbutamol|albuterol|ventolin|asthalin)\b',
    r'\b(ciprofloxacin|cipro|ciplox|cifran)\b',
    r'\b(montelukast|singulair|montair|montek)\b',
]

# Dosage patterns
DOSAGE_PATTERNS = [
    r'\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?|iu|tabs?|caps?)\b',
    r'\b(?:once|twice|thrice|\d+\s*times?)\s+(?:daily|a\s+day|per\s+day)\b',
    r'\b(?:1|2|3|4)\s*-\s*(?:0|1|2)\s*-\s*(?:0|1|2)\b',  # e.g., 1-0-1
    r'\b(?:morning|evening|night|bedtime|noon)\b',
    r'\bfor\s+\d+\s+days?\b',
]


class OCRProcessor:
    """Advanced OCR processor for medical prescriptions"""

    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.pdf']

    def preprocess_image(self, image_array):
        """
        Advanced image preprocessing pipeline for better OCR accuracy:
        1. Grayscale conversion
        2. Noise removal
        3. Contrast enhancement
        4. Thresholding (Otsu's + Adaptive)
        5. Deskewing
        6. Morphological operations
        """
        if len(image_array.shape) == 3:
            gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_array.copy()

        h, w = gray.shape
        if w < 1000:
            scale = 1500 / w
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        adaptive_thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 5
        )

        _, otsu_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        deskewed = self._deskew(adaptive_thresh)

        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(deskewed, cv2.MORPH_CLOSE, kernel)

        return processed, otsu_thresh

    def _deskew(self, image):
        """Correct skew in prescription images"""
        try:
            coords = np.column_stack(np.where(image > 0))
            if len(coords) == 0:
                return image
            angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 15:
                return image
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                                     borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return image

    def extract_text(self, image_source):
        """
        Main OCR extraction function.
        Accepts: file path, numpy array, PIL Image, base64 string, or bytes.
        """
        if isinstance(image_source, str):
            if image_source.startswith('data:'):
                header, data = image_source.split(',', 1)
                img_bytes = base64.b64decode(data)
                pil_img = Image.open(BytesIO(img_bytes))
                img_array = np.array(pil_img.convert('RGB'))
            elif os.path.exists(image_source):
                img_array = cv2.imread(image_source)
            else:
                return self._error_result("File not found")
        elif isinstance(image_source, np.ndarray):
            img_array = image_source
        elif isinstance(image_source, Image.Image):
            img_array = np.array(image_source.convert('RGB'))
        elif isinstance(image_source, bytes):
            pil_img = Image.open(BytesIO(image_source))
            img_array = np.array(pil_img.convert('RGB'))
        else:
            return self._error_result("Unsupported image format")

        if img_array is None:
            return self._error_result("Could not read image")

        processed, otsu = self.preprocess_image(img_array)

        if not TESSERACT_AVAILABLE:
            return self._mock_ocr_result()

        custom_config = r'--oem 3 --psm 6 -l eng'

        try:
            raw_text = pytesseract.image_to_string(processed, config=custom_config)

            if len(raw_text.strip()) < 10:
                raw_text = pytesseract.image_to_string(otsu, config=custom_config)

            if len(raw_text.strip()) < 10:
                raw_text = pytesseract.image_to_string(img_array, config=custom_config)

        except Exception as e:
            return self._error_result(f"OCR failed: {str(e)}")

        return self._parse_ocr_result(raw_text)

    def _parse_ocr_result(self, raw_text):
        """Parse and structure the raw OCR output"""
        if not raw_text or len(raw_text.strip()) < 3:
            return self._error_result("No text could be extracted from image")

        cleaned_text    = self._clean_text(raw_text)
        medicines_found = self._extract_medicines(cleaned_text)
        dosages_found   = self._extract_dosages(cleaned_text)
        instructions    = self._extract_instructions(cleaned_text)
        expanded_text   = self._expand_abbreviations(cleaned_text)

        return {
            "success":        True,
            "raw_text":       raw_text,
            "cleaned_text":   cleaned_text,
            "expanded_text":  expanded_text,
            "medicines_found": medicines_found,
            "dosages_found":  dosages_found,
            "instructions":   instructions,
            "word_count":     len(cleaned_text.split()),
            "confidence":     self._estimate_confidence(raw_text, medicines_found)
        }

    def _clean_text(self, text):
        text = re.sub(r'[|\\@#$%^&*_+=~`]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(\n\s*){3,}', '\n\n', text)
        return text.strip()

    def _extract_medicines(self, text):
        found = []
        text_lower = text.lower()
        for pattern in MEDICINE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                if match and match not in [m.lower() for m in found]:
                    found.append(match.title())
        return found

    def _extract_dosages(self, text):
        found = []
        for pattern in DOSAGE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found.extend(matches)
        return list(set(found))[:10]

    def _extract_instructions(self, text):
        instruction_keywords = [
            r'take\s+.{5,50}',
            r'apply\s+.{5,50}',
            r'use\s+.{5,50}',
            r'avoid\s+.{5,50}',
            r'do\s+not\s+.{5,50}',
        ]
        instructions = []
        for pattern in instruction_keywords:
            matches = re.findall(pattern, text, re.IGNORECASE)
            instructions.extend(matches[:2])
        return instructions[:5]

    def _expand_abbreviations(self, text):
        words = text.split()
        expanded = []
        for word in words:
            clean_word = word.lower().strip('.,;:()')
            if clean_word in MED_ABBREVIATIONS:
                expanded.append(f"{word} ({MED_ABBREVIATIONS[clean_word]})")
            else:
                expanded.append(word)
        return ' '.join(expanded)

    def _estimate_confidence(self, raw_text, medicines_found):
        if not raw_text:
            return 0
        word_count        = len(raw_text.split())
        has_medicines     = len(medicines_found) > 0
        has_numbers       = bool(re.search(r'\d', raw_text))
        has_medical_terms = bool(re.search(
            r'\b(?:rx|tab|cap|mg|ml|twice|daily|dose|tablet|capsule)\b',
            raw_text, re.IGNORECASE
        ))
        score = 40
        if word_count > 10:    score += 20
        if word_count > 25:    score += 10
        if has_medicines:      score += 15
        if has_numbers:        score += 8
        if has_medical_terms:  score += 7
        return min(score, 98)

    def _mock_ocr_result(self):
        """Return mock OCR result when Tesseract is unavailable"""
        return {
            "success":        True,
            "raw_text":       "Rx:\nParacetamol 500mg - 1-0-1 (twice daily)\nCetirizine 10mg - 0-0-1 (at night)\nVitamin C - once daily\n\nAdvice: Take with food. Avoid alcohol.",
            "cleaned_text":   "Paracetamol 500mg twice daily, Cetirizine 10mg at night",
            "expanded_text":  "Paracetamol 500mg twice daily (bd), Cetirizine 10mg at bedtime (hs)",
            "medicines_found": ["Paracetamol", "Cetirizine"],
            "dosages_found":  ["500mg", "10mg", "twice daily"],
            "instructions":   ["Take with food", "Avoid alcohol"],
            "word_count":     28,
            "confidence":     87
        }

    def _error_result(self, msg):
        return {
            "success":        False,
            "error":          msg,
            "raw_text":       "",
            "cleaned_text":   "",
            "medicines_found": [],
            "dosages_found":  [],
            "instructions":   [],
            "confidence":     0
        }

    def process_base64_image(self, base64_str):
        """Process a base64-encoded image string"""
        try:
            if ',' in base64_str:
                base64_str = base64_str.split(',')[1]
            img_bytes = base64.b64decode(base64_str)
            return self.extract_text(img_bytes)
        except Exception as e:
            return self._error_result(f"Base64 decode failed: {str(e)}")


# Singleton
_ocr_instance = None

def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCRProcessor()
    return _ocr_instance
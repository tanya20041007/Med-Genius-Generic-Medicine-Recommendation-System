"""
MedGenius - Dosage Calculator Module  (Feature #6)

Calculates safe medicine dosages based on:
  - Patient weight (kg)
  - Patient age
  - Patient type: adult / child / infant / elderly
  - Condition being treated

API endpoints:
  POST /api/dosage/calculate
       Body: { "medicine_id": 1, "weight_kg": 60, "age": 30,
               "patient_type": "adult", "condition": "fever" }
       → Returns: recommended dose, frequency, duration, warnings

  GET  /api/dosage/medicines
       → Returns list of medicines that have calculator support
"""

from flask import Blueprint, request, jsonify
from medicine_data import MEDICINES_DB, get_medicine_by_id

dosage_bp = Blueprint('dosage', __name__)


# ── Dosage rules database ─────────────────────────────────────────────────────
# Each entry: medicine_id → { patient_type → dosage rules }
# Weights are in kg, doses in mg.
# Dosage formulas:
#   "fixed"   → fixed mg regardless of weight
#   "per_kg"  → mg per kg of body weight (e.g. 10–15 mg/kg for paracetamol in children)

DOSAGE_RULES = {
    1: {  # Paracetamol
        "adult": {
            "dose_mg": 500, "max_dose_mg": 1000,
            "formula": "fixed", "frequency": "Every 4–6 hours", "max_daily_mg": 4000,
            "note": "Do not exceed 4g per day. Reduce to 2g/day with liver disease or alcohol use."
        },
        "elderly": {
            "dose_mg": 500, "max_dose_mg": 500,
            "formula": "fixed", "frequency": "Every 6–8 hours", "max_daily_mg": 2000,
            "note": "Use lower doses in elderly. Max 2g/day recommended due to reduced liver function."
        },
        "child": {
            "dose_mg_per_kg": 15, "max_dose_mg": 500,
            "formula": "per_kg", "frequency": "Every 4–6 hours", "max_daily_mg_per_kg": 60,
            "note": "Do not exceed 75mg/kg/day or 4g/day."
        },
        "infant": {
            "dose_mg_per_kg": 10, "max_dose_mg": 120,
            "formula": "per_kg", "frequency": "Every 6–8 hours", "max_daily_mg_per_kg": 40,
            "note": "Use infant suspension. Consult paediatrician for infants under 3 months."
        }
    },
    2: {  # Amoxicillin
        "adult": {
            "dose_mg": 500, "max_dose_mg": 875,
            "formula": "fixed", "frequency": "Every 8 hours", "max_daily_mg": 2625,
            "note": "For severe infections, 875mg every 8–12 hours. Complete full 7–14 day course."
        },
        "elderly": {
            "dose_mg": 500, "max_dose_mg": 500,
            "formula": "fixed", "frequency": "Every 8 hours", "max_daily_mg": 1500,
            "note": "Adjust dose if kidney function is impaired."
        },
        "child": {
            "dose_mg_per_kg": 25, "max_dose_mg": 500,
            "formula": "per_kg", "frequency": "Every 8 hours", "max_daily_mg_per_kg": 75,
            "note": "For ear/throat infections. Use oral suspension for children under 5."
        },
        "infant": {
            "dose_mg_per_kg": 20, "max_dose_mg": 125,
            "formula": "per_kg", "frequency": "Every 12 hours", "max_daily_mg_per_kg": 40,
            "note": "Use amoxicillin suspension. Must be prescribed by doctor."
        }
    },
    3: {  # Metformin
        "adult": {
            "dose_mg": 500, "max_dose_mg": 1000,
            "formula": "fixed", "frequency": "Twice daily with meals", "max_daily_mg": 2000,
            "note": "Start with 500mg once daily, increase slowly. Always take with food."
        },
        "elderly": {
            "dose_mg": 500, "max_dose_mg": 500,
            "formula": "fixed", "frequency": "Once daily with main meal", "max_daily_mg": 1000,
            "note": "Monitor kidney function regularly. Reduce or stop if eGFR < 30."
        },
        "child": {
            "dose_mg": 500, "max_dose_mg": 500,
            "formula": "fixed", "frequency": "Once daily with food", "max_daily_mg": 1000,
            "note": "Only for children 10+ with type 2 diabetes. Must be prescribed."
        },
        "infant": {
            "dose_mg": 0, "max_dose_mg": 0,
            "formula": "fixed", "frequency": "Not recommended", "max_daily_mg": 0,
            "note": "Metformin is NOT recommended for infants. Consult paediatrician."
        }
    },
    5: {  # Omeprazole
        "adult": {
            "dose_mg": 20, "max_dose_mg": 40,
            "formula": "fixed", "frequency": "Once daily (morning, before food)", "max_daily_mg": 40,
            "note": "Take 30 minutes before breakfast. For GERD, 4–8 weeks. For ulcers, 4–8 weeks."
        },
        "elderly": {
            "dose_mg": 20, "max_dose_mg": 20,
            "formula": "fixed", "frequency": "Once daily (morning)", "max_daily_mg": 20,
            "note": "No dose adjustment needed. Review need regularly."
        },
        "child": {
            "dose_mg_per_kg": 0.7, "max_dose_mg": 20,
            "formula": "per_kg", "frequency": "Once daily before food", "max_daily_mg_per_kg": 1.4,
            "note": "For children 1+ year. Use dispersible tablets or suspension."
        },
        "infant": {
            "dose_mg": 0, "max_dose_mg": 0,
            "formula": "fixed", "frequency": "Not recommended without specialist advice",
            "max_daily_mg": 0,
            "note": "Use only under specialist paediatric supervision."
        }
    },
    6: {  # Cetirizine
        "adult": {
            "dose_mg": 10, "max_dose_mg": 10,
            "formula": "fixed", "frequency": "Once daily (evening preferred)", "max_daily_mg": 10,
            "note": "Take at night — may cause drowsiness. Avoid alcohol and driving."
        },
        "elderly": {
            "dose_mg": 5, "max_dose_mg": 10,
            "formula": "fixed", "frequency": "Once daily (evening)", "max_daily_mg": 10,
            "note": "Start with 5mg due to increased sensitivity. Monitor for drowsiness."
        },
        "child": {
            "dose_mg": 5, "max_dose_mg": 10,
            "formula": "fixed", "frequency": "Once daily (evening)", "max_daily_mg": 10,
            "note": "5mg for ages 2–5; 10mg for ages 6+. Use liquid formulation for young children."
        },
        "infant": {
            "dose_mg": 0, "max_dose_mg": 0,
            "formula": "fixed", "frequency": "Not recommended under 2 years",
            "max_daily_mg": 0,
            "note": "Not recommended for infants under 2 years without doctor guidance."
        }
    },
    8: {  # Ibuprofen
        "adult": {
            "dose_mg": 400, "max_dose_mg": 600,
            "formula": "fixed", "frequency": "Every 6–8 hours with food", "max_daily_mg": 1800,
            "note": "Always take with food or milk. Avoid if history of ulcers or kidney disease."
        },
        "elderly": {
            "dose_mg": 200, "max_dose_mg": 400,
            "formula": "fixed", "frequency": "Every 8 hours with food", "max_daily_mg": 1200,
            "note": "High risk of GI and renal side effects in elderly. Prefer paracetamol."
        },
        "child": {
            "dose_mg_per_kg": 5, "max_dose_mg": 300,
            "formula": "per_kg", "frequency": "Every 6–8 hours with food", "max_daily_mg_per_kg": 30,
            "note": "Only for children 3 months+. Use ibuprofen suspension. Not for infants under 5kg."
        },
        "infant": {
            "dose_mg_per_kg": 5, "max_dose_mg": 50,
            "formula": "per_kg", "frequency": "Every 6–8 hours", "max_daily_mg_per_kg": 20,
            "note": "Only for infants 3 months+ and over 5kg. Consult GP before use."
        }
    }
}

# Medicines with dosage calculator support
SUPPORTED_MEDICINE_IDS = set(DOSAGE_RULES.keys())


# ── Core calculation logic ────────────────────────────────────────────────────

def calculate_dose(medicine_id: int, weight_kg: float, age: int,
                   patient_type: str) -> dict:
    """
    Calculate a recommended dose for a given medicine and patient.
    Returns a full dosage recommendation dict or an error dict.
    """
    rules = DOSAGE_RULES.get(medicine_id, {}).get(patient_type)
    if not rules:
        return {"error": f"No dosage data for this medicine and patient type."}

    med = get_medicine_by_id(medicine_id)
    if not med:
        return {"error": "Medicine not found."}

    formula = rules.get("formula", "fixed")

    if formula == "per_kg":
        dose_mg_per_kg = rules.get("dose_mg_per_kg", 0)
        calculated     = round(weight_kg * dose_mg_per_kg)
        max_dose       = rules.get("max_dose_mg", calculated)
        recommended    = min(calculated, max_dose)

        # Max daily from per_kg rule
        max_daily_per_kg = rules.get("max_daily_mg_per_kg", 0)
        max_daily        = round(weight_kg * max_daily_per_kg) if max_daily_per_kg else None
    else:
        recommended = rules.get("dose_mg", 0)
        max_dose    = rules.get("max_dose_mg", recommended)
        max_daily   = rules.get("max_daily_mg")

    # Build warnings
    warnings = []
    if patient_type == "infant":
        warnings.append("⚠️ Always consult a paediatrician before giving medicine to an infant.")
    if patient_type == "elderly":
        warnings.append("⚠️ Elderly patients may be more sensitive. Start with lowest dose.")
    if age > 0 and age < 2 and patient_type == "child":
        warnings.append("⚠️ Use with caution in children under 2 years. Consult a doctor.")
    if weight_kg < 10 and patient_type in ("child", "infant"):
        warnings.append("⚠️ Very low body weight. Paediatric specialist advice is recommended.")

    # Build the full recommendation
    result = {
        "medicine_id":       medicine_id,
        "medicine_name":     med["name"],
        "generic_name":      med["generic_name"],
        "patient_type":      patient_type,
        "weight_kg":         weight_kg,
        "age_years":         age,
        "recommended_dose":  f"{recommended} mg",
        "max_single_dose":   f"{max_dose} mg",
        "frequency":         rules["frequency"],
        "max_daily_dose":    f"{max_daily} mg/day" if max_daily else "As directed",
        "clinical_note":     rules.get("note", ""),
        "warnings":          warnings,
        "disclaimer":        (
            "⚠️ This calculator provides general guidance only. "
            "Actual dosing must be confirmed with a licensed pharmacist or doctor. "
            "Never self-medicate without professional advice."
        )
    }

    # Add formula breakdown for transparency
    if formula == "per_kg":
        result["dose_formula"] = (
            f"{rules.get('dose_mg_per_kg')} mg/kg × {weight_kg} kg "
            f"= {calculated} mg (capped at {max_dose} mg)"
        )

    return result


# ── Routes ───────────────────────────────────────────────────────────────────

@dosage_bp.route('/api/dosage/medicines', methods=['GET'])
def supported_medicines():
    """Return the list of medicines that the dosage calculator supports"""
    supported = []
    for med in MEDICINES_DB:
        if med['id'] in SUPPORTED_MEDICINE_IDS:
            supported.append({
                'id':           med['id'],
                'name':         med['name'],
                'generic_name': med['generic_name'],
                'category':     med['category'],
                'patient_types': list(DOSAGE_RULES[med['id']].keys())
            })
    return jsonify({
        'count':     len(supported),
        'medicines': supported
    })


@dosage_bp.route('/api/dosage/calculate', methods=['POST'])
def calculate():
    """
    Calculate dosage for a given medicine and patient profile.

    Required body fields:
      medicine_id   (int)   — ID from MEDICINES_DB
      weight_kg     (float) — patient weight in kilograms
      age           (int)   — patient age in years
      patient_type  (str)   — one of: adult | child | infant | elderly

    Optional:
      condition     (str)   — what condition is being treated (informational)
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    # ── Validate medicine_id ──
    try:
        medicine_id = int(data.get('medicine_id', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'medicine_id must be an integer'}), 400

    if medicine_id not in SUPPORTED_MEDICINE_IDS:
        supported_names = [m['name'] for m in MEDICINES_DB if m['id'] in SUPPORTED_MEDICINE_IDS]
        return jsonify({
            'error':             'Dosage calculator not available for this medicine.',
            'supported_medicines': supported_names
        }), 400

    # ── Validate weight ──
    try:
        weight_kg = float(data.get('weight_kg', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'weight_kg must be a number'}), 400
    if not (1 <= weight_kg <= 300):
        return jsonify({'error': 'weight_kg must be between 1 and 300'}), 400

    # ── Validate age ──
    try:
        age = int(data.get('age', -1))
    except (TypeError, ValueError):
        return jsonify({'error': 'age must be an integer (years)'}), 400
    if not (0 <= age <= 120):
        return jsonify({'error': 'age must be between 0 and 120'}), 400

    # ── Validate patient_type ──
    valid_types  = {'adult', 'child', 'infant', 'elderly'}
    patient_type = str(data.get('patient_type', '')).lower().strip()
    if patient_type not in valid_types:
        # Auto-determine if not given
        if age < 1:
            patient_type = 'infant'
        elif age < 12:
            patient_type = 'child'
        elif age >= 65:
            patient_type = 'elderly'
        else:
            patient_type = 'adult'

    condition = str(data.get('condition', '')).strip()[:200]

    # ── Calculate ──
    result = calculate_dose(medicine_id, weight_kg, age, patient_type)

    if 'error' in result:
        return jsonify(result), 400

    if condition:
        result['condition'] = condition

    return jsonify({'success': True, 'dosage': result})
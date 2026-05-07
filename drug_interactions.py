"""
MedGenius - Drug Interaction Engine
Checks for potentially dangerous interactions between medicines
Based on known pharmacological interaction data
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


# ── Severity levels ───────────────────────────────────────────────────────────
SEVERITY = {
    "CONTRAINDICATED": {"level": 4, "label": "Contraindicated",  "color": "#ef4444", "icon": "🚫"},
    "MAJOR":           {"level": 3, "label": "Major Interaction", "color": "#f97316", "icon": "⛔"},
    "MODERATE":        {"level": 2, "label": "Moderate",          "color": "#f59e0b", "icon": "⚠️"},
    "MINOR":           {"level": 1, "label": "Minor",             "color": "#22c55e", "icon": "ℹ️"},
}


@dataclass
class DrugInteraction:
    drug_a:       str
    drug_b:       str
    severity:     str                 # key from SEVERITY dict
    mechanism:    str                 # pharmacological reason
    effect:       str                 # clinical effect
    management:   str                 # what to do
    references:   List[str] = field(default_factory=list)

    @property
    def severity_info(self) -> dict:
        return SEVERITY.get(self.severity, SEVERITY["MINOR"])

    def to_dict(self) -> dict:
        return {
            "drug_a":      self.drug_a,
            "drug_b":      self.drug_b,
            "severity":    self.severity,
            "severity_info": self.severity_info,
            "mechanism":   self.mechanism,
            "effect":      self.effect,
            "management":  self.management,
        }


# ── Interaction Database ─────────────────────────────────────────────────────
# Format: (Drug A, Drug B) — always alphabetically consistent

INTERACTIONS: List[DrugInteraction] = [

    # ── Aspirin interactions ──────────────────────────────
    DrugInteraction(
        drug_a="Aspirin", drug_b="Ibuprofen",
        severity="MAJOR",
        mechanism="Competition for the same COX-1 binding site",
        effect="Ibuprofen may reduce Aspirin's cardioprotective antiplatelet effect. Combined GI bleeding risk increased.",
        management="Avoid concurrent use if Aspirin is for cardiovascular protection. If NSAIDs needed, take Aspirin 2 hours before Ibuprofen.",
    ),
    DrugInteraction(
        drug_a="Aspirin", drug_b="Warfarin",
        severity="MAJOR",
        mechanism="Additive anticoagulant/antiplatelet effect",
        effect="Significantly elevated risk of bleeding, including GI and intracranial hemorrhage.",
        management="Combination generally avoided; if necessary, use lowest effective doses with close INR monitoring.",
    ),
    DrugInteraction(
        drug_a="Aspirin", drug_b="Methotrexate",
        severity="MAJOR",
        mechanism="Aspirin reduces renal clearance of Methotrexate",
        effect="Elevated Methotrexate levels → toxicity (bone marrow suppression, mucositis).",
        management="Avoid combination. If unavoidable, reduce Methotrexate dose and monitor CBC/LFTs closely.",
    ),

    # ── Paracetamol interactions ──────────────────────────
    DrugInteraction(
        drug_a="Paracetamol", drug_b="Warfarin",
        severity="MODERATE",
        mechanism="Paracetamol inhibits vitamin K epoxide reductase at high doses",
        effect="Increased INR at doses ≥2 g/day; bleeding risk.",
        management="Limit Paracetamol to <2 g/day. Monitor INR. Avoid chronic high-dose use.",
    ),
    DrugInteraction(
        drug_a="Paracetamol", drug_b="Alcohol",
        severity="MAJOR",
        mechanism="Alcohol induces CYP2E1, producing more toxic NAPQI metabolite",
        effect="Hepatotoxicity, acute liver failure even at therapeutic doses.",
        management="Advise patients to limit/avoid alcohol. Do not exceed 2 g/day in alcohol users.",
    ),
    DrugInteraction(
        drug_a="Isoniazid", drug_b="Paracetamol",
        severity="MAJOR",
        mechanism="Isoniazid induces CYP2E1, increasing hepatotoxic NAPQI production",
        effect="Severe hepatotoxicity.",
        management="Avoid concurrent use or use minimum effective Paracetamol dose with close liver monitoring.",
    ),

    # ── Metformin interactions ────────────────────────────
    DrugInteraction(
        drug_a="Alcohol", drug_b="Metformin",
        severity="MODERATE",
        mechanism="Alcohol inhibits hepatic gluconeogenesis and potentiates lactic acidosis risk",
        effect="Risk of hypoglycaemia and lactic acidosis.",
        management="Advise patients to avoid excessive alcohol. Monitor renal function.",
    ),
    DrugInteraction(
        drug_a="Furosemide", drug_b="Metformin",
        severity="MODERATE",
        mechanism="Furosemide increases Metformin plasma levels by competing for renal tubular secretion",
        effect="Metformin toxicity risk; lactic acidosis.",
        management="Monitor renal function; adjust Metformin dose if needed.",
    ),
    DrugInteraction(
        drug_a="Cimetidine", drug_b="Metformin",
        severity="MODERATE",
        mechanism="Cimetidine reduces renal tubular secretion of Metformin",
        effect="Increased Metformin exposure and lactic acidosis risk.",
        management="Use alternative H2 blocker (e.g., ranitidine) or PPI. Monitor kidney function.",
    ),

    # ── Warfarin interactions ─────────────────────────────
    DrugInteraction(
        drug_a="Ciprofloxacin", drug_b="Warfarin",
        severity="MAJOR",
        mechanism="Ciprofloxacin inhibits CYP1A2, reducing Warfarin metabolism",
        effect="Increased INR → bleeding risk.",
        management="Monitor INR closely when starting/stopping Ciprofloxacin. Adjust Warfarin dose accordingly.",
    ),
    DrugInteraction(
        drug_a="Azithromycin", drug_b="Warfarin",
        severity="MODERATE",
        mechanism="Azithromycin may inhibit CYP3A4 and alter gut flora affecting Vitamin K",
        effect="Increased INR and bleeding risk.",
        management="Monitor INR during and after antibiotic course.",
    ),
    DrugInteraction(
        drug_a="Atorvastatin", drug_b="Warfarin",
        severity="MODERATE",
        mechanism="Possible CYP2C9 competition",
        effect="Modest increase in INR.",
        management="Monitor INR when starting or changing statin dose.",
    ),
    DrugInteraction(
        drug_a="Omeprazole", drug_b="Warfarin",
        severity="MINOR",
        mechanism="Omeprazole inhibits CYP2C19, slight effect on Warfarin S-isomer",
        effect="Minor INR elevation in some patients.",
        management="Routine INR monitoring is sufficient.",
    ),

    # ── Statins interactions ──────────────────────────────
    DrugInteraction(
        drug_a="Atorvastatin", drug_b="Cyclosporine",
        severity="CONTRAINDICATED",
        mechanism="Cyclosporine is a potent CYP3A4 inhibitor, massively increasing statin exposure",
        effect="Severe rhabdomyolysis risk.",
        management="Avoid combination. Use pravastatin (not CYP3A4 dependent) with cyclosporine.",
    ),
    DrugInteraction(
        drug_a="Atorvastatin", drug_b="Grapefruit Juice",
        severity="MODERATE",
        mechanism="Grapefruit inhibits intestinal CYP3A4, increasing Atorvastatin bioavailability",
        effect="Elevated statin levels → increased myopathy/rhabdomyolysis risk.",
        management="Advise patients to avoid grapefruit and grapefruit juice.",
    ),
    DrugInteraction(
        drug_a="Atorvastatin", drug_b="Niacin",
        severity="MODERATE",
        mechanism="Pharmacodynamic additive effect on muscle",
        effect="Increased risk of myopathy and rhabdomyolysis.",
        management="Use combination cautiously; monitor for muscle pain and CK levels.",
    ),

    # ── Amlodipine interactions ───────────────────────────
    DrugInteraction(
        drug_a="Amlodipine", drug_b="Simvastatin",
        severity="MODERATE",
        mechanism="Amlodipine inhibits CYP3A4, increasing Simvastatin exposure",
        effect="Higher risk of statin-induced myopathy.",
        management="Do not exceed Simvastatin 20 mg/day with Amlodipine. Switch to Atorvastatin if higher dose needed.",
    ),
    DrugInteraction(
        drug_a="Amlodipine", drug_b="Cyclosporine",
        severity="MODERATE",
        mechanism="Amlodipine inhibits CYP3A4; Cyclosporine also inhibits P-gp",
        effect="Increased Amlodipine exposure.",
        management="Monitor blood pressure carefully; may need dose reduction.",
    ),

    # ── Ciprofloxacin interactions ────────────────────────
    DrugInteraction(
        drug_a="Ciprofloxacin", drug_b="Theophylline",
        severity="MAJOR",
        mechanism="Ciprofloxacin inhibits CYP1A2, reducing Theophylline clearance",
        effect="Theophylline toxicity: seizures, arrhythmia.",
        management="Reduce Theophylline dose by 50% when adding Ciprofloxacin. Monitor serum levels.",
    ),
    DrugInteraction(
        drug_a="Ciprofloxacin", drug_b="Antacids",
        severity="MODERATE",
        mechanism="Chelation of Ciprofloxacin by di/trivalent cations (Mg²⁺, Al³⁺, Ca²⁺)",
        effect="Significantly reduced Ciprofloxacin absorption (up to 90% reduction).",
        management="Administer antacids at least 2 hours after Ciprofloxacin.",
    ),
    DrugInteraction(
        drug_a="Azithromycin", drug_b="Ciprofloxacin",
        severity="MAJOR",
        mechanism="Additive QT-prolonging effects",
        effect="Risk of torsades de pointes and potentially fatal arrhythmia.",
        management="Avoid concurrent use. If unavoidable, obtain baseline ECG and monitor QTc interval.",
    ),

    # ── Omeprazole / PPI interactions ─────────────────────
    DrugInteraction(
        drug_a="Clopidogrel", drug_b="Omeprazole",
        severity="MAJOR",
        mechanism="Omeprazole inhibits CYP2C19, reducing conversion of Clopidogrel to active metabolite",
        effect="Reduced antiplatelet effect → increased cardiovascular events.",
        management="Use Pantoprazole (weaker CYP2C19 inhibitor) instead. Consult cardiologist.",
    ),
    DrugInteraction(
        drug_a="Methotrexate", drug_b="Omeprazole",
        severity="MODERATE",
        mechanism="PPIs inhibit renal tubular secretion of Methotrexate",
        effect="Elevated Methotrexate levels → toxicity.",
        management="Monitor Methotrexate levels; consider dose adjustment or temporary PPI cessation.",
    ),

    # ── Levothyroxine interactions ────────────────────────
    DrugInteraction(
        drug_a="Calcium Carbonate", drug_b="Levothyroxine",
        severity="MODERATE",
        mechanism="Calcium forms an insoluble complex with Levothyroxine in the GI tract",
        effect="Significantly reduced Levothyroxine absorption → hypothyroidism.",
        management="Take Levothyroxine at least 4 hours before or after calcium supplements.",
    ),
    DrugInteraction(
        drug_a="Iron Supplement", drug_b="Levothyroxine",
        severity="MODERATE",
        mechanism="Iron chelates Levothyroxine in the gut",
        effect="Reduced Levothyroxine absorption.",
        management="Separate administration by at least 4 hours.",
    ),
    DrugInteraction(
        drug_a="Antacids", drug_b="Levothyroxine",
        severity="MODERATE",
        mechanism="Calcium/magnesium antacids bind Levothyroxine",
        effect="Reduced absorption.",
        management="Take Levothyroxine on empty stomach 30–60 min before antacids.",
    ),

    # ── Salbutamol interactions ───────────────────────────
    DrugInteraction(
        drug_a="Beta-Blockers", drug_b="Salbutamol",
        severity="CONTRAINDICATED",
        mechanism="Beta-blockers block the beta-2 receptors that Salbutamol activates",
        effect="Bronchospasm, loss of bronchodilator effect — potentially life-threatening in asthma.",
        management="Avoid non-selective beta-blockers in asthma. Use cardioselective beta-blocker (e.g., bisoprolol) only if essential.",
    ),
    DrugInteraction(
        drug_a="Digoxin", drug_b="Salbutamol",
        severity="MODERATE",
        mechanism="Salbutamol-induced hypokalaemia increases Digoxin sensitivity",
        effect="Risk of Digoxin toxicity and arrhythmia.",
        management="Monitor serum potassium and Digoxin levels during concurrent use.",
    ),

    # ── Cetirizine interactions ───────────────────────────
    DrugInteraction(
        drug_a="Alcohol", drug_b="Cetirizine",
        severity="MODERATE",
        mechanism="Additive CNS depression",
        effect="Excessive drowsiness, impaired cognitive function and reaction time.",
        management="Advise patients to avoid alcohol while taking Cetirizine.",
    ),

    # ── Amoxicillin interactions ──────────────────────────
    DrugInteraction(
        drug_a="Amoxicillin", drug_b="Warfarin",
        severity="MODERATE",
        mechanism="Antibiotic reduces gut bacteria producing Vitamin K",
        effect="Increased INR → bleeding risk.",
        management="Monitor INR during and 1 week after antibiotic course.",
    ),
    DrugInteraction(
        drug_a="Amoxicillin", drug_b="Oral Contraceptives",
        severity="MINOR",
        mechanism="May reduce enterohepatic recirculation of oestrogen (evidence debated)",
        effect="Possible reduced efficacy of oral contraceptives.",
        management="Use additional contraceptive barrier methods during antibiotic course.",
    ),

    # ── Ibuprofen interactions ────────────────────────────
    DrugInteraction(
        drug_a="Ibuprofen", drug_b="Lithium",
        severity="MAJOR",
        mechanism="NSAIDs reduce renal prostaglandin synthesis, decreasing Lithium clearance",
        effect="Lithium toxicity: tremor, confusion, cardiac effects.",
        management="Monitor Lithium serum levels closely. Consider paracetamol for pain instead.",
    ),
    DrugInteraction(
        drug_a="ACE Inhibitors", drug_b="Ibuprofen",
        severity="MAJOR",
        mechanism="NSAIDs blunt the renal vasodilatory effect of prostaglandins that ACE inhibitors depend on",
        effect="Reduced antihypertensive effect; acute kidney injury risk.",
        management="Avoid NSAIDs in patients on ACE inhibitors. Use Paracetamol for analgesia.",
    ),

    # ── Montelukast interactions ──────────────────────────
    DrugInteraction(
        drug_a="Montelukast", drug_b="Rifampicin",
        severity="MODERATE",
        mechanism="Rifampicin is a potent CYP3A4 inducer, increasing Montelukast metabolism",
        effect="Reduced Montelukast efficacy.",
        management="Consider increasing Montelukast dose or switching asthma prophylaxis.",
    ),
]


# ── Engine class ─────────────────────────────────────────────────────────────

class DrugInteractionEngine:
    """
    Checks a list of medicine names against the interaction database
    and returns all relevant interactions sorted by severity.
    """

    def __init__(self):
        self._index: Dict[str, List[DrugInteraction]] = {}
        self._build_index()

    def _build_index(self):
        """Build a lowercase name → interactions lookup index"""
        for ia in INTERACTIONS:
            for key in (ia.drug_a.lower(), ia.drug_b.lower()):
                self._index.setdefault(key, []).append(ia)

    # ── aliases for common brand names ───────────────────
    BRAND_TO_GENERIC = {
        "crocin": "paracetamol", "dolo": "paracetamol", "calpol": "paracetamol",
        "tylenol": "paracetamol", "brufen": "ibuprofen", "advil": "ibuprofen",
        "nurofen": "ibuprofen", "lipitor": "atorvastatin", "storvas": "atorvastatin",
        "omez": "omeprazole", "ocid": "omeprazole", "prilosec": "omeprazole",
        "zyrtec": "cetirizine", "alerid": "cetirizine",
        "zithromax": "azithromycin", "azithral": "azithromycin",
        "norvasc": "amlodipine", "amlip": "amlodipine",
        "synthroid": "levothyroxine", "thyronorm": "levothyroxine", "eltroxin": "levothyroxine",
        "ventolin": "salbutamol", "asthalin": "salbutamol",
        "cipro": "ciprofloxacin", "ciplox": "ciprofloxacin",
        "singulair": "montelukast", "montair": "montelukast",
        "amoxil": "amoxicillin",
        "glucophage": "metformin", "glycomet": "metformin",
        "ecosprin": "aspirin", "loprin": "aspirin",
        "pantop": "pantoprazole",
    }

    def _resolve_name(self, name: str) -> str:
        """Resolve brand name to generic"""
        name_lower = name.strip().lower()
        return self.BRAND_TO_GENERIC.get(name_lower, name_lower)

    def check(self, medicines: List[str]) -> dict:
        """
        Check a list of medicines for interactions.

        Args:
            medicines: list of medicine name strings

        Returns:
            dict with interactions list, severity summary, and safe pairs
        """
        resolved    = [self._resolve_name(m) for m in medicines]
        found       = []
        checked_pairs: set = set()

        for i, med_a in enumerate(resolved):
            interactions_a = self._index.get(med_a, [])
            for ia in interactions_a:
                other = ia.drug_b.lower() if ia.drug_a.lower() == med_a else ia.drug_a.lower()
                if other in resolved:
                    pair_key = tuple(sorted([med_a, other]))
                    if pair_key not in checked_pairs:
                        checked_pairs.add(pair_key)
                        found.append(ia.to_dict())

        # Sort by severity (highest first)
        severity_order = {"CONTRAINDICATED": 4, "MAJOR": 3, "MODERATE": 2, "MINOR": 1}
        found.sort(key=lambda x: severity_order.get(x["severity"], 0), reverse=True)

        # Summary counts
        counts = {"CONTRAINDICATED": 0, "MAJOR": 0, "MODERATE": 0, "MINOR": 0}
        for f in found:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1

        highest = max(counts, key=lambda k: counts[k] * severity_order[k]) if found else None

        return {
            "medicines_checked": medicines,
            "interactions_found": len(found),
            "interactions": found,
            "severity_counts": counts,
            "highest_severity": highest,
            "is_safe": len(found) == 0,
            "recommendation": self._overall_recommendation(highest, len(found))
        }

    def check_pair(self, drug_a: str, drug_b: str) -> Optional[dict]:
        """Check a single drug pair"""
        result = self.check([drug_a, drug_b])
        return result["interactions"][0] if result["interactions"] else None

    def _overall_recommendation(self, highest: Optional[str], count: int) -> str:
        if count == 0:
            return "No known interactions found between these medicines. Always consult your doctor."
        if highest == "CONTRAINDICATED":
            return "⛔ CONTRAINDICATED combination detected. Do NOT take these medicines together. Consult your doctor immediately."
        if highest == "MAJOR":
            return "⚠️ Major interaction(s) detected. Consult your doctor or pharmacist before taking these medicines together."
        if highest == "MODERATE":
            return "⚠️ Moderate interaction(s) detected. Take these medicines under medical supervision."
        return "ℹ️ Minor interaction(s) noted. Generally safe but inform your doctor."

    def all_interactions_for(self, medicine: str) -> List[dict]:
        """Return all known interactions for a single medicine"""
        name = self._resolve_name(medicine)
        return [ia.to_dict() for ia in self._index.get(name, [])]

    def interaction_count(self) -> int:
        return len(INTERACTIONS)


# ── Singleton ─────────────────────────────────────────────────────────────────
_engine: Optional[DrugInteractionEngine] = None

def get_interaction_engine() -> DrugInteractionEngine:
    global _engine
    if _engine is None:
        _engine = DrugInteractionEngine()
    return _engine


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = get_interaction_engine()
    print(f"Interaction DB: {engine.interaction_count()} entries\n")

    combos = [
        ["Aspirin", "Ibuprofen"],
        ["Paracetamol", "Cetirizine"],
        ["Atorvastatin", "Warfarin", "Aspirin"],
        ["Azithromycin", "Ciprofloxacin"],
        ["Metformin", "Alcohol"],
    ]
    for combo in combos:
        result = engine.check(combo)
        print(f"Medicines: {combo}")
        print(f"  Safe: {result['is_safe']} | Interactions: {result['interactions_found']} | Highest: {result['highest_severity']}")
        print(f"  → {result['recommendation']}\n")
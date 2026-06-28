"""Static reference data used to generate a believable demo dataset."""

from __future__ import annotations

from app.models.enums import FailureCode

FIRST_NAMES = [
    "Olivia", "Liam", "Amara", "Noah", "Sofia", "Ethan", "Priya", "Lucas",
    "Mia", "Kai", "Zoe", "Mateo", "Aisha", "Daniel", "Lena", "Omar",
    "Hana", "Marcus", "Nadia", "Theo", "Ines", "Yusuf", "Clara", "Diego",
    "Maya", "Sven", "Fatima", "Jonas", "Ada", "Tomas", "Leah", "Ravi",
    "Greta", "Hugo", "Anaya", "Elias", "Nora", "Felix", "Sara", "Idris",
    "Camila", "Bjorn", "Tara", "Andre", "Wren", "Cyrus", "Esme", "Niko",
]

LAST_NAMES = [
    "Okafor", "Nguyen", "Patel", "Andersson", "Costa", "Rossi", "Kovac",
    "Mbeki", "Schneider", "Haddad", "Larsson", "Dubois", "Khan", "Silva",
    "Novak", "Adeyemi", "Fischer", "Moreau", "Ferreira", "Yamamoto",
    "Bauer", "Mensah", "Petrov", "Romano", "Lindqvist", "Bianchi", "Eze",
    "Halloran", "Marchetti", "Sorensen", "Ibrahim", "Voss", "Kaur",
    "Delgado", "Janssen", "Okonkwo", "Reyes", "Travers", "Bergstrom",
]

COMPANY_PREFIX = [
    "North", "Bright", "Clear", "Iron", "Cedar", "Atlas", "Vega", "Lumen",
    "Quill", "Harbor", "Slate", "Coral", "Vertex", "Onyx", "Aster", "Nimbus",
    "Forge", "Ridge", "Tidal", "Kestrel", "Halcyon", "Maple", "Granite",
]
COMPANY_SUFFIX = [
    "Labs", "Systems", "Studio", "Works", "Logistics", "Health", "Capital",
    "Robotics", "Analytics", "Foods", "Media", "Freight", "Bio", "Cloud",
    "Devices", "Interactive", "Partners", "Retail", "Energy", "Security",
]

# (plan name, monthly amount in minor units, segment, relative weight)
PLANS = [
    ("Starter (monthly)", 2900, "starter", 30),
    ("Starter (annual)", 29000, "starter", 8),
    ("Growth (monthly)", 9900, "growth", 26),
    ("Growth (annual)", 99000, "growth", 9),
    ("Scale (monthly)", 24900, "growth", 12),
    ("Business (monthly)", 49900, "enterprise", 8),
    ("Enterprise (annual)", 1200000, "enterprise", 4),
    ("Enterprise+ (annual)", 3600000, "enterprise", 2),
]

COUNTRIES = ["US", "US", "US", "GB", "GB", "DE", "FR", "NL", "SE", "ZA", "CA", "AU", "IE"]

# Realistic processor decline strings for each normalised failure code.
DECLINE_MESSAGES: dict[FailureCode, str] = {
    FailureCode.INSUFFICIENT_FUNDS: "Your card has insufficient funds. (insufficient_funds)",
    FailureCode.EXPIRED_CARD: "Your card has expired. (expired_card)",
    FailureCode.DO_NOT_HONOR: "Your card was declined by the issuer. (do_not_honor)",
    FailureCode.CARD_DECLINED: "Your card was declined. (generic_decline)",
    FailureCode.LOST_OR_STOLEN: "Your card was reported lost or stolen. (lost_card)",
    FailureCode.AUTHENTICATION_REQUIRED: "This payment requires authentication. (authentication_required)",
    FailureCode.PROCESSING_ERROR: "An error occurred processing your card. (processing_error)",
    FailureCode.FRAUD_SUSPECTED: "Your card was declined due to suspected fraud. (fraudulent)",
}

# How failures are distributed across the population (relative weights). Soft
# declines dominate real billing — that's where automated recovery shines.
FAILURE_WEIGHTS: list[tuple[FailureCode, int]] = [
    (FailureCode.INSUFFICIENT_FUNDS, 34),
    (FailureCode.EXPIRED_CARD, 18),
    (FailureCode.DO_NOT_HONOR, 14),
    (FailureCode.CARD_DECLINED, 11),
    (FailureCode.AUTHENTICATION_REQUIRED, 9),
    (FailureCode.PROCESSING_ERROR, 7),
    (FailureCode.LOST_OR_STOLEN, 4),
    (FailureCode.FRAUD_SUSPECTED, 3),
]

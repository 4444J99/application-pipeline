"""Constants for source_jobs.py."""

TITLE_KEYWORDS = [
    "software engineer", "developer", "engineering",
    "developer advocate", "developer relations", "devrel",
    "developer experience", "developer tools", "cli",
    "technical writer", "documentation engineer",
    "solutions engineer", "forward deployed",
    "infrastructure", "platform engineer",
    "agentic", "ai engineer", "ml engineer",
    "full stack", "backend", "frontend",
]

TITLE_EXCLUDES = [
    "senior staff", "staff engineer", "principal",
    "director", "vp", "head of", "manager",
    "intern", "co-op",
    "hardware", "mechanical", "electrical",
    "finance", "accounting", "legal", "counsel",
    "recruiter", "people ops", "hr ",
]

HTTP_TIMEOUT = 15

VALID_LOCATION_CLASSES = {"us-onsite", "us-remote", "remote-global", "international", "unknown"}

US_STATES = [
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
    "dc",
]

US_CITIES = [
    "san francisco", "new york", "seattle", "austin", "chicago",
    "los angeles", "boston", "denver", "portland", "miami",
    "atlanta", "dallas", "houston", "phoenix", "philadelphia",
    "san jose", "san diego", "nashville", "raleigh", "pittsburgh",
    "minneapolis", "salt lake city", "boulder", "palo alto",
    "mountain view", "menlo park", "sunnyvale", "cupertino",
    "redmond", "bellevue", "brooklyn", "manhattan",
    "sf", "nyc",
]

INTERNATIONAL_MARKERS = [
    "london", "uk", "united kingdom", "dublin", "ireland",
    "tokyo", "japan", "singapore", "korea", "seoul",
    "hyderabad", "india", "bangalore", "bengaluru", "mumbai",
    "hungary", "budapest", "netherlands", "amsterdam",
    "germany", "berlin", "munich", "france", "paris",
    "canada", "toronto", "vancouver", "montreal",
    "australia", "sydney", "melbourne",
    "brazil", "são paulo",
    "switzerland", "zürich", "zurich",
    "israel", "tel aviv",
    "poland", "warsaw",
    "spain", "madrid", "barcelona",
    "italy", "milan", "rome",
    "sweden", "stockholm",
    "emea", "apac",
]

US_KEYWORDS = [
    "united states", "usa", " us ", "u.s.", "us-", "- us",
    "remote - us", "remote-us", "remote us", "us remote",
]

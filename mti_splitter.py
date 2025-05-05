# mti_splitter.py
import re

# Define explicit MTI list (expand as needed)
VALID_MTIS = ["1240", "1442", "1644", "1804", "1420", "1422", "1424", "1426", "1428", "1430"]

# Create a pattern to match any of the valid MTIs
MTI_PATTERN = re.compile(rf"({'|'.join(VALID_MTIS)})")

def extract_records_from_raw_text(content: str, max_record_len=2000):
    matches = list(MTI_PATTERN.finditer(content))
    if not matches:
        return []

    records = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        record = content[start:end].strip()

        # Filter out too-short records (likely noise)
        if len(record) >= 60:
            records.append(record)

    return records

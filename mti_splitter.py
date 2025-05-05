# mti_splitter.py
import re

# Mastercard MTIs typically begin with '1240', '1442', '1644' etc.
# PAN starts with 5 or 4, and is usually 16 digits

MTI_PATTERN = re.compile(r"(?=(12[4-9]0|14[4-9]2|16[4-9]4))")
PAN_PATTERN = re.compile(r"\b[45]\d{11,18}\b")


def extract_records_from_raw_text(content: str, max_record_len=2000):
    # Split based on MTI locations
    indexes = [m.start(1) for m in MTI_PATTERN.finditer(content)]
    if not indexes:
        return []

    indexes.append(len(content))  # Sentinel to capture last segment
    records = []
    for i in range(len(indexes) - 1):
        start, end = indexes[i], indexes[i + 1]
        record = content[start:end].strip()

        if PAN_PATTERN.search(record):  # Confirm valid PAN exists
            records.append(record)

    return records

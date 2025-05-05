import streamlit as st
import csv
import io

# Adjust this to your actual record length (in bytes/chars)
RECORD_LENGTH = 256  # <-- Change this to match your file!

# Define the fields and their positions/lengths (example, adjust as needed)
FIELDS = [
    ("MTI", 0, 4),
    ("PAN", 4, 19),
    ("Processing Code", 23, 6),
    ("Amount Transaction", 29, 12),
    ("Amount Reconciliation", 41, 12),
    ("Conversion Rate Reconciliation", 53, 8),
    ("Local Transaction Date/Time", 61, 10),
    ("Date Expiration", 71, 4),
    ("POS Data Code", 75, 3),
    ("Card Sequence Number", 78, 3),
    ("Function Code", 81, 3),
    ("Message Reason Code", 84, 4),
    ("Card Acceptor Business Code", 88, 4),
    ("Amounts Original", 92, 12),
    ("Acquirer Reference Data", 104, 12),
    ("Acquiring Institution ID Code", 116, 11),
    ("Forwarding Institution ID Code", 127, 11),
    ("Retrieval Reference Number", 138, 12),
    ("Approval Code", 150, 6),
    ("Service Code", 156, 3),
    ("Card Acceptor Terminal ID", 159, 8),
    ("Card Acceptor ID Code", 167, 15),
    ("Card Acceptor Name/Location", 182, 40),
    ("Additional Data", 222, 34),  # Example: adjust length as needed
    # Add more fields as needed...
]

def parse_record(record):
    parsed = {}
    for name, start, length in FIELDS:
        parsed[name] = record[start:start+length].strip()
    return parsed

st.title("Mastercard T112/T113 File Parser")

uploaded_file = st.file_uploader("Choose a Mastercard file (.001, .002, .dat, .txt)", type=["001", "002", "dat", "txt"])

if uploaded_file is not None:
    data = uploaded_file.read()
    records = [data[i:i+RECORD_LENGTH] for i in range(0, len(data), RECORD_LENGTH)]
    records = [rec.decode('ascii', errors='ignore') for rec in records if len(rec) == RECORD_LENGTH]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[name for name, _, _ in FIELDS])
    writer.writeheader()
    for rec in records:
        parsed = parse_record(rec)
        writer.writerow(parsed)

    st.success(f"Parsed {len(records)} records.")
    st.download_button("Download CSV", output.getvalue(), file_name="parsed_t112.csv", mime="text/csv")

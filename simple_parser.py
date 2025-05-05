import streamlit as st
import pandas as pd
import json
import os
from mti_splitter import extract_records_from_raw_text

# -------------------------------------
# 1. Load MTI rules from JSON
# -------------------------------------
def load_mti_rules(path="mti_rules.json"):
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception as e:
        st.warning(f"Failed to load MTI rules: {e}")
        return {}

mti_rules = load_mti_rules()

# -------------------------------------
# 2. Load ISO spec for each MTI
# -------------------------------------
def load_spec_for_mti(mti: str, specs_dir="specs"):
    spec_file = os.path.join(specs_dir, f"{mti}.json")
    default_file = os.path.join(specs_dir, "default.json")
    try:
        with open(spec_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(default_file, "r") as f:
            return json.load(f)

# -------------------------------------
# 3. ISO Validator (field-level checks)
# -------------------------------------
def validate_iso_fields(parsed: dict, spec: dict) -> list:
    errors = []
    for key, value in parsed.items():
        if key.startswith("Field "):
            field_num = key.split(" ")[1]
            field_spec = spec.get(field_num, {})
            expected_len = field_spec.get("max_len")
            expected_type = field_spec.get("type")

            if expected_len and len(value) != expected_len:
                errors.append(f"{key}: length {len(value)} vs {expected_len}")

            if expected_type == "numeric" and not value.isdigit():
                errors.append(f"{key}: expected numeric")

    return errors

# -------------------------------------
# 4. Parse one ISO record
# -------------------------------------
def parse_mastercard_iso8583(record: str) -> dict:
    parsed = {}
    cursor = 0
    mti = record[:4]
    parsed["MTI"] = mti
    parsed["MTI Meaning"] = mti_rules.get(mti, "❓ Unknown MTI")

    spec = load_spec_for_mti(mti)

    for field_id, field_spec in spec.items():
        length = field_spec["max_len"]
        value = record[cursor:cursor + length]
        parsed[f"Field {field_id}"] = value.strip()
        cursor += length

    errors = validate_iso_fields(parsed, spec)
    parsed["Validation Errors"] = "; ".join(errors)
    parsed["Status"] = "✅ Pass" if not errors else "❌ Fail"

    return parsed

# -------------------------------------
# 5. Streamlit App UI
# -------------------------------------
st.title("Mastercard ISO 8583 Parser with MTI-Aware Specs")

uploaded_file = st.file_uploader("📂 Upload Mastercard TT112/TT140 File", type=None)

if uploaded_file:
    content = uploaded_file.read().decode("utf-8", errors="replace")
    records = extract_records_from_raw_text(content)

    st.subheader("📄 Raw Record Preview")
    for i, rec in enumerate(records[:2]):
        st.code(rec)

    if st.button("🚀 Parse File"):
        parsed_data = [parse_mastercard_iso8583(rec) for rec in records]
        df = pd.DataFrame(parsed_data)

        mti_list = df["MTI Meaning"].dropna().unique().tolist()
        selected_mti = st.selectbox("📌 Filter by MTI Meaning", options=["All"] + mti_list)
        only_failures = st.checkbox("🔎 Show only records with validation errors")

        df_filtered = df.copy()
        if selected_mti != "All":
            df_filtered = df_filtered[df_filtered["MTI Meaning"] == selected_mti]
        if only_failures:
            df_filtered = df_filtered[df_filtered["Status"] == "❌ Fail"]

        st.subheader("📊 Parsed + Validated Records")
        st.dataframe(df_filtered)

        st.download_button(
            label="⬇️ Download CSV",
            data=df_filtered.to_csv(index=False).encode("utf-8"),
            file_name="parsed_validated_mastercard.csv",
            mime="text/csv"
        )
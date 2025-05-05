import streamlit as st
import csv
import io
import pandas as pd
from cardutil.mciipm import IpmReader

# Record length for T112
T112_RECORD_LENGTH = 256

# MTI Code definitions
MASTERCARD_MTI_CODES = {
    "1240": "Authorization Request",
    "1250": "Authorization Response",
    "1420": "Clearing Advice",
    "1430": "Clearing Advice Response",
    "1440": "Clearing Notification"
}

def analyze_mti(mti):
    if len(mti) != 4:
        return {
            "MTI": mti,
            "Description": "Invalid MTI"
        }
    return {
        "MTI": mti,
        "Description": MASTERCARD_MTI_CODES.get(mti, "Unknown Transaction Type")
    }

def parse_t112_record(record):
    fields = [
        ("MTI", 0, 4),
        ("PAN", 4, 19),
        ("Processing Code", 23, 6),
        ("Amount", 29, 12),
        ("Local Date/Time", 61, 10),
        ("Card Expiry", 71, 4),
        ("MCC", 88, 4),
        ("Terminal ID", 159, 8),
        ("Merchant ID", 167, 15),
        ("Merchant Name", 182, 40)
    ]
    
    parsed = {}
    for name, start, length in fields:
        value = record[start:start+length].strip()
        if name == "PAN":
            value = ''.join(c for c in value if c.isalnum())
        elif name == "Amount":
            value = str(int(value or '0'))
        parsed[name] = value
    return parsed

def process_t112_file(data):
    records = [data[i:i+T112_RECORD_LENGTH] for i in range(0, len(data), T112_RECORD_LENGTH)]
    records = [rec.decode('ascii', errors='ignore') for rec in records if len(rec) == T112_RECORD_LENGTH]
    
    parsed_records = []
    for rec in records:
        parsed = parse_t112_record(rec)
        if "MTI" in parsed:
            mti_info = analyze_mti(parsed["MTI"])
            parsed["Transaction Type"] = mti_info["Description"]
        parsed_records.append(parsed)
    
    df = pd.DataFrame(parsed_records)
    csv_data = df.to_csv(index=False)
    return csv_data, len(records), df

def process_t113_file(data):
    file_like = io.BytesIO(data)
    parsed_rows = []
    
    try:
        reader = IpmReader(file_like, blocked=True)
        for record in reader:
            if isinstance(record, dict):
                if "MTI" in record:
                    mti_info = analyze_mti(record["MTI"])
                    record["Transaction Type"] = mti_info["Description"]
                parsed_rows.append(record)
    except Exception:
        file_like.seek(0)
        try:
            reader = IpmReader(file_like, blocked=False)
            for record in reader:
                if isinstance(record, dict):
                    if "MTI" in record:
                        mti_info = analyze_mti(record["MTI"])
                        record["Transaction Type"] = mti_info["Description"]
                    parsed_rows.append(record)
        except Exception as e:
            st.error(f"Error parsing T113 file: {e}")
            return "", 0, pd.DataFrame()
    
    if parsed_rows:
        df = pd.DataFrame(parsed_rows)
        csv_data = df.to_csv(index=False)
        return csv_data, len(parsed_rows), df
    return "", 0, pd.DataFrame()

def main():
    st.title("Mastercard Parser")

    col1, col2 = st.columns([1, 2])
    with col1:
        file_type = st.radio("Type", ["T112", "T113"])
    with col2:
        uploaded_file = st.file_uploader("File", type=["001", "002", "dat", "txt"])

    if uploaded_file is not None:
        try:
            data = uploaded_file.read()
            if file_type == "T112":
                csv_data, record_count, df = process_t112_file(data)
            else:
                csv_data, record_count, df = process_t113_file(data)
            
            if record_count > 0:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.download_button(
                        "Download CSV",
                        csv_data,
                        file_name=f"parsed_{file_type.lower()}.csv",
                        mime="text/csv"
                    )
                with col2:
                    st.success(f"{record_count} records")
                
                st.dataframe(df)
                
                if "MTI" in df.columns:
                    with st.expander("Transaction Types"):
                        mti_counts = df["MTI"].value_counts()
                        for mti in mti_counts.index:
                            st.write(f"{mti}: {MASTERCARD_MTI_CODES.get(mti, 'Unknown')} ({mti_counts[mti]} records)")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 
import streamlit as st
import csv
import io
import pandas as pd
import re

def clean_record(record):
    """Clean the record by removing null bytes and special characters."""
    # Remove null bytes and other control characters
    cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', record)
    # Remove @ symbols
    cleaned = cleaned.replace('@', '')
    return cleaned

def parse_tt112_record(record):
    """Parse a single TT112 record and return a dictionary of fields."""
    try:
        # Clean the record first
        record = clean_record(record)
        
        # Extract basic record information
        record_type = record[0:4]  # First 4 characters
        
        # Find the record length - it's after the record type
        length_match = re.search(r'\d{4}', record[4:8])
        if not length_match:
            return {"Error": "Invalid record length", "Raw Record": record}
        record_length = int(length_match.group())
        
        # Parse the record based on its type
        if record_type == "1644":
            # Extract transaction data
            # Find all M-prefixed transaction records
            transactions = re.findall(r'M\d{6}\d{10}\d{12}', record)
            
            if transactions:
                # Process each transaction
                parsed_transactions = []
                for trans in transactions:
                    trans_date = trans[1:7]  # YYMMDD
                    trans_time = trans[7:13]  # HHMMSS
                    amount = trans[13:25]  # Amount
                    
                    parsed_transactions.append({
                        "Record Type": record_type,
                        "Record Length": record_length,
                        "Transaction Date": trans_date,
                        "Transaction Time": trans_time,
                        "Amount": amount,
                        "Raw Transaction": trans
                    })
                return parsed_transactions
            else:
                # If no transactions found, return basic record info
                return {
                    "Record Type": record_type,
                    "Record Length": record_length,
                    "Raw Data": record[8:].strip()
                }
        else:
            # Other record types (header, trailer, etc.)
            return {
                "Record Type": record_type,
                "Record Length": record_length,
                "Raw Data": record[8:].strip()
            }
    except Exception as e:
        return {"Error": f"Failed to parse record: {str(e)}", "Raw Record": record}

def main():
    st.title("Mastercard TT112 Parser")
    st.markdown(
        """
        **Upload** one or more `.001` TT112 dump files.  
        The app will parse each record according to the Mastercard TT112 format,
        display the results in a table, and allow you to download a CSV.
        """
    )

    uploaded_files = st.file_uploader(
        "Select TT112 `.001` files from your system:", 
        type=["001"], 
        accept_multiple_files=True
    )

    if not uploaded_files:
        return

    for uploaded in uploaded_files:
        raw = uploaded.read()
        # Split on record boundaries (1644)
        records = re.split(b'(?=1644)', raw)
        parsed_rows = []

        for rec in records:
            if not rec:
                continue
            try:
                # Convert bytes to string, handling encoding
                record_str = rec.decode('latin-1', errors='ignore')
                parsed_record = parse_tt112_record(record_str)
                
                # Handle both single records and lists of transactions
                if isinstance(parsed_record, list):
                    parsed_rows.extend(parsed_record)
                else:
                    parsed_rows.append(parsed_record)
                    
            except Exception as e:
                st.warning(f"Record parse error in {uploaded.name}: {e}")
                continue

        if parsed_rows:
            # Convert to DataFrame
            df = pd.DataFrame(parsed_rows)
            
            st.subheader(f"Parsed Output: {uploaded.name}")
            st.dataframe(df)

            # CSV download
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode("utf-8")

            st.download_button(
                label=f"Download CSV for {uploaded.name}",
                data=csv_bytes,
                file_name=f"{uploaded.name}.csv",
                mime="text/csv",
                key=f"download_{uploaded.name}"  # Unique key for each button
            )

if __name__ == "__main__":
    main() 
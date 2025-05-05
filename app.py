import streamlit as st
import pandas as pd
import base64
import chardet
import struct
from io import BytesIO
import os

# Configure page
st.set_page_config(page_title="T112 Processor", layout="wide")
st.title("ISO 8583 T112 File Processor")
st.markdown("""
Process T112 files with robust error handling and automatic format detection.
""")

## ----------------------------
## ISO 8583 Configuration
## ----------------------------

ISO_FIELD_DEFS = {
    2: ('Primary Account Number', 19, 'n', None),
    3: ('Processing Code', 6, 'n', None),
    4: ('Amount Transaction', 12, 'n', lambda x: float(x)/100 if x.strip() else None),
    7: ('Transmission Date/Time', 10, 'n', 
        lambda x: f"{x[0:2]}-{x[2:4]}-{x[4:6]} {x[6:8]}:{x[8:10]}" if x else None),
    11: ('System Trace Audit Number', 6, 'n', None),
    12: ('Local Transaction Time', 6, 'n', 
        lambda x: f"{x[0:2]}:{x[2:4]}:{x[4:6]}" if x else None),
    22: ('POS Data Code', 12, 'ans', None),
    24: ('Function Code', 3, 'n', None),
    32: ('Acquiring Institution ID', 11, 'n', None),
    37: ('Retrieval Reference Number', 12, 'ans', None),
    38: ('Approval Code', 6, 'ans', None),
    41: ('Card Acceptor Terminal ID', 16, 'ans', None),
    43: ('Card Acceptor Name/Location', 99, 'ans', None),
    49: ('Currency Code', 3, 'n', None)
}

## ----------------------------
## Enhanced Parser Implementations
## ----------------------------

def safe_decode(data, encoding='ascii'):
    """Safely decode binary data with error handling"""
    try:
        return data.decode(encoding).strip('\x00').strip()
    except:
        return data.hex()

def parse_binary_amount(data):
    """Handle different amount formats in binary data"""
    try:
        # Try ASCII numeric first
        decoded = safe_decode(data)
        if decoded:
            return float(decoded)/100
    except:
        pass
    
    try:
        # Fallback to binary packed format
        if len(data) >= 6:
            return struct.unpack('>q', b'\x00\x00' + data[-6:])[0]/100
    except:
        pass
    
    return None

def parse_iso8583_binary(content):
    """Robust binary parser with error handling"""
    transactions = []
    pos = 0
    content_length = len(content)
    
    while pos + 4 <= content_length:  # Minimum MTI length
        try:
            # Parse MTI
            mti = safe_decode(content[pos:pos+4])
            pos += 4
            
            # Skip if we don't have enough data for bitmap
            if pos + 8 > content_length:
                break
                
            # Parse primary bitmap
            bitmap_int = int.from_bytes(content[pos:pos+8], 'big')
            bitmap = bin(bitmap_int)[2:].zfill(64)
            pos += 8
            
            fields = {'mti': mti, 'record_format': 'binary'}
            field_pos = 1  # ISO fields start at 1
            
            for bit in bitmap:
                if bit == '1' and field_pos in ISO_FIELD_DEFS:
                    name, length, field_type, convert = ISO_FIELD_DEFS[field_pos]
                    
                    # Check if we have enough data remaining
                    if pos + length > content_length:
                        break
                        
                    field_data = content[pos:pos+length]
                    pos += length
                    
                    # Special handling for amount fields
                    if field_pos == 4:
                        fields[name] = parse_binary_amount(field_data)
                    else:
                        try:
                            decoded = safe_decode(field_data)
                            fields[name] = convert(decoded) if convert else decoded
                        except Exception as e:
                            fields[name] = field_data.hex()
                            st.warning(f"Field {field_pos} decoding error: {str(e)}")
                
                field_pos += 1
            
            transactions.append(fields)
            
        except Exception as e:
            st.warning(f"Skipping malformed record at position {pos}: {str(e)}")
            # Attempt to recover by finding next MTI pattern
            next_mti = content.find(b'\x02', pos+1)  # Look for STX character
            if next_mti == -1:
                break
            pos = next_mti - 4 if next_mti >= 4 else next_mti
    
    return transactions

def parse_iso8583_text(content):
    """Parse text-based ISO 8583 with encoding detection"""
    try:
        encoding = detect_encoding(content)
        content_str = content.decode(encoding)
        transactions = []
        
        for line in content_str.split('\n'):
            if not line.strip():
                continue
                
            # Handle different text formats
            if '|' in line:  # Pipe-delimited
                parts = line.strip().split('|')
                mti = parts[0] if parts else None
                fields = {'mti': mti, 'record_format': 'text'}
                
                for part in parts[1:]:
                    if ':' in part:
                        field_num, value = part.split(':', 1)
                        try:
                            field_num = int(field_num)
                            if field_num in ISO_FIELD_DEFS:
                                name, _, _, convert = ISO_FIELD_DEFS[field_num]
                                fields[name] = convert(value) if convert else value
                        except:
                            continue
                
                transactions.append(fields)
            else:  # Fixed-width
                # Implement your fixed-width format parsing here
                pass
                
        return transactions
    except Exception as e:
        st.error(f"Text parsing error: {str(e)}")
        return []

## ----------------------------
## File Processing Core
## ----------------------------

def detect_encoding(content):
    """Detect file encoding with robust fallback"""
    try:
        result = chardet.detect(content)
        return result['encoding'] if result['confidence'] > 0.7 else 'latin-1'
    except:
        return 'latin-1'

def process_t112_file(content, filename):
    """Process file with format detection and error handling"""
    try:
        # Check for binary indicators
        is_binary = (
            filename.lower().endswith('.001') or
            content.startswith((b'\x01', b'\x02')) or
            b'\x00' in content[:1000]  # Null bytes in first 1000 bytes
        )
        
        if is_binary:
            return parse_iso8583_binary(content)
        else:
            return parse_iso8583_text(content)
    except Exception as e:
        st.error(f"File processing error: {str(e)}")
        return []

## ----------------------------
## Streamlit UI Implementation
## ----------------------------

def main():
    uploaded_files = st.file_uploader(
        "Upload T112 Files",
        type=["txt", "dat", "log", "t112", "001"],
        accept_multiple_files=True
    )

    if uploaded_files:
        all_transactions = []
        
        with st.spinner("Processing files..."):
            for uploaded_file in uploaded_files:
                try:
                    content = uploaded_file.getvalue()
                    filename = uploaded_file.name
                    
                    transactions = process_t112_file(content, filename)
                    for txn in transactions:
                        txn['source_file'] = filename
                        all_transactions.append(txn)
                        
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

        if all_transactions:
            df = pd.DataFrame(all_transactions)
            
            # Display results
            st.success(f"Processed {len(df)} transactions from {len(uploaded_files)} files")
            
            # Show preview with PAN masking
            st.subheader("Processed Data Preview")
            df_display = df.copy()
            if 'Primary Account Number' in df_display:
                df_display['Primary Account Number'] = df_display['Primary Account Number'].apply(
                    lambda x: f"{x[:6]}******{x[-4:]}" if isinstance(x, str) and len(x) >= 10 else x
                )
            st.dataframe(df_display.head())
            
            # Show statistics
            st.subheader("Transaction Statistics")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**By Format Type**")
                st.bar_chart(df['record_format'].value_counts())
            
            with col2:
                if 'Amount Transaction' in df:
                    st.write("**Amount Distribution**")
                    st.bar_chart(df['Amount Transaction'].value_counts(bins=5))
            
            # Download button
            st.subheader("Download Processed Data")
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="t112_processed.csv",
                mime="text/csv"
            )
        else:
            st.error("No valid transactions found. Check file formats.")

    # Documentation
    with st.expander("T112 File Format Help"):
        st.markdown("""
        **Supported Formats:**
        
        - **Binary .001 Files**:
          - Must contain valid ISO 8583 messages
          - Can have either ASCII or binary-packed amounts
          - Should start with MTI (4 bytes)
        
        - **Text Files**:
          - Pipe-delimited format: `MTI|FIELD1:VALUE|FIELD2:VALUE`
          - Fixed-width formats (configure parser)
        
        **Troubleshooting:**
        - Binary parsing errors usually indicate incorrect format
        - Try different files if you get decoding errors
        - Contact support if you need help with file formats
        """)

if __name__ == "__main__":
    main()
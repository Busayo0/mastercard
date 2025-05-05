import streamlit as st
import pandas as pd
import io
from cardutil.mciipm import IpmReader

def main():
    st.title("Mastercard T113/IPM Parser (Mapped with cardutil)")
    st.markdown(
        """
        **Upload** one or more T113/IPM files (any extension).  
        The app will use cardutil to map and parse each record, display the results in a table, and allow you to download a CSV.
        """
    )

    uploaded_files = st.file_uploader(
        "Select T113/IPM files from your system:", 
        accept_multiple_files=True
    )

    if not uploaded_files:
        return

    for uploaded in uploaded_files:
        raw = uploaded.read()
        # Use BytesIO to provide a file-like object for IpmReader
        file_like = io.BytesIO(raw)
        parsed_rows = []
        try:
            reader = IpmReader(file_like, blocked=True)
            for record in reader:
                parsed_rows.append(record)
        except Exception:
            file_like.seek(0)
            try:
                reader = IpmReader(file_like, blocked=False)
                for record in reader:
                    parsed_rows.append(record)
            except Exception as e:
                st.error(f"Error parsing {uploaded.name}: {e}")
                continue

        if parsed_rows:
            df = pd.DataFrame(parsed_rows)
            st.subheader(f"Parsed Output: {uploaded.name}")
            st.dataframe(df)

            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue().encode("utf-8")
            st.download_button(
                label=f"Download CSV for {uploaded.name}",
                data=csv_bytes,
                file_name=f"{uploaded.name}.csv",
                mime="text/csv",
                key=f"download_{uploaded.name}"
            )

if __name__ == "__main__":
    main() 
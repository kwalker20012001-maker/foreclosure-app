import streamlit as st
import pandas as pd
from io import BytesIO
from google import genai
from google.genai import types

# --- 1. SETUP & API CONFIG ---
st.set_page_config(page_title="Texas Auction Analyzer", layout="wide")
st.title("⚖️ Texas Foreclosure Auction Analyzer")

# Get API Key from Streamlit Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except:
    st.error("API Key not found. Please add GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()

# --- 2. THE BRAIN: EXTRACTION FUNCTION ---
def extract_data_from_pdf(pdf_file):
    pdf_bytes = pdf_file.read()
    
    prompt = """
    Analyze this Texas foreclosure legal instrument. 
    Extract the following details for EVERY property mentioned. 
    Format the output as a Python-readable list of dictionaries.
    Required Fields:
    - legal_description: (Lot, Block, Subdivision, Section)
    - street_address: (Physical address if present)
    - auction_date: (Date of sale)
    - auction_county: (Texas County)
    - min_bid: (The opening bid or debt amount, as a number)
    - fmv_estimate: (Estimate the fair market value in 120 days based on the location)
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            prompt
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return response.parsed

# --- 3. THE MATH: FORMULA ENGINE ---
def apply_formulas(df):
    # F: Fair Market Value (Already in DF from Gemini)
    # G: Renovation Budget (10%)
    df['Renovation Budget (G)'] = df['fmv_estimate'] * 0.10
    # H: Realtor Commissions (5%)
    df['Realtor Comm (H)'] = df['fmv_estimate'] * 0.05
    # I: Final Closing Costs (3.5%)
    df['Closing Costs (I)'] = df['fmv_estimate'] * 0.035
    # J: Initial MAO (70% of FMV)
    df['Initial MAO (J)'] = df['fmv_estimate'] * 0.70
    # K: Misc Costs
    df['Misc Costs (K)'] = 300
    # L: Holding Costs (1% of Initial MAO x 4 months)
    df['Holding Costs (L)'] = (df['Initial MAO (J)'] * 0.01) * 4
    # M: Final MAO
    df['Final MAO (M)'] = df['Initial MAO (J)'] - df['Misc Costs (K)'] - df['Holding Costs (L)']
    return df

# --- 4. THE INTERFACE ---
uploaded_file = st.file_uploader("Upload Foreclosure PDF(s)", type="pdf")

if uploaded_file:
    with st.spinner("Gemini is reading the legal instruments..."):
        try:
            raw_results = extract_data_from_pdf(uploaded_file)
            df = pd.DataFrame(raw_results)
            
            # Apply your formulas
            df = apply_formulas(df)
            
            st.success("Extraction Complete!")
            st.dataframe(df)
            
            # Excel Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button("📥 Download Excel", output.getvalue(), "Auction_List.xlsx")
            
        except Exception as e:
            st.error(f"Error during extraction: {e}")

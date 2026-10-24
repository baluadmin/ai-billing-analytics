import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from google import genai

st.set_page_config(page_title="AI Billing & Analytics Dashboard", layout="wide")

# Replace with your published Google Sheet CSV link for Transactions
SHEET_CSV_URL = "YOUR_GOOGLE_SHEET_CSV_EXPORT_URL"
APPS_SCRIPT_URL = "YOUR_APPS_SCRIPT_WEB_APP_URL"

@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df
    except Exception as e:
        return pd.DataFrame()

st.title("📊 AI-Powered Billing & Store Analytics Dashboard")

df = load_data()

if df.empty:
    st.warning("No transaction data found yet. Connect your Google Sheet URL in the script.")
else:
    # Ensure Date/Time columns are parsed
    df['Date'] = pd.to_datetime(df['Date'])
    df['Hour'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce').dt.hour

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Sales", f"₹ {int((df['Quantity'] * df['Unit Price']).sum())}")
    col2.metric("Total Transactions", len(df['Transaction ID'].unique()))
    col3.metric("New Customers", len(df[df['Customer Type'] == 'New']['Customer Phone'].unique()))
    col4.metric("Returning Customers", len(df[df['Customer Type'] == 'Old']['Customer Phone'].unique()))

    st.markdown("---")

    # 1. Rush Hour Analysis
    st.subheader("⏰ Shop Rush Timing & Peak Hours")
    rush_df = df.groupby('Hour')['Transaction ID'].count().reset_index()
    fig_rush = px.bar(rush_df, x='Hour', y='Transaction ID', title="Transactions by Hour of Day", labels={'Transaction ID': 'Footfall / Sales Count'})
    st.plotly_chart(fig_rush, use_container_width=True)

    # 2. Top Selling Products
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🔥 Best Selling Products")
        prod_df = df.groupby('Product Name')['Quantity'].sum().reset_index().sort_values(by='Quantity', ascending=False)
        fig_prod = px.bar(prod_df.head(10), x='Quantity', y='Product Name', orientation='h', title="Top Products by Units Sold")
        st.plotly_chart(fig_prod, use_container_width=True)

    with col_b:
        st.subheader("👥 Customer Segmentation (New vs. Old)")
        cust_type_df = df['Customer Type'].value_counts().reset_index()
        fig_cust = px.pie(cust_type_df, names='Customer Type', values='count', title="New vs Old Customer Ratio")
        st.plotly_chart(fig_cust, use_container_width=True)

    # 3. AI Insights Generator
    st.markdown("---")
    st.subheader("🤖 AI Store Performance Advisor")
    if st.button("Generate AI Business Insights"):
        summary_text = f"""
        Total Sales Records: {len(df)}
        Top Products: {prod_df.head(3).to_dict(orient='records')}
        Peak Hours: {rush_df.sort_values(by='Transaction ID', ascending=False).head(3).to_dict(orient='records')}
        Customer Breakdown: {cust_type_df.to_dict(orient='records')}
        """
        
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Analyze this retail shop data and provide 3 actionable business recommendations to optimize stock inventory and staff scheduling during rush hours:\n{summary_text}"
        )
        st.write(response.text)app.py

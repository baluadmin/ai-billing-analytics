import streamlit as st
import pandas as pd
import plotly.express as px
import requests

st.set_page_config(page_title="Smart Store Billing & Analytics Dashboard", layout="wide")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Database Connection")
sheet_csv_input = st.sidebar.text_input(
    "Google Sheet Published CSV URL",
    value="YOUR_GOOGLE_SHEET_CSV_EXPORT_URL",
    help="Paste your published CSV link from Google Sheets here."
)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx-sFUudPmSnrfciS08oQc8k_fAQ-KSniWa5PttB1L5XpLOx6CkGIw9wUrx38LxX8J5/exec"

@st.cache_data(ttl=10)
def load_data(url):
    if not url or url == "YOUR_GOOGLE_SHEET_CSV_EXPORT_URL":
        return pd.DataFrame()
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return pd.DataFrame()

st.title("📊 Smart Store Billing & Analytics Dashboard")

df = load_data(sheet_csv_input)

if df.empty:
    st.warning("⚠️ No transaction data connected yet.")
    st.info("""
    ### How to connect your Google Sheet in 3 steps:
    1. Open your Google Sheet containing your **Transactions** tab.
    2. Go to **File > Share > Publish to web**.
    3. Select your **Transactions** sheet, choose **Comma-separated values (.csv)**, click **Publish**, and copy the link into the **sidebar input box on the left**.
    """)
else:
    # Ensure Date/Time columns are parsed safely
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Hour'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce').dt.hour

    # Top Metrics Row
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

    # 2. Top Selling Products & Customer Segmentation
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

    # 3. Automated Smart Store Recommendations
    st.markdown("---")
    st.subheader("💡 Automated Store Performance Advisor")
    
    if not rush_df.empty and not prod_df.empty:
        peak_hour = int(rush_df.sort_values(by='Transaction ID', ascending=False).iloc[0]['Hour'])
        top_product = prod_df.iloc[0]['Product Name']
        top_qty = prod_df.iloc[0]['Quantity']
        
        total_cust_count = len(df)
        new_cust_count = len(df[df['Customer Type'] == 'New'])
        new_pct = int((new_cust_count / total_cust_count) * 100) if total_cust_count > 0 else 0

        st.info(f"""
        * **Peak Rush Alert:** Your busiest hour of the day is around **{peak_hour}:00 hours**. Ensure you have counter assistance ready during this slot.
        * **Top Demand Driver:** **{top_product}** leads sales with **{top_qty} units sold**. Keep adequate buffer stock for this item.
        * **Customer Retention:** **{new_pct}%** of your transactions are from first-time buyers. Consider loyalty rewards to encourage return visits.
        """)

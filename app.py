import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

st.set_page_config(page_title="Smart Store Billing & Analytics POS", layout="wide")

# --- CONFIGURATION ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1OzON29VseWISfGfXyEJ3evicXaBtPo8D0X54rxp71Jk/export?format=csv"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx-sFUudPmSnrfciS08oQc8k_fAQ-KSniWa5PttB1L5XpLOx6CkGIw9wUrx38LxX8J5/exec"

@st.cache_data(ttl=5)
def load_data(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return pd.DataFrame()

df = load_data(SHEET_CSV_URL)

# --- NAVIGATION TABS ---
st.title("🛒 Smart Store POS & Analytics Platform")
tab_billing, tab_analytics = st.tabs(["⚡ Counter Billing (POS)", "📊 Store Analytics & Rush Hours"])

# ==========================================
# TAB 1: FRONT-END BILLING & PRODUCT LIST
# ==========================================
with tab_billing:
    st.subheader("🛍️ Product Billing Counter")
    
    # Define your store product catalog & prices here
    product_catalog = {
        "Mobile Charger": 350,
        "Tempered Glass": 150,
        "Earphones": 500,
        "USB Cable": 200,
        "Power Bank": 1200,
        "Phone Case": 250,
        "Bluetooth Speaker": 999,
        "Memory Card 32GB": 450
    }

    col_form, col_summary = st.columns([1.2, 1])

    with col_form:
        with st.form("billing_form", clear_on_submit=True):
            st.markdown("### Customer & Item Details")
            customer_name = st.text_input("Customer Name")
            customer_phone = st.text_input("Customer Phone Number (Required for Tracking)")
            
            selected_product = st.selectbox("Select Product", list(product_catalog.keys()))
            unit_price = product_catalog[selected_product]
            
            st.text(f"Unit Price: ₹ {unit_price}")
            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
            
            submitted = st.form_submit_button("Print Bill & Save to Google Sheet")

    with col_summary:
        st.markdown("### 🧾 Current Bill Preview")
        total_amount = unit_price * quantity
        st.metric("Total Payable", f"₹ {total_amount}")
        
        if submitted:
            if not customer_phone or not customer_name:
                st.error("⚠️ Please enter Customer Name and Phone Number.")
            else:
                # Generate unique transaction ID
                tx_id = "TXN" + datetime.now().strftime("%Y%m%d%H%M%S")
                current_date = datetime.now().strftime("%Y-%m-%d")
                current_time = datetime.now().strftime("%H:%M:%S")

                payload = {
                    "transaction_id": tx_id,
                    "date": current_date,
                    "time": current_time,
                    "customer_phone": str(customer_phone).strip(),
                    "customer_name": customer_name.strip(),
                    "product_name": selected_product,
                    "quantity": int(quantity),
                    "unit_price": float(unit_price)
                }

                try:
                    # Send data to Google Apps Script Webhook
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Bill Generated Successfully! (ID: {tx_id})")
                        st.balloons()
                    else:
                        st.error("⚠️ Failed to record to Google Sheet. Check Apps Script deployment.")
                except Exception as ex:
                    st.error(f"Connection error: {ex}")

# ==========================================
# TAB 2: ANALYTICS & RUSH TIMING DASHBOARD
# ==========================================
with tab_analytics:
    st.subheader("📈 Live Store Analytics & Rush Hours")

    if df.empty:
        st.warning("⚠️ No transaction data found in your Google Sheet yet. Generate a bill in the POS tab above to see analytics!")
    else:
        # Parse Dates & Times safely
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df['Hour'] = pd.to_datetime(df['Time'], format='%H:%M:%S', errors='coerce').dt.hour

        # Top Metric Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sales", f"₹ {int((df['Quantity'] * df['Unit Price']).sum())}")
        c2.metric("Total Bills", len(df['Transaction ID'].unique()))
        c3.metric("New Customers", len(df[df['Customer Type'] == 'New']['Customer Phone'].unique()))
        c4.metric("Returning Customers", len(df[df['Customer Type'] == 'Old']['Customer Phone'].unique()))

        st.markdown("---")

        # 1. Rush Hour Timing Analysis
        st.subheader("⏰ Shop Rush Timing & Peak Hours")
        rush_df = df.groupby('Hour')['Transaction ID'].count().reset_index()
        fig_rush = px.bar(rush_df, x='Hour', y='Transaction ID', title="Footfall / Transactions by Hour of Day", labels={'Transaction ID': 'Sales Count'})
        st.plotly_chart(fig_rush, use_container_width=True)

        # 2. Product Demand & Customer Segments
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔥 Product Demand (Most Selling)")
            prod_df = df.groupby('Product Name')['Quantity'].sum().reset_index().sort_values(by='Quantity', ascending=False)
            fig_prod = px.bar(prod_df, x='Quantity', y='Product Name', orientation='h', title="Units Sold per Product")
            st.plotly_chart(fig_prod, use_container_width=True)

        with col_b:
            st.subheader("👥 Customer Retention (New vs Old)")
            cust_type_df = df['Customer Type'].value_counts().reset_index()
            fig_cust = px.pie(cust_type_df, names='Customer Type', values='count', title="New vs Old Ratio")
            st.plotly_chart(fig_cust, use_container_width=True)

        # 3. Smart Recommendations
        st.markdown("---")
        st.subheader("💡 Automated Store Performance Insights")
        if not rush_df.empty and not prod_df.empty:
            peak_hr = int(rush_df.sort_values(by='Transaction ID', ascending=False).iloc[0]['Hour'])
            top_prod = prod_df.iloc[0]['Product Name']
            top_qty = prod_df.iloc[0]['Units Sold'] if 'Units Sold' in prod_df.columns else prod_df.iloc[0]['Quantity']
            
            st.info(f"""
            * **Peak Rush Hour:** Your shop experiences the highest footfall around **{peak_hr}:00 hours**. Keep your billing counter staffed during this slot.
            * **Top Selling Product:** **{top_prod}** has the highest customer demand (**{top_qty} units**). Make sure you keep enough stock in your inventory.
            """)

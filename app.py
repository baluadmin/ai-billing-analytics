import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime

st.set_page_config(page_title="Smart Store POS & Analytics", layout="wide")

SHEET_ID = "1OzON29VseWISfGfXyEJ3evicXaBtPo8D0X54rxp71Jk"
TX_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Transactions"
INV_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Inventory"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx-sFUudPmSnrfciS08oQc8k_fAQ-KSniWa5PttB1L5XpLOx6CkGIw9wUrx38LxX8J5/exec"

@st.cache_data(ttl=5)
def load_sheet(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.astype(str).str.strip().str.title()
        return df
    except Exception as e:
        return pd.DataFrame()

df_tx = load_sheet(TX_CSV_URL)
df_inv = load_sheet(INV_CSV_URL)

st.title("🛒 Smart Store POS & Analytics Platform")
tab_billing, tab_analytics = st.tabs(["⚡ Counter Billing (POS)", "📊 Store Analytics & Inventory"])

# ==========================================
# TAB 1: FRONT-END BILLING COUNTER
# ==========================================
with tab_billing:
    st.subheader("🛍️ Product Billing Counter")

    # Build product catalog from Inventory tab safely
    product_catalog = {}
    if not df_inv.empty and 'Product Name' in df_inv.columns:
        for _, row in df_inv.iterrows():
            p_name = str(row['Product Name']).strip()
            # Skip empty or placeholder rows if any
            if p_name and p_name.lower() != 'nan':
                p_price = float(row['Unit Price']) if 'Unit Price' in df_inv.columns and pd.notna(row['Unit Price']) else 100.0
                product_catalog[p_name] = p_price

    col_form, col_summary = st.columns([1.2, 1])

    with col_form:
        with st.form("billing_form", clear_on_submit=True):
            st.markdown("### Customer & Item Details")
            customer_name = st.text_input("Customer Name")
            customer_phone = st.text_input("Customer Phone Number")
            
            # Product selection with search suggestions if inventory exists, otherwise empty text box
            if product_catalog:
                #selectbox acts as a suggestion/search dropdown with items from inventory
                selected_product = st.selectbox("Search or Select Product Name", ["-- Select Product --"] + list(product_catalog.keys()))
                unit_price = product_catalog.get(selected_product, 0.0) if selected_product != "-- Select Product --" else 0.0
            else:
                selected_product = st.text_input("Product Name (Inventory is empty)")
                unit_price = st.number_input("Unit Price (₹)", min_value=0.0, value=100.0, step=10.0)

            quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
            submitted = st.form_submit_button("Print Bill & Save to Google Sheet")

    with col_summary:
        st.markdown("### 🧾 Current Bill Preview")
        actual_price = unit_price if product_catalog else unit_price
        total_amount = actual_price * quantity
        st.metric("Total Payable", f"₹ {total_amount}")
        
        if submitted:
            final_prod = selected_product if product_catalog else selected_product
            if not customer_phone or not customer_name or final_prod == "-- Select Product --" or not final_prod:
                st.error("⚠️ Please fill in Customer Name, Phone Number, and select a valid Product.")
            else:
                tx_id = "TXN" + datetime.now().strftime("%Y%m%d%H%M%S")
                payload = {
                    "transaction_id": tx_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "customer_phone": str(customer_phone).strip(),
                    "customer_name": customer_name.strip(),
                    "product_name": final_prod.strip(),
                    "quantity": int(quantity),
                    "unit_price": float(actual_price)
                }

                try:
                    response = requests.post(APPS_SCRIPT_URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Bill Generated Successfully! (ID: {tx_id})")
                        st.balloons()
                    else:
                        st.error("⚠️ Failed to record to Google Sheet. Check Apps Script deployment.")
                except Exception as ex:
                    st.error(f"Connection error: {ex}")

# ==========================================
# TAB 2: ANALYTICS & INVENTORY DASHBOARD
# ==========================================
with tab_analytics:
    st.subheader("📈 Live Store Analytics & Inventory Stock")

    if not df_inv.empty:
        st.markdown("### 📦 Current Stock Levels")
        st.dataframe(df_inv, use_container_width=True)
        st.markdown("---")

    if df_tx.empty or 'Transaction Id' not in df_tx.columns:
        st.info("ℹ️ No transaction data found yet. Generate a bill in the POS tab to view sales analytics.")
    else:
        df_tx['Date'] = pd.to_datetime(df_tx['Date'], errors='coerce')
        df_tx['Hour'] = pd.to_datetime(df_tx['Time'], format='%H:%M:%S', errors='coerce').dt.hour if 'Time' in df_tx.columns else 12

        total_sales = int((df_tx['Quantity'] * df_tx['Unit Price']).sum()) if 'Quantity' in df_tx.columns and 'Unit Price' in df_tx.columns else 0
        total_bills = len(df_tx['Transaction Id'].unique())
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Sales", f"₹ {total_sales}")
        c2.metric("Total Bills", total_bills)
        c3.metric("New Customers", len(df_tx[df_tx['Customer Type'] == 'New']['Customer Phone'].unique()) if 'Customer Type' in df_tx.columns else 0)
        c4.metric("Returning Customers", len(df_tx[df_tx['Customer Type'] == 'Old']['Customer Phone'].unique()) if 'Customer Type' in df_tx.columns else 0)

        st.markdown("---")
        st.subheader("⏰ Shop Rush Timing & Peak Hours")
        rush_df = df_tx.groupby('Hour')['Transaction Id'].count().reset_index()
        fig_rush = px.bar(rush_df, x='Hour', y='Transaction Id', title="Footfall by Hour of Day")
        st.plotly_chart(fig_rush, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔥 Product Demand (Most Selling)")
            if 'Product Name' in df_tx.columns:
                prod_demand = df_tx.groupby('Product Name')['Quantity'].sum().reset_index().sort_values(by='Quantity', ascending=False)
                fig_prod = px.bar(prod_demand, x='Quantity', y='Product Name', orientation='h')
                st.plotly_chart(fig_prod, use_container_width=True)

        with col_b:
            if 'Customer Type' in df_tx.columns:
                st.subheader("👥 Customer Retention")
                cust_type_df = df_tx['Customer Type'].value_counts().reset_index()
                fig_cust = px.pie(cust_type_df, names='Customer Type', values='count')
                st.plotly_chart(fig_cust, use_container_width=True)

import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Gurukripa Siddha Clinic - Medstock", layout="wide", page_icon="💊")

# Database Connection
@st.cache_resource
def get_db_engine():
    try:
        db_url = st.secrets["DATABASE_URL"]
        return create_engine(db_url)
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

engine = get_db_engine()

# Create Table Structure
if engine:
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS medicines (
                    sl_no SERIAL PRIMARY KEY,
                    company_name TEXT,
                    medicine_name TEXT NOT NULL,
                    packing_type TEXT,
                    pack_size TEXT,
                    rate NUMERIC(10, 2) DEFAULT 0.0,
                    indications TEXT,
                    expiry_date DATE,
                    stock_available INT DEFAULT 0,
                    total_sold INT DEFAULT 0,
                    indent TEXT
                );
            """))
            conn.commit()
    except Exception as e:
        pass

# Header Section
st.title("🏥 Gurukripa Siddha Clinic - Medstock")
st.markdown("---")

# ---------------------------------------------------------
# TOP CONTROLS (SEARCH & SORT)
# ---------------------------------------------------------
col_search, col_sort, col_date = st.columns([3, 2, 2])

with col_search:
    search_query = st.text_input("🔍 Search Medicine / Company:", placeholder="Type medicine or company name...")

with col_sort:
    sort_option = st.selectbox("↕️ Sort Order:", [
        "Medicine Name (A-Z)",
        "Medicine Name (Z-A)",
        "Company Name (A-Z)",
        "Serial No (Ascending)",
        "Stock (Low to High)",
        "Expiry Date (Nearest)"
    ])

with col_date:
    st.info(f"📅 Today: **{date.today().strftime('%d-%b-%Y')}**")

st.markdown("---")

# ---------------------------------------------------------
# FORM & EDIT SECTION
# ---------------------------------------------------------
if engine:
    df_raw = pd.read_sql("SELECT * FROM medicines ORDER BY sl_no ASC;", engine)
   
    selected_med = None
    med_options = ["-- ➕ Add New Medicine --"] + [f"Sl:{row['sl_no']} | {row['medicine_name']} ({row['company_name'] if pd.notnull(row['company_name']) else ''})" for _, row in df_raw.iterrows()]
   
    selected_option = st.selectbox("✏️ Select Medicine to Edit / Record Sale (or choose Add New):", med_options)
   
    if selected_option != "-- ➕ Add New Medicine --":
        sl_selected = int(selected_option.split("|")[0].replace("Sl:", "").strip())
        selected_med = df_raw[df_raw['sl_no'] == sl_selected].iloc[0]

    st.subheader("📝 Medicine Details & Actions")
   
    with st.form("main_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
       
        with c1:
            company_name = st.text_input("Company Name:", value=selected_med['company_name'] if selected_med is not None and pd.notnull(selected_med['company_name']) else "")
            packing_type = st.text_input("Packing Type (e.g. Bottle, Packet, Jar):", value=selected_med['packing_type'] if selected_med is not None and pd.notnull(selected_med['packing_type']) else "Bottle")
            indications = st.text_input("Indications:", value=selected_med['indications'] if selected_med is not None and pd.notnull(selected_med['indications']) else "")
            indent = st.text_input("Indent:", value=selected_med['indent'] if selected_med is not None and pd.notnull(selected_med['indent']) else "")

        with c2:
            medicine_name = st.text_input("Medicine Name*:", value=selected_med['medicine_name'] if selected_med is not None else "")
            pack_size = st.text_input("Pack Size:", value=selected_med['pack_size'] if selected_med is not None and pd.notnull(selected_med['pack_size']) else "")
            exp_val = pd.to_datetime(selected_med['expiry_date']).date() if selected_med is not None and pd.notnull(selected_med['expiry_date']) else date.today() + timedelta(days=365)
            expiry_date = st.date_input("Expiry Date:", value=exp_val)

        with c3:
            rate = st.number_input("Rate (₹):", min_value=0.0, value=float(selected_med['rate']) if selected_med is not None and pd.notnull(selected_med['rate']) else 0.0, step=0.5)
            stock_available = st.number_input("Stock Available:", min_value=0, value=int(selected_med['stock_available']) if selected_med is not None and pd.notnull(selected_med['stock_available']) else 0, step=1)
            sale_qty = st.number_input("Sale Qty (Deduct Stock):", min_value=0, value=0, step=1)

        b1, b2, b3 = st.columns(3)
       
        with b1:
            btn_save = st.form_submit_button("➕ / ✏️ Save / Update Medicine", type="primary")
        with b2:
            btn_sale = st.form_submit_button("🛒 Record Sale & Update Stock")
        with b3:
            btn_clear = st.form_submit_button("🔄 Clear Form")

        # Logic: Add or Edit
        if btn_save:
            if medicine_name:
                with engine.connect() as conn:
                    if selected_med is None: # Add New
                        conn.execute(
                            text("""
                                INSERT INTO medicines (company_name, medicine_name, packing_type, pack_size, rate, indications, expiry_date, stock_available, indent)
                                VALUES (:c, :m, :pt, :ps, :r, :i, :e, :s, :ind);
                            """),
                            {"c": company_name, "m": medicine_name, "pt": packing_type, "ps": pack_size, "r": rate, "i": indications, "e": expiry_date, "s": stock_available, "ind": indent}
                        )
                        st.success(f"Added '{medicine_name}' successfully!")
                    else: # Update Existing
                        conn.execute(
                            text("""
                                UPDATE medicines
                                SET company_name=:c, medicine_name=:m, packing_type=:pt, pack_size=:ps, rate=:r, indications=:i, expiry_date=:e, stock_available=:s, indent=:ind
                                WHERE sl_no=:sl;
                            """),
                            {"c": company_name, "m": medicine_name, "pt": packing_type, "ps": pack_size, "r": rate, "i": indications, "e": expiry_date, "s": stock_available, "ind": indent, "sl": int(selected_med['sl_no'])}
                        )
                        st.success(f"Updated '{medicine_name}' successfully!")
                    conn.commit()
                st.rerun()
            else:
                st.warning("Please enter Medicine Name.")

        # Logic: Sale
        if btn_sale:
            if selected_med is not None and sale_qty > 0:
                if sale_qty <= int(selected_med['stock_available']):
                    with engine.connect() as conn:
                        conn.execute(
                            text("""
                                UPDATE medicines
                                SET stock_available = stock_available - :sq, total_sold = total_sold + :sq
                                WHERE sl_no = :sl;
                            """),
                            {"sq": sale_qty, "sl": int(selected_med['sl_no'])}
                        )
                        conn.commit()
                    st.success(f"Sold {sale_qty} unit(s) of '{selected_med['medicine_name']}'. Total Amount: ₹{sale_qty * float(rate):.2f}")
                    st.rerun()
                else:
                    st.error("Sale quantity exceeds available stock!")
            else:
                st.warning("Select a medicine and enter Sale Qty > 0.")

st.markdown("---")

# ---------------------------------------------------------
# TABLE & TICK DELETE SECTION
# ---------------------------------------------------------
st.subheader("📦 Stock Inventory Table")

if engine:
    try:
        df_table = pd.read_sql("SELECT * FROM medicines;", engine)
       
        if not df_table.empty:
            # Search Filter
            if search_query:
                sq_lower = search_query.lower()
                df_table = df_table[
                    df_table['medicine_name'].astype(str).str.lower().str.contains(sq_lower, na=False) |
                    df_table['company_name'].astype(str).str.lower().str.contains(sq_lower, na=False) |
                    df_table['indications'].astype(str).str.lower().str.contains(sq_lower, na=False)
                ]

            # Sorting Logic
            if sort_option == "Medicine Name (A-Z)":
                df_table = df_table.sort_values(by="medicine_name", ascending=True)
            elif sort_option == "Medicine Name (Z-A)":
                df_table = df_table.sort_values(by="medicine_name", ascending=False)
            elif sort_option == "Company Name (A-Z)":
                df_table = df_table.sort_values(by="company_name", ascending=True)
            elif sort_option == "Stock (Low to High)":
                df_table = df_table.sort_values(by="stock_available", ascending=True)
            elif sort_option == "Expiry Date (Nearest)":
                df_table = df_table.sort_values(by="expiry_date", ascending=True)
            else:
                df_table = df_table.sort_values(by="sl_no", ascending=True)

            # Rename columns
            df_display = df_table.rename(columns={
                'sl_no': 'Serial No',
                'company_name': 'Company Name',
                'medicine_name': 'Medicine Name',
                'packing_type': 'Packing Type',
                'pack_size': 'Pack Size',
                'rate': 'Rate (₹)',
                'indications': 'Indications',
                'expiry_date': 'Expiry Date',
                'stock_available': 'Stock Available',
                'total_sold': 'Total Sold',
                'indent': 'Indent'
            })

            # Expiry RED Color Styling
            today = date.today()
            near_exp = today + timedelta(days=30)

            def highlight_expiry(row):
                if pd.notnull(row["Expiry Date"]):
                    exp = pd.to_datetime(row["Expiry Date"]).date()
                    if exp <= today:
                        return ['background-color: #ff4d4d; color: white; font-weight: bold;'] * len(row)
                    elif exp <= near_exp:
                        return ['background-color: #ff9999; color: black;'] * len(row)
                return [''] * len(row)

            # Interactive Table with Tick Selection
            edited_df = st.data_editor(
                df_display.style.apply(highlight_expiry, axis=1),
                use_container_width=True,
                num_rows="dynamic",
                disabled=["Serial No", "Total Sold"] # Allow editing all columns
            )

            # Delete Selected / Ticked Medicines
            col_del1, col_del2 = st.columns([1, 4])
            with col_del1:
                selected_rows_to_del = st.multiselect("Select Serial No to Delete Ticked:", df_display["Serial No"].tolist())
                if st.button("🗑️ Delete Selected Ticked", type="primary"):
                    if selected_rows_to_del:
                        with engine.connect() as conn:
                            for sl in selected_rows_to_del:
                                conn.execute(text("DELETE FROM medicines WHERE sl_no = :sl;"), {"sl": int(sl)})
                            conn.commit()
                        st.success(f"Deleted {len(selected_rows_to_del)} item(s) successfully!")
                        st.rerun()
                    else:
                        st.warning("Please select Serial No to delete.")

            # Alerts
            expired_items = df_display[pd.to_datetime(df_display['Expiry Date']).dt.date <= today]
            if not expired_items.empty:
                st.error(f"🚨 **ALERT:** {len(expired_items)} medicine(s) have EXPIRED (Highlighted in Red)!")

        else:
            st.info("No medicines added yet!")
    except Exception as e:
        st.error(f"Error loading table: {e}")

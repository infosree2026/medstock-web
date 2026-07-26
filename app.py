import os
import pandas as pd
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Gurukripa Siddha Clinic - Medstock",
    page_icon="💊",
    layout="wide",
)


# Supabase Database Connection
def get_connection():
  return psycopg2.connect(st.secrets["DATABASE_URL"])


# Initialize Database Table
def init_db():
  conn = get_connection()
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            sl_no TEXT PRIMARY KEY,
            company_name TEXT,
            medicine_name TEXT,
            packing_type TEXT,
            pack_size TEXT,
            rate TEXT,
            indications TEXT,
            expiry_date TEXT,
            stock_available INTEGER,
            total_sold INTEGER DEFAULT 0,
            indent TEXT
        )
    """)
  conn.commit()
  cursor.close()
  conn.close()


try:
  init_db()
except Exception as e:
  st.error(f"Database Connection Error: {e}")

# ==========================================
# --- HEADER WITH LOGO ---
# ==========================================
col_logo, col_title = st.columns([1, 6])

with col_logo:
  if os.path.exists("logo.png"):
    st.image("logo.png", width=90)
  else:
    st.title("💊")

with col_title:
  st.title("Gurukripa Siddha Clinic")
  st.subheader("Medstock Management System")

st.divider()

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(
    ["📦 Medicine Inventory", "➕ Add New Stock", "🛍️ Record Sale"]
)

# ==========================================
# --- TAB 1: INVENTORY, SEARCH & RED HIGHLIGHT ---
# ==========================================
with tab1:
  st.write("### Current Stock List")
  try:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM medicines ORDER BY medicine_name ASC", conn
    )
    conn.close()

    if not df.empty:
      search = st.text_input("🔍 Search Medicine / Company:")
      if search:
        df = df[
            df["medicine_name"].str.contains(search, case=False, na=False)
            | df["company_name"].str.contains(search, case=False, na=False)
        ]

      # Expired items red ആക്കാനുള്ള തീയതി ചെക്കിംഗ്
      today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

      def highlight_expired(row):
        exp_date = str(row["expiry_date"])
        if exp_date and exp_date < today_str:
          return [
              "background-color: #fee2e2; color: #dc2626; font-weight: bold"
          ] * len(row)
        return [""] * len(row)

      styled_df = df.style.apply(highlight_expired, axis=1)

      st.dataframe(styled_df, use_container_width=True)

      # CSV / Excel Export
      csv = df.to_csv(index=False).encode("utf-8")
      st.download_button(
          "📊 Download Excel/CSV Data",
          data=csv,
          file_name="Medstock_Data.csv",
          mime="text/csv",
      )
    else:
      st.info("No medicines added yet!")
  except Exception as e:
    st.error(f"Error loading data: {e}")

# ==========================================
# --- TAB 2: ADD MEDICINE ---
# ==========================================
with tab2:
  st.write("### Add New Medicine Entry")
  with st.form("add_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
      sl_no = st.text_input("Serial No *")
      company_name = st.text_input("Company Name")
      medicine_name = st.text_input("Medicine Name")
    with col2:
      packing_type = st.selectbox(
          "Packing Type",
          ["Bottle", "Packet", "Box", "Strip", "Tube", "Jar", "Other"],
      )
      pack_size = st.text_input("Pack Size")
      rate = st.text_input("Rate")
    with col3:
      indications = st.text_input("Indications")
      expiry_date = st.date_input("Expiry Date")
      stock_available = st.number_input(
          "Stock Available", min_value=0, step=1
      )
      indent = st.text_input("Indent")

    submit = st.form_submit_button("➕ Save Medicine")

    if submit:
      if not sl_no or not medicine_name:
        st.warning("Serial No and Medicine Name are required!")
      else:
        try:
          conn = get_connection()
          cursor = conn.cursor()
          cursor.execute(
              """
                        INSERT INTO medicines (sl_no, company_name, medicine_name, packing_type, pack_size, rate, indications, expiry_date, stock_available, indent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
              (
                  sl_no,
                  company_name,
                  medicine_name,
                  packing_type,
                  pack_size,
                  rate,
                  indications,
                  str(expiry_date),
                  stock_available,
                  indent,
              ),
          )
          conn.commit()
          cursor.close()
          conn.close()
          st.success(f"{medicine_name} Added Successfully!")
          st.rerun()
        except Exception as e:
          st.error(f"Failed to add: Serial No might already exist! ({e})")

# ==========================================
# --- TAB 3: RECORD SALE ---
# ==========================================
with tab3:
  st.write("### Record Sale (Stock Deduct)")
  try:
    conn = get_connection()
    meds_df = pd.read_sql_query(
        "SELECT sl_no, medicine_name, stock_available, total_sold FROM"
        " medicines",
        conn,
    )
    conn.close()

    if not meds_df.empty:
      med_options = {
          f"{row['medicine_name']} (Stock: {row['stock_available']})": (
              row["sl_no"],
              row["stock_available"],
              row["total_sold"],
          )
          for _, row in meds_df.iterrows()
      }
      selected_med = st.selectbox(
          "Select Medicine for Sale", list(med_options.keys())
      )

      if selected_med:
        sl_no, current_stock, current_sold = med_options[selected_med]
        sale_qty = st.number_input("Sale Qty", min_value=1, step=1)

        if st.button("🛍️ Deduct & Update Sale"):
          if sale_qty > current_stock:
            st.error("Sale quantity is higher than available stock!")
          else:
            new_stock = current_stock - sale_qty
            new_sold = (current_sold or 0) + sale_qty
            try:
              conn = get_connection()
              cursor = conn.cursor()
              cursor.execute(
                  "UPDATE medicines SET stock_available = %s, total_sold = %s"
                  " WHERE sl_no = %s",
                  (new_stock, new_sold, sl_no),
              )
              conn.commit()
              cursor.close()
              conn.close()
              st.success(
                  f"Sale Recorded! Remaining Stock for {selected_med}:"
                  f" {new_stock}"
              )
              st.rerun()
            except Exception as e:
              st.error(f"Error updating sale: {e}")
  except Exception as e:
    st.error(f"Error: {e}")

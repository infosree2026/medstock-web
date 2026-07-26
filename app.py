import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Gurukripa Siddha Clinic", layout="wide", page_icon="💊")

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

# Create Tables Automatically
if engine:
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS medicines (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    quantity INT DEFAULT 0,
                    price NUMERIC(10, 2),
                    expiry_date DATE
                );
            """))
            conn.commit()
    except Exception as e:
        st.error(f"Table Creation Error: {e}")

# Header
st.title("🏥 Gurukripa Siddha Clinic")
st.caption("Medstock Management System")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Medicine Inventory",
    "➕ Add / Edit Stock",
    "🛒 Record Sale",
    "🗑️ Manage / Delete"
])

# ---------------------------------------------------------
# TAB 1: INVENTORY & SEARCH (WITH SORTING & EXPIRY RED ALERT)
# ---------------------------------------------------------
with tab1:
    st.header("Stock Inventory")
    if engine:
        try:
            col_search, col_sort = st.columns([3, 1])
           
            with col_search:
                search_query = st.text_input("🔍 Search Medicine by Name or Category", "")
           
            with col_sort:
                sort_option = st.selectbox("↕️ Sort By", ["Newest First", "Medicine Name (A-Z)", "Medicine Name (Z-A)", "Quantity (Low to High)", "Quantity (High to Low)"])
           
            # Base SQL Order
            if sort_option == "Medicine Name (A-Z)":
                order_by = "ORDER BY LOWER(name) ASC"
            elif sort_option == "Medicine Name (Z-A)":
                order_by = "ORDER BY LOWER(name) DESC"
            elif sort_option == "Quantity (Low to High)":
                order_by = "ORDER BY quantity ASC"
            elif sort_option == "Quantity (High to Low)":
                order_by = "ORDER BY quantity DESC"
            else:
                order_by = "ORDER BY id DESC"

            if search_query:
                query = f"""
                    SELECT id AS "ID", name AS "Medicine Name", category AS "Category",
                           quantity AS "Quantity", price AS "Price (₹)", expiry_date AS "Expiry Date"
                    FROM medicines
                    WHERE LOWER(name) LIKE LOWER('%{search_query}%') OR LOWER(category) LIKE LOWER('%{search_query}%')
                    {order_by};
                """
            else:
                query = f"""
                    SELECT id AS "ID", name AS "Medicine Name", category AS "Category",
                           quantity AS "Quantity", price AS "Price (₹)", expiry_date AS "Expiry Date"
                    FROM medicines {order_by};
                """
           
            df = pd.read_sql(query, engine)
           
            if not df.empty:
                today = date.today()
                near_expiry = today + timedelta(days=30)
               
                # Highlight rows: Expiry past/near in RED
                def highlight_expiry(row):
                    exp = row["Expiry Date"]
                    if pd.notnull(exp):
                        if exp <= today:
                            return ['background-color: #ff4d4d; color: white; font-weight: bold;'] * len(row)
                        elif exp <= near_expiry:
                            return ['background-color: #ff9999; color: black;'] * len(row)
                    return [''] * len(row)

                # Show table with color highlighting
                st.dataframe(df.style.apply(highlight_expiry, axis=1), use_container_width=True)
               
                # Expiry Warning Boxes
                expired_count = df[df["Expiry Date"] <= today]
                if not expired_count.empty:
                    st.error(f"🚨🚨 **ALERT:** {len(expired_count)} medicine(s) have EXPIRED! Please remove them.")
               
                # Low stock notification
                low_stock = df[df["Quantity"] <= 5]
                if not low_stock.empty:
                    st.warning(f"⚠️ **Stock Alert:** {len(low_stock)} medicine(s) have low stock (5 or less)!")
            else:
                st.info("No medicines found!")
        except Exception as e:
            st.error(f"Error loading data: {e}")

# ---------------------------------------------------------
# TAB 2: ADD / EDIT ALL FIELDS OF STOCK
# ---------------------------------------------------------
with tab2:
    st.header("Add or Edit Medicine Details")
   
    action = st.radio("Choose Action", ["Add New Medicine", "Edit Existing Medicine (All Fields)"], horizontal=True)
   
    if action == "Add New Medicine":
        with st.form("add_form", clear_on_submit=True):
            name = st.text_input("Medicine Name*")
            category = st.text_input("Category (e.g., Lehyam, Choornam, Thailam)")
            quantity = st.number_input("Quantity", min_value=1, step=1)
            price = st.number_input("Price per unit (₹)", min_value=0.0, step=0.5)
            exp_date = st.date_input("Expiry Date", value=date.today() + timedelta(days=365))
           
            submitted = st.form_submit_button("Save Medicine")
            if submitted:
                if name:
                    try:
                        with engine.connect() as conn:
                            conn.execute(
                                text("INSERT INTO medicines (name, category, quantity, price, expiry_date) VALUES (:n, :c, :q, :p, :e);"),
                                {"n": name, "c": category, "q": quantity, "p": price, "e": exp_date}
                            )
                            conn.commit()
                        st.success(f"Added '{name}' successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding medicine: {e}")
                else:
                    st.warning("Please enter medicine name.")
                   
    else: # Edit Existing Medicine
        if engine:
            try:
                df_edit = pd.read_sql("SELECT * FROM medicines ORDER BY name ASC;", engine)
                if not df_edit.empty:
                    med_dict = {f"{row['name']} (ID: {row['id']})": row for _, row in df_edit.iterrows()}
                    selected_med_str = st.selectbox("Select Medicine to Edit", list(med_dict.keys()))
                    selected_med = med_dict[selected_med_str]
                   
                    st.subheader(f"Editing: {selected_med['name']}")
                   
                    with st.form("edit_form"):
                        edit_name = st.text_input("Medicine Name", value=selected_med['name'])
                        edit_category = st.text_input("Category", value=selected_med['category'] if selected_med['category'] else "")
                        edit_quantity = st.number_input("Quantity", min_value=0, value=int(selected_med['quantity']), step=1)
                        edit_price = st.number_input("Price per unit (₹)", min_value=0.0, value=float(selected_med['price'] if selected_med['price'] else 0.0), step=0.5)
                       
                        curr_exp = selected_med['expiry_date'] if pd.notnull(selected_med['expiry_date']) else date.today()
                        edit_exp_date = st.date_input("Expiry Date", value=curr_exp)
                       
                        update_submitted = st.form_submit_button("Update Medicine Details")
                        if update_submitted:
                            with engine.connect() as conn:
                                conn.execute(
                                    text("""
                                        UPDATE medicines
                                        SET name = :n, category = :c, quantity = :q, price = :p, expiry_date = :e
                                        WHERE id = :id;
                                    """),
                                    {
                                        "n": edit_name,
                                        "c": edit_category,
                                        "q": edit_quantity,
                                        "p": edit_price,
                                        "e": edit_exp_date,
                                        "id": selected_med['id']
                                    }
                                )
                                conn.commit()
                            st.success(f"Updated '{edit_name}' successfully!")
                            st.rerun()
                else:
                    st.info("No medicines available to edit.")
            except Exception as e:
                st.error(f"Error loading medicine for edit: {e}")

# ---------------------------------------------------------
# TAB 3: RECORD SALE
# ---------------------------------------------------------
with tab3:
    st.header("Record Sale / Dispense Medicine")
    if engine:
        try:
            df_sale = pd.read_sql("SELECT id, name, quantity, price FROM medicines WHERE quantity > 0 ORDER BY name ASC;", engine)
            if not df_sale.empty:
                med_dict = {f"{row['name']} (Stock: {row['quantity']} | Price: ₹{row['price']})": row for _, row in df_sale.iterrows()}
                selected_med_str = st.selectbox("Select Medicine Sold", list(med_dict.keys()))
                selected_med = med_dict[selected_med_str]
               
                sell_qty = st.number_input("Quantity Sold", min_value=1, max_value=int(selected_med['quantity']), step=1)
                total_price = sell_qty * float(selected_med['price'])
               
                st.write(f"💵 **Total Amount: ₹{total_price:.2f}**")
               
                if st.button("Complete Sale", type="primary"):
                    with engine.connect() as conn:
                        conn.execute(
                            text("UPDATE medicines SET quantity = quantity - :q WHERE id = :id;"),
                            {"q": sell_qty, "id": selected_med['id']}
                        )
                        conn.commit()
                    st.success(f"Sold {sell_qty} unit(s) of '{selected_med['name']}'.")
                    st.rerun()
            else:
                st.info("No medicines currently in stock to sell.")
        except Exception as e:
            st.error(f"Error recording sale: {e}")

# ---------------------------------------------------------
# TAB 4: DELETE / MANAGE
# ---------------------------------------------------------
with tab4:
    st.header("Delete Medicine Entry")
    if engine:
        try:
            df_del = pd.read_sql("SELECT id, name FROM medicines ORDER BY name ASC;", engine)
            if not df_del.empty:
                med_list = {f"{row['name']} (ID: {row['id']})": row['id'] for _, row in df_del.iterrows()}
                selected_med = st.selectbox("Select Medicine to Delete", list(med_list.keys()))
               
                if st.button("🗑️ Delete Selected Medicine", type="primary"):
                    med_id = med_list[selected_med]
                    with engine.connect() as conn:
                        conn.execute(
                            text("DELETE FROM medicines WHERE id = :id;"),
                            {"id": med_id}
                        )
                        conn.commit()
                    st.success("Medicine deleted successfully!")
                    st.rerun()
            else:
                st.info("No medicines available to delete.")
        except Exception as e:
            st.error(f"Error deleting medicine: {e}")

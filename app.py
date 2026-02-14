import streamlit as st
import pandas as pd
import glob

# --- 1. Config หน้าเว็บ (ต้องอยู่บรรทัดแรกสุด ห้ามย้าย) ---
st.set_page_config(
    page_title="PharmaSales Dashboard",
    page_icon="💊",
    layout="wide"
)

# ==========================================
# 🔐 ส่วนจัดการระบบ Login (แก้ไขใหม่: เสถียรขึ้น)
# ==========================================

# รหัสผ่านที่ถูกต้อง
VALID_PASSWORDS = ["wrd022026", "onn022026"]

# ตรวจสอบสถานะการล็อกอิน
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ถ้ายังไม่ล็อกอิน ให้แสดงหน้า Login
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;">
                <h1 style="color: #0ea5e9;">💊 PharmaSales</h1>
                <p style="color: gray;">กรุณากรอกรหัสผ่านเพื่อเข้าใช้งาน</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ใช้ Form แบบง่าย (ตัด Logic ซับซ้อนออก)
        with st.form("login_form"):
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True, type="primary")
            
            if submit_button:
                if password in VALID_PASSWORDS:
                    st.session_state['logged_in'] = True
                    st.rerun() # รีโหลดหน้าทันทีเมื่อรหัสถูก
                else:
                    st.error("❌ รหัสผ่านไม่ถูกต้อง")
    
    st.stop() # 🛑 หยุดการทำงานส่วนอื่นจนกว่าจะล็อกอินผ่าน

# ==========================================
# 📊 ส่วนโปรแกรมหลัก (Dashboard)
# (ทำงานเมื่อ logged_in = True เท่านั้น)
# ==========================================

# --- ฟังก์ชันโหลดข้อมูล ---
@st.cache_data
def load_data():
    files = glob.glob("*.xlsx") + glob.glob("*.XLSX") + glob.glob("*.csv")
    if not files:
        return None, "❌ ไม่พบไฟล์ข้อมูล (.xlsx หรือ .csv) ใน GitHub Repository นี้"
    
    target_file = files[0]
    df = None
    
    try:
        if target_file.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(target_file, engine='openpyxl')
        else:
            for enc in ['utf-8', 'cp874', 'tis-620']:
                try:
                    df = pd.read_csv(target_file, encoding=enc)
                    break
                except: continue
        
        if df is None: return None, "อ่านไฟล์ไม่ได้", target_file

        df.columns = df.columns.str.strip() 
        
        # Mapping Column
        col_map = {
            'ID': 'PERSONID', 'FNAME': 'FNAME', 'LNAME': 'LNAME',
            'BRANCH': 'NAME', 'ITEM': 'ITEMNAME', 'SKU': 'ITEMID',
            'QTY': 'BASEQUANTITY', 'PRICE': 'PRICE', 'AMOUNT': 'AMOUNT',
            'GROUP': 'CF_ITEMGROUPL1_GROUPNAME', 'UNIT': 'CF_UNITNAME'
        }
        
        df['Search_ID'] = df[col_map['ID']].astype(str).str.replace(r'[^0-9]', '', regex=True)
        f = df[col_map['FNAME']].fillna('').astype(str)
        l = df[col_map['LNAME']].fillna('').astype(str)
        df['Search_Name'] = f + ' ' + l

        return df, col_map, target_file

    except Exception as e:
        return None, f"Error: {e}", target_file

df, col_map, filename = load_data()

# --- Sidebar ---
with st.sidebar:
    st.title("💊 Pharma Lookup")
    st.caption(f"File: {filename}")
    st.markdown("---")
    
    search_query = st.text_input("🔍 ค้นหา (เบอร์โทร/ชื่อ)", placeholder="พิมพ์คำค้นหา...")
    selected_customer_id = None
    
    if df is not None and search_query:
        mask = (df['Search_ID'].str.contains(search_query, na=False)) | \
               (df['Search_Name'].str.contains(search_query, na=False))
        results = df[mask]
        customers = results[['Search_ID', 'Search_Name']].drop_duplicates().head(50)
        
        if not customers.empty:
            st.success(f"พบ {len(customers)} รายชื่อ")
            choice = st.radio("เลือกรายชื่อ:", customers.itertuples(), format_func=lambda x: f"{x.Search_Name} ({x.Search_ID})")
            selected_customer_id = choice.Search_ID
        else:
            st.warning("ไม่พบข้อมูล")

    st.markdown("---")
    if st.button("🔒 ออกจากระบบ (Logout)"):
        st.session_state['logged_in'] = False
        st.rerun()

# --- Main Content ---

if selected_customer_id and df is not None:
    cust_df = df[df['Search_ID'] == selected_customer_id]
    info = cust_df.iloc[0]
    
    # คำนวณยอด
    total_spend = cust_df[col_map['AMOUNT']].sum()
    total_items = cust_df[col_map['QTY']].sum()
    top_cat = cust_df[col_map['GROUP']].mode()[0] if col_map['GROUP'] in cust_df else "-"
    
    # แสดงสาขาทั้งหมด
    unique_branches = cust_df[col_map['BRANCH']].unique()
    branch_display = ", ".join([str(b) for b in unique_branches if pd.notna(b)])

    # Header
    st.title(info['Search_Name'])
    st.markdown(f"**สมาชิก:** `{selected_customer_id}`  |  **สาขา:** `{branch_display}`")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💰 ยอดซื้อรวม", f"฿{total_spend:,.0f}")
    m2.metric("📦 จำนวนชิ้นรวม", f"{total_items:,.0f}")
    m3.metric("🏆 หมวดหมู่หลัก", str(top_cat)[:20])

    st.markdown("---")
    st.subheader("🛒 รายการสินค้าที่สั่งซื้อ")
    
    tab1, tab2 = st.tabs(["📊 สรุปรายการยอดนิยม (Grouped)", "📝 ประวัติละเอียด (All Logs)"])

    # --- Tab 1: แบบสรุป ---
    with tab1:
        summary_df = cust_df.groupby(
            [col_map['SKU'], col_map['ITEM'], col_map['UNIT'], col_map['GROUP']]
        ).agg(
            Total_Qty=(col_map['QTY'], 'sum'),
            Total_Amount=(col_map['AMOUNT'], 'sum'),
            Avg_Price=(col_map['PRICE'], 'mean')
        ).reset_index()
        
        summary_df = summary_df.sort_values(by='Total_Amount', ascending=False)
        
        # จัดลำดับ Column (SKU, สินค้า, จำนวน, หน่วย, ยอดเงิน, เฉลี่ย, หมวด)
        summary_df = summary_df[[
            col_map['SKU'], 
            col_map['ITEM'], 
            'Total_Qty',    
            col_map['UNIT'], 
            'Total_Amount', 
            'Avg_Price', 
            col_map['GROUP']
        ]]

        st.dataframe(
            summary_df,
            column_config={
                col_map['SKU']: st.column_config.TextColumn("SKU", width="small"),
                col_map['ITEM']: "สินค้า",
                "Total_Qty": st.column_config.NumberColumn("จำนวนรวม", format="%d"),
                col_map['UNIT']: st.column_config.TextColumn("หน่วย", width="small"),
                "Total_Amount": st.column_config.ProgressColumn(
                    "ยอดเงินรวม",

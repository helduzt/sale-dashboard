import streamlit as st
import pandas as pd
import glob

# --- 1. Config หน้าเว็บ ---
st.set_page_config(
    page_title="PharmaSales Dashboard",
    page_icon="💊",
    layout="wide" # ใช้พื้นที่เต็มจอ
)

# --- 2. ฟังก์ชันโหลดข้อมูล (หาไฟล์ Excel ใน Folder อัตโนมัติ) ---
@st.cache_data
def load_data():
    # หาไฟล์ Excel ทั้งหมด
    files = glob.glob("*.xlsx") + glob.glob("*.XLSX")
    
    if not files:
        return None, "❌ ไม่พบไฟล์ Excel (.xlsx) ใน GitHub Repository นี้"
    
    target_file = files[0] # เอาไฟล์แรกที่เจอ
    
    try:
        # อ่านไฟล์ Excel
        df = pd.read_excel(target_file, engine='openpyxl')
        
        # Clean Data
        df.columns = df.columns.str.strip() # ลบช่องว่างชื่อ Column
        
        # Mapping ชื่อ Column ให้ตรงกับตัวแปร
        # (แก้ไขชื่อทางขวาได้ถ้าหัวตารางใน Excel เปลี่ยน)
        col_map = {
            'ID': 'PERSONID',
            'FNAME': 'FNAME',
            'LNAME': 'LNAME',
            'BRANCH': 'NAME',
            'ITEM': 'ITEMNAME',
            'QTY': 'BASEQUANTITY',
            'PRICE': 'PRICE',
            'AMOUNT': 'AMOUNT',
            'GROUP': 'CF_ITEMGROUPL1_GROUPNAME',
            'UNIT': 'CF_UNITNAME'
        }
        
        # สร้าง Column สำหรับค้นหา (Search_ID)
        if col_map['ID'] in df.columns:
            # แปลงเป็น Text และเก็บเฉพาะตัวเลข
            df['Search_ID'] = df[col_map['ID']].astype(str).str.replace(r'[^0-9]', '', regex=True)
        else:
            df['Search_ID'] = '0'
            
        # สร้าง Column ชื่อเต็ม (Search_Name)
        f_col = col_map['FNAME']
        l_col = col_map['LNAME']
        
        fname = df[f_col].fillna('') if f_col in df.columns else ''
        lname = df[l_col].fillna('') if l_col in df.columns else ''
        df['Search_Name'] = fname.astype(str) + ' ' + lname.astype(str)

        return df, col_map, target_file

    except Exception as e:
        return None, f"Error: {e}", target_file

# เรียกใช้ฟังก์ชันโหลดข้อมูล
df, col_map, filename = load_data()

# --- 3. UI ส่วน Sidebar (เมนูค้นหา) ---
with st.sidebar:
    st.title("💊 Pharma Lookup")
    st.caption(f"File: {filename}")
    st.markdown("---")
    
    # ช่องค้นหา
    search_query = st.text_input("🔍 ค้นหา (เบอร์โทร/ชื่อ)", placeholder="พิมพ์คำค้นหา...")
    
    selected_customer_id = None
    
    if df is not None and search_query:
        # กรองข้อมูล
        mask = (df['Search_ID'].str.contains(search_query, na=False)) | \
               (df['Search_Name'].str.contains(search_query, na=False))
        results = df[mask]
        
        # ดึงรายชื่อคนที่ไม่ซ้ำ
        customers = results[['Search_ID', 'Search_Name']].drop_duplicates().head(50)
        
        if not customers.empty:
            st.success(f"พบ {len(customers)} รายชื่อ")
            
            # ใช้ Radio Button เลือกรายชื่อ (Clean กว่าปุ่มเยอะๆ)
            choice = st.radio(
                "ผลลัพธ์การค้นหา:",
                options=customers.itertuples(),
                format_func=lambda x: f"{x.Search_Name} ({x.Search_ID})"
            )
            selected_customer_id = choice.Search_ID
        else:
            st.warning("ไม่พบข้อมูล")

# --- 4. Main Content (ส่วนแสดงผลหลัก) ---

if selected_customer_id and df is not None:
    # ดึงข้อมูลลูกค้าคนนั้น
    cust_df = df[df['Search_ID'] == selected_customer_id]
    info = cust_df.iloc[0]
    
    # เตรียมตัวแปร
    c_amount = col_map['AMOUNT']
    c_qty = col_map['QTY']
    c_group = col_map['GROUP']
    c_branch = col_map['BRANCH']
    
    # คำนวณยอด
    total_spend = cust_df[c_amount].sum() if c_amount in cust_df else 0
    total_items = cust_df[c_qty].sum() if c_qty in cust_df else 0
    
    top_cat = "-"
    if c_group in cust_df:
        try: top_cat = cust_df[c_group].mode()[0]
        except: pass
        
    branch = info[c_branch] if c_branch in cust_df else "-"

    # --- ส่วนแสดงผล (Native Streamlit) ---
    
    # 1. Header
    st.title(info['Search_Name'])
    st.markdown(f"**เบอร์โทร:** `{selected_customer_id}`  |  **สาขา:** `{branch}`")
    st.markdown("---")

    # 2. Metrics (KPI Cards)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💰 ยอดซื้อรวม (Total Spend)", f"฿{total_spend:,.2f}")
    with c2:
        st.metric("📦 จำนวนรายการ (Items)", f"{total_items:,.0f} ชิ้น")
    with c3:
        st.metric("🏆 กลุ่มสินค้าหลัก", str(top_cat)[:20]) # ตัดคำถ้ายาวไป

    # 3. Data Table (Interactive)
    st.subheader("📝 ประวัติการสั่งซื้อ")
    
    # เลือกเฉพาะ Column ที่จำเป็นมาแสดง
    show_cols = [col_map['ITEMNAME'], col_map['CF_ITEMGROUPL1_GROUPNAME'], 
                 col_map['BASEQUANTITY'], col_map['CF_UNITNAME'], 
                 col_map['PRICE'], col_map['AMOUNT']]
    
    display_df = cust_df[show_cols].copy()
    
    # ใช้ st.dataframe แบบ Configurable
    st.dataframe(
        display_df,
        column_config={
            col_map['ITEMNAME']: "ชื่อสินค้า",
            col_map['CF_ITEMGROUPL1_GROUPNAME']: "หมวดหมู่",
            col_map['BASEQUANTITY']: st.column_config.NumberColumn("จำนวน", format="%d"),
            col_map['CF_UNITNAME']: "หน่วย",
            col_map['PRICE']: st.column_config.NumberColumn("ราคา/หน่วย", format="฿%.2f"),
            col_map['AMOUNT']: st.column_config.NumberColumn("รวมเงิน", format="฿%.2f"),
        },
        use_container_width=True, # ให้ตารางขยายเต็มจอสวยๆ
        hide_index=True, # ซ่อนเลขบรรทัด 0,1,2
        height=500 # กำหนดความสูง
    )

else:
    # หน้าจอเริ่มต้น (Welcome Screen)
    st.info("👈 กรุณาพิมพ์ชื่อ หรือ เบอร์โทรศัพท์ ที่แถบเมนูด้านซ้ายเพื่อเริ่มค้นหา")
    
    # (Optional) แสดงสถิติภาพรวมทั้งบริษัท
    if df is not None:
        st.markdown("### 📊 ภาพรวมข้อมูลทั้งหมด")
        col1, col2 = st.columns(2)
        col1.metric("จำนวนลูกค้าทั้งหมด", f"{df['Search_ID'].nunique():,} คน")
        col2.metric("จำนวนรายการทั้งหมด", f"{len(df):,} รายการ")

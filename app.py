import streamlit as st
import pandas as pd
import glob

# --- 1. Config หน้าเว็บ ---
st.set_page_config(
    page_title="PharmaSales Dashboard",
    page_icon="💊",
    layout="wide"
)

# --- 2. ฟังก์ชันโหลดข้อมูล ---
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
            'BRANCH': 'NAME', 'ITEM': 'ITEMNAME', 'SKU': 'ITEMID', # เพิ่ม Mapping SKU
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

# --- 3. Sidebar ---
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

# --- 4. Main Content ---

if selected_customer_id and df is not None:
    cust_df = df[df['Search_ID'] == selected_customer_id]
    info = cust_df.iloc[0]
    
    total_spend = cust_df[col_map['AMOUNT']].sum()
    total_items = cust_df[col_map['QTY']].sum()
    top_cat = cust_df[col_map['GROUP']].mode()[0] if col_map['GROUP'] in cust_df else "-"
    branch = info[col_map['BRANCH']]

    st.title(info['Search_Name'])
    st.markdown(f"**สมาชิก:** `{selected_customer_id}`  |  **สาขา:** `{branch}`")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💰 ยอดซื้อรวม", f"฿{total_spend:,.0f}")
    m2.metric("📦 จำนวนชิ้นรวม", f"{total_items:,.0f}")
    m3.metric("🏆 หมวดหมู่หลัก", str(top_cat)[:20])

    st.markdown("---")
    st.subheader("🛒 รายการสินค้าที่สั่งซื้อ")
    
    tab1, tab2 = st.tabs(["📊 สรุปรายการยอดนิยม (Grouped)", "📝 ประวัติละเอียด (All Logs)"])

    # --- Tab 1: แบบสรุป (แก้ไขตามสั่ง) ---
    with tab1:
        # Group รวมยอด
        summary_df = cust_df.groupby(
            [col_map['SKU'], col_map['ITEM'], col_map['UNIT'], col_map['GROUP']]
        ).agg(
            Total_Qty=(col_map['QTY'], 'sum'),
            Total_Amount=(col_map['AMOUNT'], 'sum'),
            Avg_Price=(col_map['PRICE'], 'mean')
        ).reset_index()
        
        # เรียงตามยอดเงิน
        summary_df = summary_df.sort_values(by='Total_Amount', ascending=False)
        
        # จัดลำดับ Column ใหม่: SKU / สินค้า / หน่วย / จำนวนรวม / ยอดเงินรวม / ราคาเฉลี่ย / หมวดหมู่
        summary_df = summary_df[[
            col_map['SKU'], 
            col_map['ITEM'], 
            col_map['UNIT'], 
            'Total_Qty', 
            'Total_Amount', 
            'Avg_Price', 
            col_map['GROUP']
        ]]

        st.dataframe(
            summary_df,
            column_config={
                col_map['SKU']: st.column_config.TextColumn("SKU", width="small"),
                col_map['ITEM']: "สินค้า",
                col_map['UNIT']: st.column_config.TextColumn("หน่วย", width="small"),
                "Total_Qty": st.column_config.NumberColumn("จำนวนรวม", format="%d"),
                "Total_Amount": st.column_config.ProgressColumn(
                    "ยอดเงินรวม", 
                    format="฿%.2f",
                    min_value=0,
                    max_value=int(summary_df['Total_Amount'].max())
                ),
                "Avg_Price": st.column_config.NumberColumn("ราคาเฉลี่ย", format="฿%.2f"),
                col_map['GROUP']: "หมวดหมู่",
            },
            use_container_width=True,
            hide_index=True,
            height=500
        )

    # --- Tab 2: แบบละเอียด (แก้ไขตามสั่ง) ---
    with tab2:
        # เพิ่ม SKU เป็น Column แรก
        detail_cols = [
            col_map['SKU'], 
            col_map['ITEM'], 
            col_map['GROUP'], 
            col_map['QTY'], 
            col_map['UNIT'], 
            col_map['PRICE'], 
            col_map['AMOUNT']
        ]
        detail_df = cust_df[detail_cols]
        
        st.dataframe(
            detail_df,
            column_config={
                col_map['SKU']: st.column_config.TextColumn("SKU", width="small"),
                col_map['ITEM']: "สินค้า",
                col_map['GROUP']: "หมวดหมู่",
                col_map['QTY']: st.column_config.NumberColumn("จำนวน", format="%d"),
                col_map['UNIT']: "หน่วย",
                col_map['PRICE']: st.column_config.NumberColumn("ราคา/หน่วย", format="฿%.2f"),
                col_map['AMOUNT']: st.column_config.NumberColumn("รวม", format="฿%.2f"),
            },
            use_container_width=True,
            hide_index=True
        )

else:
    st.info("👈 กรุณาค้นหารายชื่อจากเมนูด้านซ้าย")

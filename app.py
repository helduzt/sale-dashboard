import streamlit as st
import pandas as pd
import io

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Dashboard ข้อมูลการขาย", layout="wide")

# ฟังก์ชันโหลดข้อมูล
@st.cache_data
def load_data():
    file_path = "R6.201_202601.CSV"
    try:
        # ลองอ่านไฟล์ด้วยวิธีต่างๆ (เผื่อภาษาไทยเพี้ยน)
        return pd.read_csv(file_path)
    except:
        try:
            return pd.read_csv(file_path, encoding='cp874')
        except:
            return pd.read_csv(file_path, encoding='tis-620')

try:
    # 1. โหลดข้อมูล
    df = load_data()
    
    # แปลงวันที่ (ถ้าทำได้)
    if 'TRANDATE' in df.columns:
        df['TRANDATE'] = pd.to_datetime(df['TRANDATE'], dayfirst=True, errors='coerce')

    st.title("🛒 ระบบค้นหาและดูยอดขาย (Online)")

    # 2. สร้างแถบด้านข้าง (Sidebar) สำหรับ Filter
    st.sidebar.header("ตัวกรองข้อมูล")
    
    # เลือกสาขา
    if 'FNAME' in df.columns:
        branch_list = sorted(df['FNAME'].astype(str).unique())
        selected_branch = st.sidebar.multiselect("เลือกสาขา:", branch_list, default=branch_list)
    else:
        selected_branch = []

    # 3. ส่วนค้นหา (Search)
    search_txt = st.text_input("🔍 ค้นหา (พิมพ์ชื่อสินค้า, เลขบิล, หรือลูกค้า):", "")

    # 4. กรองข้อมูลตามที่เลือก
    filtered_df = df.copy()
    
    # กรองสาขา
    if selected_branch:
        filtered_df = filtered_df[filtered_df['FNAME'].isin(selected_branch)]
    
    # กรองคำค้นหา
    if search_txt:
        # ค้นหาในหลายๆ คอลัมน์พร้อมกัน
        mask = (
            filtered_df['ITEMNAME'].astype(str).str.contains(search_txt, case=False, na=False) |
            filtered_df['TRANNO'].astype(str).str.contains(search_txt, case=False, na=False) |
            filtered_df['CF_COMPANY'].astype(str).str.contains(search_txt, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # 5. แสดงผลลัพธ์
    # สรุปยอด
    c1, c2, c3 = st.columns(3)
    c1.metric("จำนวนรายการ", f"{len(filtered_df):,}")
    c2.metric("ยอดขายรวม (บาท)", f"{filtered_df['GRANDTOTAL'].sum():,.2f}")
    
    st.divider()
    
    # ตารางข้อมูล
    st.write("### รายละเอียดข้อมูล")
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")
    st.write("คำแนะนำ: ตรวจสอบว่าชื่อไฟล์ CSV ใน GitHub ตรงกับในโค้ดหรือไม่ (R6.201_202601.CSV)")

import streamlit as st
import pandas as pd
import os

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="PharmaSales Dashboard", layout="wide", page_icon="💊")

# --- 2. ฟังก์ชันโหลดข้อมูล (รองรับไฟล์ XLSX ของคุณ) ---
@st.cache_data
def load_data():
    # ระบุชื่อไฟล์ของคุณตรงนี้
    file_path = "bkk 11.2025 - 02.2026.XLSX"
    
    if not os.path.exists(file_path):
        return None, f"❌ หาไฟล์ไม่เจอ! กรุณาตรวจสอบว่าไฟล์ชื่อ '{file_path}' อยู่ในโฟลเดอร์เดียวกับ app.py หรือไม่"

    df = None
    error_log = ""

    # ความพยายามที่ 1: อ่านแบบ Excel (มาตรฐานของ .XLSX)
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
    except Exception as e_excel:
        error_log += f"Read Excel failed: {e_excel}\n"
        
        # ความพยายามที่ 2: อ่านแบบ CSV (เผื่อเป็นไฟล์ Text ที่ตั้งชื่อเป็น .XLSX)
        try:
            df = pd.read_csv(file_path)
        except Exception as e_csv:
            error_log += f"Read CSV failed: {e_csv}\n"

    if df is None:
        return None, f"❌ อ่านไฟล์ไม่ได้ทั้งแบบ Excel และ CSV\nError Log:\n{error_log}"

    # --- 3. Clean Data ---
    try:
        # ลบช่องว่างชื่อ Column (เผื่อมีวรรคหน้าหลัง)
        df.columns = df.columns.str.strip()
        
        # ตรวจสอบ Column สำคัญ
        required = ['PERSONID', 'FNAME', 'NAME', 'AMOUNT', 'ITEMNAME']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return None, f"❌ ไฟล์ขาด Column สำคัญ: {missing}\nColumn ที่เจอ: {list(df.columns)}"

        # แปลงเบอร์โทรให้เป็นข้อความ (ตัดตัวอักษรแปลกปลอม)
        df['PERSONID'] = df['PERSONID'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        
        # สร้างชื่อเต็ม
        df['Fullname'] = df['FNAME'].fillna('') + ' ' + df['LNAME'].fillna('')
        
        # แปลงตัวเลข (ลบ comma ถ้ามี)
        for col in ['BASEQUANTITY', 'PRICE', 'AMOUNT']:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
    except Exception as e:
        return None, f"❌ เกิดข้อผิดพลาดตอนแปลงข้อมูล: {e}"

    return df, None

# --- เรียกใช้งาน ---
df, error_msg = load_data()

if error_msg:
    st.error(error_msg)
    st.stop()

# ==========================================
# ส่วนแสดงผล UI (Tailwind Design)
# ==========================================

st.markdown("""
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<style>
    body { font-family: sans-serif; background-color: #f5f7f8; }
    .stApp { background-color: #f5f7f8; }
    /* ซ่อน Header มาตรฐานของ Streamlit เพื่อความสวยงาม */
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Sidebar ค้นหา ---
with st.sidebar:
    st.title("💊 Pharma Lookup")
    search_query = st.text_input("ค้นหาลูกค้า", placeholder="พิมพ์ชื่อ หรือ เบอร์โทร...")
    
    if 'selected_id' not in st.session_state:
        st.session_state['selected_id'] = None

    if search_query:
        # กรองข้อมูล (รองรับ Partial Match)
        mask = (
            df['PERSONID'].str.contains(search_query, na=False) | 
            df['FNAME'].str.contains(search_query, na=False) |
            df['LNAME'].str.contains(search_query, na=False)
        )
        results = df[mask]
        
        # ดึงรายชื่อที่ไม่ซ้ำ
        unique_customers = results[['PERSONID', 'Fullname', 'NAME']].drop_duplicates().head(20)
        
        if not unique_customers.empty:
            st.success(f"เจอ {len(unique_customers)} คน")
            for _, row in unique_customers.iterrows():
                # ปุ่มเลือก
                label = f"{row['Fullname']}\n({row['PERSONID']})"
                if st.button(label, key=f"btn_{row['PERSONID']}", use_container_width=True):
                    st.session_state['selected_id'] = row['PERSONID']
                    st.rerun()
        else:
            st.warning("ไม่พบข้อมูล")

    if st.button("รีเซ็ต", type="secondary"):
        st.session_state['selected_id'] = None
        st.rerun()

# --- Main Content ---
selected_id = st.session_state['selected_id']

if selected_id:
    # ดึงข้อมูลลูกค้าที่เลือก
    customer_data = df[df['PERSONID'] == selected_id]
    info = customer_data.iloc[0]
    
    # คำนวณสถิติ
    total_spend = customer_data['AMOUNT'].sum()
    total_items = customer_data['BASEQUANTITY'].sum()
    try:
        top_cat = customer_data['CF_ITEMGROUPL1_GROUPNAME'].mode()[0]
    except:
        top_cat = "-"

    # สร้างตาราง HTML
    rows_html = ""
    for _, row in customer_data.iterrows():
        cat_name = str(row.get('CF_ITEMGROUPL1_GROUPNAME', '-'))
        rows_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; hover:background-color: #f8fafc;">
            <td style="padding: 12px; color: #334155;">{row['ITEMNAME']}</td>
            <td style="padding: 12px;">
                <span style="background:#eff6ff; color:#1d4ed8; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600;">
                    {cat_name[:20]}
                </span>
            </td>
            <td style="padding: 12px; text-align:right; color: #475569;">{int(row['BASEQUANTITY'])} {row['CF_UNITNAME']}</td>
            <td style="padding: 12px; text-align:right; color: #475569;">{row['PRICE']:,.2f}</td>
            <td style="padding: 12px; text-align:right; font-weight:bold; color: #0f172a;">{row['AMOUNT']:,.2f}</td>
        </tr>
        """

    # แสดงผลหน้าจอ
    st.markdown(f"""
    <div style="max-width: 1000px; margin: 0 auto;">
        <div style="background:white; padding:24px; border-radius:16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 20px;">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div>
                    <h1 style="font-size: 28px; font-weight: 800; color: #1e293b; margin-bottom: 4px;">{info['Fullname']}</h1>
                    <div style="display:flex; gap:12px; color: #64748b; font-size: 14px;">
                        <span style="display:flex; align-items:center; gap:4px;"><span class="material-icons-outlined" style="font-size:16px;">phone</span> {info['PERSONID']}</span>
                        <span style="display:flex; align-items:center; gap:4px;"><span class="material-icons-outlined" style="font-size:16px;">store</span> {info['NAME']}</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <span style="background:#d1fae5; color:#047857; padding:4px 12px; border-radius:99px; font-size:12px; font-weight:bold;">Active Customer</span>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 24px;">
                <div style="background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0;">
                    <p style="font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase;">ยอดซื้อรวม (Total)</p>
                    <p style="font-size:24px; font-weight:800; color:#0f172a;">฿{total_spend:,.2f}</p>
                </div>
                <div style="background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0;">
                    <p style="font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase;">จำนวนรายการ</p>
                    <p style="font-size:24px; font-weight:800; color:#0f172a;">{int(total_items):,}</p>
                </div>
                <div style="background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0;">
                    <p style="font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase;">กลุ่มสินค้าหลัก</p>
                    <p style="font-size:18px; font-weight:800; color:#0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{top_cat}</p>
                </div>
            </div>
        </div>

        <div style="background:white; padding:24px; border-radius:16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <h3 style="font-size:18px; font-weight:bold; color:#1e293b; margin-bottom:16px; border-bottom:1px solid #e2e8f0; padding-bottom:12px;">
                ประวัติการสั่งซื้อ (Order History)
            </h3>
            <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse: collapse; font-size:14px;">
                    <thead style="background:#f8fafc; border-bottom: 2px solid #e2e8f0;">
                        <tr>
                            <th style="padding:12px; text-align:left; color:#64748b; font-weight:600;">สินค้า</th>
                            <th style="padding:12px; text-align:left; color:#64748b; font-weight:600;">หมวดหมู่</th>
                            <th style="padding:12px; text-align:right; color:#64748b; font-weight:600;">จำนวน</th>
                            <th style="padding:12px; text-align:right; color:#64748b; font-weight:600;">ราคา/หน่วย</th>
                            <th style="padding:12px; text-align:right; color:#64748b; font-weight:600;">รวม</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # หน้าจอตอนยังไม่เลือกใคร
    st.markdown("""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:60vh; color:#94a3b8;">
        <span class="material-icons-outlined" style="font-size:64px; margin-bottom:16px; color:#cbd5e1;">search</span>
        <h3 style="font-size:20px; font-weight:600; color:#64748b;">เริ่มใช้งานโดยการค้นหาลูกค้า</h3>
        <p style="font-size:14px;">พิมพ์ชื่อหรือเบอร์โทรที่แถบเมนูด้านซ้าย</p>
    </div>
    """, unsafe_allow_html=True)

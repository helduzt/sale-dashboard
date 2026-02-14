import streamlit as st
import pandas as pd
import os
import glob

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="PharmaSales Dashboard", layout="wide", page_icon="💊")

# --- 2. ฟังก์ชันค้นหาและโหลดไฟล์อัตโนมัติ ---
@st.cache_data
def load_data():
    # ค้นหาไฟล์ทั้งหมดที่เป็น .csv หรือ .xlsx ในโฟลเดอร์ปัจจุบัน
    possible_files = glob.glob("*.csv") + glob.glob("*.xlsx") + glob.glob("*.XLSX")
    
    if not possible_files:
        return None, "❌ ไม่พบไฟล์ข้อมูล (CSV หรือ Excel) ในโฟลเดอร์นี้เลย กรุณาวางไฟล์ข้อมูลไว้ที่เดียวกับ app.py"

    df = None
    loaded_file = ""
    error_log = ""

    # ลองอ่านทีละไฟล์ที่เจอ
    for file_path in possible_files:
        try:
            # ถ้าลงท้ายด้วย .csv หรือ .CSV
            if file_path.lower().endswith('.csv'):
                # ลองอ่านด้วย encoding ต่างๆ (เพื่อแก้ปัญหาภาษาไทย)
                for enc in ['utf-8', 'cp874', 'tis-620']:
                    try:
                        df = pd.read_csv(file_path, encoding=enc)
                        loaded_file = file_path
                        break
                    except:
                        continue
            
            # ถ้าลงท้ายด้วย .xlsx หรือ .XLSX
            elif file_path.lower().endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
                loaded_file = file_path

            # ถ้าอ่านสำเร็จ ให้หยุดวนลูป
            if df is not None:
                break
                
        except Exception as e:
            error_log += f"Failed to load {file_path}: {e}\n"
            continue

    if df is None:
        return None, f"❌ พยายามอ่านไฟล์เหล่านี้แล้วแต่ไม่สำเร็จ:\n{possible_files}\n\nError Log:\n{error_log}"

    # --- 3. Clean Data (จัดระเบียบข้อมูล) ---
    try:
        # ลบช่องว่างหัวท้ายชื่อ Column
        df.columns = df.columns.str.strip()
        
        # ตรวจสอบ Column สำคัญ
        required_cols = ['PERSONID', 'FNAME', 'NAME', 'AMOUNT', 'ITEMNAME']
        # เช็คว่ามี Column ครบไหม (แบบไม่สนตัวพิมพ์เล็กใหญ่)
        lower_cols = [c.lower() for c in df.columns]
        missing = [c for c in required_cols if c.lower() not in lower_cols]
        
        if missing:
            # ถ้าไม่เจอ ลอง map ชื่อ column ให้ฉลาดขึ้น
            # (เผื่อในไฟล์เขียน Person ID, First Name)
            pass 
        
        # แปลงเบอร์โทรเป็นข้อความ
        if 'PERSONID' in df.columns:
            df['PERSONID'] = df['PERSONID'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        
        # สร้างชื่อเต็ม
        if 'FNAME' in df.columns:
            df['Fullname'] = df['FNAME'].fillna('')
            if 'LNAME' in df.columns:
                df['Fullname'] += ' ' + df['LNAME'].fillna('')
        
        # แปลงตัวเลข
        for col in ['BASEQUANTITY', 'PRICE', 'AMOUNT']:
            if col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
    except Exception as e:
        return None, f"❌ เกิดข้อผิดพลาดตอนแปลงข้อมูล: {e}"

    return df, f"✅ โหลดข้อมูลสำเร็จจากไฟล์: {loaded_file}"

# --- เรียกใช้งานฟังก์ชัน ---
df, status_msg = load_data()

# แสดงสถานะการโหลด (ถ้า Error ให้หยุด)
if df is None:
    st.error(status_msg)
    st.stop()
else:
    # ซ่อนข้อความสำเร็จไว้ใน sidebar เพื่อไม่ให้รก
    with st.sidebar:
        st.success(status_msg)

# ==========================================
# ส่วนแสดงผล UI
# ==========================================

st.markdown("""
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<style>
    body { font-family: 'Sarabun', sans-serif; background-color: #f5f7f8; }
    .stApp { background-color: #f5f7f8; }
    /* ปรับแต่ง Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### 🔍 ค้นหาลูกค้า")
    search_query = st.text_input("พิมพ์ชื่อ หรือ เบอร์โทร...", placeholder="เช่น 081... หรือ สมชาย")
    
    if 'selected_id' not in st.session_state:
        st.session_state['selected_id'] = None

    if search_query:
        # กรองข้อมูล
        mask = pd.Series(False, index=df.index)
        if 'PERSONID' in df.columns:
            mask |= df['PERSONID'].str.contains(search_query, na=False)
        if 'FNAME' in df.columns:
            mask |= df['FNAME'].str.contains(search_query, na=False)
        if 'LNAME' in df.columns:
            mask |= df['LNAME'].str.contains(search_query, na=False)
            
        results = df[mask]
        
        # ดึงรายชื่อ
        unique_customers = results[['PERSONID', 'Fullname', 'NAME']].drop_duplicates().head(20)
        
        if not unique_customers.empty:
            st.info(f"พบ {len(unique_customers)} รายชื่อ")
            for _, row in unique_customers.iterrows():
                # ปุ่มเลือก
                label = f"{row['Fullname']}\n({row['PERSONID']})"
                if st.button(label, key=f"btn_{row['PERSONID']}", use_container_width=True):
                    st.session_state['selected_id'] = row['PERSONID']
                    st.rerun()
        else:
            st.warning("ไม่พบข้อมูล")
            
    if st.button("ล้างการค้นหา", type="secondary"):
        st.session_state['selected_id'] = None
        st.rerun()

# --- Main Content ---
selected_id = st.session_state['selected_id']

if selected_id:
    # กรองข้อมูลลูกค้า
    customer_data = df[df['PERSONID'] == selected_id]
    
    if not customer_data.empty:
        info = customer_data.iloc[0]
        
        # คำนวณยอด
        total_spend = customer_data['AMOUNT'].sum() if 'AMOUNT' in df.columns else 0
        total_items = customer_data['BASEQUANTITY'].sum() if 'BASEQUANTITY' in df.columns else 0
        
        top_cat = "-"
        if 'CF_ITEMGROUPL1_GROUPNAME' in customer_data.columns:
            try:
                top_cat = customer_data['CF_ITEMGROUPL1_GROUPNAME'].mode()[0]
            except:
                pass

        # สร้างตาราง HTML
        rows_html = ""
        for _, row in customer_data.iterrows():
            item_name = row.get('ITEMNAME', '-')
            cat_name = str(row.get('CF_ITEMGROUPL1_GROUPNAME', '-'))[:20]
            qty = row.get('BASEQUANTITY', 0)
            unit = row.get('CF_UNITNAME', '')
            price = row.get('PRICE', 0)
            amount = row.get('AMOUNT', 0)
            
            rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px; color: #334155;">{item_name}</td>
                <td style="padding: 12px;">
                    <span style="background:#eff6ff; color:#1d4ed8; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:600;">
                        {cat_name}
                    </span>
                </td>
                <td style="padding: 12px; text-align:right; color: #475569;">{int(qty)} {unit}</td>
                <td style="padding: 12px; text-align:right; color: #475569;">{price:,.2f}</td>
                <td style="padding: 12px; text-align:right; font-weight:bold; color: #0f172a;">{amount:,.2f}</td>
            </tr>
            """

        # แสดงผล UI
        st.markdown(f"""
        <div style="max-width: 1000px; margin: 0 auto; padding-top: 20px;">
            <div style="background:white; padding:24px; border-radius:16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 20px;">
                <div style="display:flex; justify-content:space-between; align-items:start;">
                    <div>
                        <h1 style="font-size: 28px; font-weight: 800; color: #1e293b; margin-bottom: 4px;">{info.get('Fullname', 'Unknown')}</h1>
                        <div style="display:flex; gap:12px; color: #64748b; font-size: 14px;">
                            <span style="display:flex; align-items:center; gap:4px;"><span class="material-icons-outlined" style="font-size:16px;">phone</span> {info.get('PERSONID', '-')}</span>
                            <span style="display:flex; align-items:center; gap:4px;"><span class="material-icons-outlined" style="font-size:16px;">store</span> {info.get('NAME', '-')}</span>
                        </div>
                    </div>
                    <div>
                        <span style="background:#d1fae5; color:#047857; padding:4px 12px; border-radius:99px; font-size:12px; font-weight:bold;">Active</span>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 24px;">
                    <div style="background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0;">
                        <p style="font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase;">ยอดซื้อรวม (Total Spend)</p>
                        <p style="font-size:24px; font-weight:800; color:#0f172a;">฿{total_spend:,.2f}</p>
                    </div>
                    <div style="background:#f8fafc; padding:16px; border-radius:12px; border:1px solid #e2e8f0;">
                        <p style="font-size:12px; color:#64748b; font-weight:600; text-transform:uppercase;">จำนวนรายการ (Items)</p>
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
                    รายการสินค้าที่สั่งซื้อ (Order History)
                </h3>
                <div style="overflow-x:auto;">
                    <table style="width:100%; border-collapse: collapse;

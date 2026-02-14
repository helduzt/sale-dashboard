import streamlit as st
import pandas as pd

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบค้นหาลูกค้า", layout="wide", page_icon="📂")

# CSS ตกแต่งให้สวยงาม
st.markdown("""
<style>
    .stApp { background-color: #f0f2f6; }
    div[data-testid="stMetricValue"] { font-size: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ส่วนหัวและตัวอัปโหลดไฟล์ ---
st.title("📂 ระบบค้นหาประวัติการซื้อ (แบบอัปโหลดเอง)")
st.markdown("---")

# สร้างปุ่มอัปโหลดไฟล์ตรงนี้ (รองรับทั้ง CSV และ Excel)
uploaded_file = st.file_uploader("1. กรุณาลากไฟล์ข้อมูล (CSV หรือ Excel) มาวางที่นี่", type=['csv', 'xlsx', 'xls'])

# --- 3. ฟังก์ชันโหลดข้อมูล ---
@st.cache_data
def load_data(file):
    df = None
    # ถ้าเป็นไฟล์ CSV
    if file.name.lower().endswith('.csv'):
        # ลองอ่านทีละภาษา (กันภาษาต่างดาว)
        encodings = ['utf-8', 'cp874', 'tis-620', 'utf-16']
        for enc in encodings:
            try:
                file.seek(0) # รีเซ็ตไฟล์ไปที่จุดเริ่มต้น
                df = pd.read_csv(file, encoding=enc)
                break
            except:
                continue
                
    # ถ้าเป็นไฟล์ Excel
    else:
        try:
            df = pd.read_excel(file)
        except Exception as e:
            st.error(f"อ่านไฟล์ Excel ไม่ได้: {e}")
            return None

    if df is None:
        return None

    # --- Clean Data ---
    try:
        # ลบช่องว่างชื่อ Column
        df.columns = df.columns.str.strip()
        
        # แปลงเบอร์โทร (PERSONID) ให้เป็นข้อความ
        # หา column ที่น่าจะเป็นเบอร์โทร (ที่มีคำว่า ID หรือ PERSON)
        id_col = [c for c in df.columns if 'PERSON' in c or 'ID' in c][0]
        df['Search_ID'] = df[id_col].astype(str).str.replace(r'[^0-9]', '', regex=True)
        
        # หา column ชื่อ (FNAME)
        name_col = [c for c in df.columns if 'NAME' in c or 'FNAME' in c][0]
        df['Search_Name'] = df[name_col].astype(str).fillna('')
        
        # รวมชื่อนามสกุล (ถ้ามี LNAME)
        lname_col = [c for c in df.columns if 'LNAME' in c]
        if lname_col:
            df['Search_Name'] += ' ' + df[lname_col[0]].astype(str).fillna('')

    except Exception as e:
        st.error(f"❌ รูปแบบไฟล์ไม่ถูกต้อง: {e}")
        return None

    return df

# --- 4. การทำงานหลัก ---
if uploaded_file is not None:
    # โหลดข้อมูล
    df = load_data(uploaded_file)
    
    if df is not None:
        st.success(f"✅ โหลดข้อมูลสำเร็จ! พบ {len(df):,} รายการ")
        
        # แบ่งหน้าจอ ซ้าย(ค้นหา) ขวา(แสดงผล)
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("🔍 2. ค้นหาลูกค้า")
            search_text = st.text_input("พิมพ์ชื่อ หรือ เบอร์โทร", placeholder="เช่น 081...")
            
            selected_person = None
            
            if search_text:
                # กรองข้อมูล
                mask = (df['Search_ID'].str.contains(search_text, na=False)) | \
                       (df['Search_Name'].str.contains(search_text, na=False))
                results = df[mask]
                
                # เอารายชื่อที่ไม่ซ้ำมาแสดง
                people = results[['Search_ID', 'Search_Name']].drop_duplicates()
                
                if not people.empty:
                    st.info(f"พบ {len(people)} คน")
                    # สร้าง Radio Button ให้เลือก
                    choice = st.radio(
                        "ผลการค้นหา (คลิกเพื่อดูข้อมูล)",
                        people.apply(lambda x: f"{x['Search_Name']} ({x['Search_ID']})", axis=1)
                    )
                    # แกะ ID จากตัวเลือก
                    selected_id = choice.split('(')[-1].replace(')', '')
                    selected_person = selected_id
                else:
                    st.warning("ไม่พบข้อมูล")

        with col2:
            st.subheader("📊 3. ประวัติการซื้อ")
            
            if selected_person:
                # ดึงข้อมูลคนนั้น
                history = df[df['Search_ID'] == selected_person]
                
                # แสดงข้อมูลส่วนตัว
                info = history.iloc[0]
                st.markdown(f"**ลูกค้า:** {info['Search_Name']}")
                st.markdown(f"**เบอร์:** {selected_person}")
                
                # คำนวณยอดรวม (หา column ที่เป็นตัวเลขยอดเงิน)
                amount_col = [c for c in df.columns if 'AMOUNT' in c or 'PRICE' in c or 'TOTAL' in c]
                if amount_col:
                    total = history[amount_col[-1]].sum()
                    st.metric("💰 ยอดซื้อรวมทั้งหมด", f"฿{total:,.2f}")
                
                # แสดงตาราง
                st.dataframe(history, use_container_width=True)
            else:
                st.info("👈 กรุณาเลือกรายชื่อลูกค้าจากด้านซ้าย")

    else:
        st.error("อ่านไฟล์ไม่สำเร็จ ลอง Save ไฟล์เป็น CSV (UTF-8) แล้วอัปโหลดใหม่ครับ")

else:
    # ตอนยังไม่อัปโหลดไฟล์
    st.info("👆 กรุณาอัปโหลดไฟล์ข้อมูลเพื่อเริ่มต้น")

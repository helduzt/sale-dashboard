import streamlit as st
import pandas as pd
import os

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบค้นหาลูกค้า", layout="wide")

# 2. ฟังก์ชันโหลดไฟล์ที่ทนทานที่สุด
@st.cache_data
def load_data():
    file_path = "data.csv" # เปลี่ยนชื่อไฟล์ให้ง่าย
    
    # 2.1 เช็คว่ามีไฟล์ไหม
    if not os.path.exists(file_path):
        return None, f"❌ หาไฟล์ '{file_path}' ไม่เจอ! กรุณาเปลี่ยนชื่อไฟล์จริงเป็น data.csv แล้ววางไว้ที่เดียวกับ app.py"

    df = None
    success_msg = ""
    
    # 2.2 ลองอ่านด้วย 3 รหัสภาษาไทยยอดฮิต
    encodings = ['utf-8', 'cp874', 'tis-620', 'utf-16']
    
    for enc in encodings:
        try:
            # ลองอ่านแบบ CSV
            temp_df = pd.read_csv(file_path, encoding=enc)
            
            # เช็คว่าอ่านรู้เรื่องไหม (ต้องมี column ที่ชื่อมีคำว่า 'PERSON' หรือ 'NAME')
            cols = "".join(temp_df.columns).upper()
            if "PERSON" in cols or "NAME" in cols or "ITEM" in cols:
                df = temp_df
                success_msg = f"อ่านไฟล์สำเร็จด้วยรหัส: {enc}"
                break
        except:
            continue
            
    # 2.3 ถ้าอ่าน CSV ไม่ได้ ลองอ่านแบบ Excel (เผื่อเป็นไฟล์ Excel ปลอมตัวมา)
    if df is None:
        try:
            df = pd.read_excel(file_path)
            success_msg = "อ่านไฟล์สำเร็จแบบ Excel"
        except:
            pass

    # ถ้ายังไม่ได้อีก ยอมแพ้
    if df is None:
        return None, "❌ อ่านไฟล์ไม่ได้เลย กรุณาลองเปิดไฟล์ด้วย Excel แล้ว Save As เป็น 'CSV UTF-8'"

    # 3. จัดการข้อมูล (Cleaning)
    try:
        # ลบช่องว่างชื่อ Column
        df.columns = df.columns.str.strip()
        
        # แปลงชื่อ Column ให้เป็นมาตรฐาน (เผื่อชื่อไม่ตรงเป๊ะ)
        # เช่น Person ID -> PERSONID
        df.columns = df.columns.str.upper().str.replace(' ', '').str.replace('_', '')
        
        # หาชื่อ Column จริงๆ ในไฟล์ที่โหลดมา
        col_map = {
            'ID': [c for c in df.columns if 'PERSON' in c or 'TEL' in c or 'ID' in c][0], # เดาว่าช่องไหนคือ ID
            'NAME': [c for c in df.columns if 'FNAME' in c or 'NAME' in c][0],
            'ITEM': [c for c in df.columns if 'ITEMNAME' in c or 'PRODUCT' in c][0],
            'AMOUNT': [c for c in df.columns if 'AMOUNT' in c or 'PRICE' in c or 'TOTAL' in c][-1] # เอาอันหลังสุดมักจะเป็นราคารวม
        }
        
        # เก็บ Column ที่จะใช้
        df['Display_ID'] = df[col_map['ID']].astype(str).str.replace(r'\.0$', '', regex=True) # ลบ .0 ทิ้ง
        df['Display_Name'] = df[col_map['NAME']].astype(str)
        df['Display_Item'] = df[col_map['ITEM']].astype(str)
        df['Display_Amount'] = pd.to_numeric(df[col_map['AMOUNT']].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # แถม Column อื่นๆ ถ้ามี
        if 'CFUNITNAME' in df.columns: df['Display_Unit'] = df['CFUNITNAME']
        else: df['Display_Unit'] = ""
            
        if 'BASEQUANTITY' in df.columns: df['Display_Qty'] = df['BASEQUANTITY']
        else: df['Display_Qty'] = 0

    except Exception as e:
        return None, f"❌ ข้อมูลในไฟล์ไม่ตรงรูปแบบ: {e}\nColumn ที่เจอ: {list(df.columns)}"

    return df, success_msg

# --- เริ่มรัน ---
df, msg = load_data()

if df is None:
    st.error(msg)
    st.stop()

# --- ส่วนแสดงผล ---
st.title("🔎 ค้นหาประวัติการซื้อ")
st.caption(msg) # บอก User ว่าโหลดไฟล์แบบไหนมา

search = st.text_input("พิมพ์ชื่อ หรือ เบอร์โทรลูกค้า", placeholder="เช่น 081...")

if search:
    # กรองข้อมูล
    results = df[
        df['Display_ID'].str.contains(search, na=False) | 
        df['Display_Name'].str.contains(search, na=False) 
    ]
    
    if not results.empty:
        # สรุปรายชื่อคนที่ไม่ซ้ำ
        people = results[['Display_ID', 'Display_Name']].drop_duplicates()
        
        st.write(f"พบ {len(people)} คน:")
        
        for i, person in people.iterrows():
            with st.expander(f"👤 {person['Display_Name']} (เบอร์: {person['Display_ID']})"):
                # ดึงข้อมูลการซื้อของคนนี้
                history = df[df['Display_ID'] == person['Display_ID']]
                
                # แสดงยอดรวม
                total = history['Display_Amount'].sum()
                st.metric("ยอดซื้อรวมทั้งหมด", f"฿{total:,.2f}")
                
                # แสดงตาราง
                st.dataframe(
                    history[['Display_Item', 'Display_Qty', 'Display_Unit', 'Display_Amount']],
                    column_config={
                        "Display_Item": "สินค้า",
                        "Display_Qty": "จำนวน",
                        "Display_Unit": "หน่วย",
                        "Display_Amount": "ราคา"
                    },
                    use_container_width=True,
                    hide_index=True
                )
    else:
        st.warning("ไม่พบข้อมูล")

import streamlit as st
import pandas as pd
import glob
import os

# --- 1. ตั้งค่าหน้าเว็บ (Config) ---
st.set_page_config(page_title="PharmaSales Dashboard", layout="wide", page_icon="💊")

# --- 2. ฟังก์ชันโหลดไฟล์ Excel อัตโนมัติ (จาก GitHub) ---
@st.cache_data
def load_data():
    # ค้นหาไฟล์ Excel ทุกไฟล์ในโฟลเดอร์นี้ (.xlsx หรือ .XLSX)
    excel_files = glob.glob("*.xlsx") + glob.glob("*.XLSX")
    
    if not excel_files:
        return None, "❌ ไม่พบไฟล์ Excel (.xlsx) ใน Repository นี้ กรุณาอัปโหลดไฟล์ข้อมูลเข้า GitHub"
    
    # เอาไฟล์แรกที่เจอมาใช้
    target_file = excel_files[0]
    
    try:
        # อ่านไฟล์ Excel
        df = pd.read_excel(target_file, engine='openpyxl')
        
        # --- Clean Data (จัดการข้อมูลให้สะอาด) ---
        # 1. ลบช่องว่างหัวท้ายชื่อ Column (เผื่อมีวรรคเกิน)
        df.columns = df.columns.str.strip()
        
        # 2. Map ชื่อ Column (จับคู่ชื่อใน Excel เข้ากับตัวแปร)
        # ปรับแก้ตรงนี้ได้ถ้าชื่อ Column ใน Excel เปลี่ยน
        col_map = {
            'ID': 'PERSONID',       # รหัสลูกค้า/เบอร์โทร
            'FNAME': 'FNAME',       # ชื่อ
            'LNAME': 'LNAME',       # นามสกุล
            'BRANCH': 'NAME',       # สาขา
            'ITEM': 'ITEMNAME',     # ชื่อสินค้า
            'QTY': 'BASEQUANTITY',  # จำนวน
            'PRICE': 'PRICE',       # ราคาต่อหน่วย
            'AMOUNT': 'AMOUNT',     # ราคารวม
            'GROUP': 'CF_ITEMGROUPL1_GROUPNAME', # กลุ่มสินค้า
            'UNIT': 'CF_UNITNAME'   # หน่วยนับ
        }
        
        # ตรวจสอบว่ามี Column ครบไหม
        missing_cols = [v for k, v in col_map.items() if v not in df.columns]
        if missing_cols:
            # ถ้าไม่เจอชื่อเป๊ะๆ ให้ลองเดา (เผื่อชื่อเปลี่ยนนิดหน่อย)
            pass 

        # 3. สร้าง Column สำหรับค้นหา (Search_ID, Search_Name)
        # แปลงเบอร์โทรเป็นข้อความล้วน (ตัดขีด ตัดวรรค)
        if col_map['ID'] in df.columns:
            df['Search_ID'] = df[col_map['ID']].astype(str).str.replace(r'[^0-9]', '', regex=True)
        else:
            df['Search_ID'] = '0'
            
        # รวมชื่อ-นามสกุล
        f = df[col_map['FNAME']].fillna('') if col_map['FNAME'] in df.columns else ''
        l = df[col_map['LNAME']].fillna('') if col_map['LNAME'] in df.columns else ''
        df['Search_Name'] = f.astype(str) + ' ' + l.astype(str)

        return df, col_map, target_file

    except Exception as e:
        return None, f"อ่านไฟล์ {target_file} ไม่สำเร็จ: {str(e)}", target_file

# โหลดข้อมูลเก็บไว้
df, col_map, loaded_filename = load_data()

# --- 3. Inject HTML/CSS (ส่วนดีไซน์ Tailwind) ---
st.markdown("""
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<style>
    /* Override Streamlit Defaults */
    .stApp { background-color: #f5f7f8; font-family: 'Manrope', 'Noto Sans Thai', sans-serif; }
    header { visibility: hidden; } /* ซ่อนแถบด้านบน */
    .block-container { padding: 0 !important; max-width: 100%; }
    
    /* ปรับแต่ง Sidebar */
    section[data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e2e8f0; }
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# ถ้าโหลดข้อมูลไม่ได้ ให้แจ้งเตือนและหยุด
if df is None:
    st.error(col_map) # col_map จะเก็บ error message ในกรณีนี้
    st.stop()

# --- 4. Sidebar (ส่วนค้นหา) ---
with st.sidebar:
    # Logo Area
    st.markdown(f"""
    <div class="flex items-center gap-3 px-4 mb-8">
        <div class="bg-blue-500/10 p-2 rounded-lg">
            <span class="material-icons-outlined text-blue-500 text-2xl">medication</span>
        </div>
        <div>
            <h1 class="font-bold text-lg tracking-tight leading-none text-slate-800">PharmaSales</h1>
            <p class="text-xs text-slate-500">Data: {loaded_filename}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Input Box
    search_query = st.text_input("🔎 ค้นหาลูกค้า", placeholder="พิมพ์เบอร์โทร หรือ ชื่อ...")
    
    selected_customer_id = None
    
    # Logic การค้นหา
    if search_query:
        # กรองข้อมูล (Partial Match)
        mask = (df['Search_ID'].str.contains(search_query, na=False)) | \
               (df['Search_Name'].str.contains(search_query, na=False))
        results = df[mask]
        
        # ดึงรายชื่อคนที่ไม่ซ้ำ (เอาแค่ 50 คนแรกกันค้าง)
        unique_customers = results[['Search_ID', 'Search_Name']].drop_duplicates().head(50)
        
        st.markdown(f"<p class='px-4 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2'>ผลลัพธ์ ({len(unique_customers)})</p>", unsafe_allow_html=True)
        
        # สร้างปุ่มกดเลือก
        for _, row in unique_customers.iterrows():
            # ใช้ Streamlit Button แต่แต่งชื่อให้ดูดี
            btn_label = f"{row['Search_Name']}\n{row['Search_ID']}"
            if st.button(btn_label, key=row['Search_ID'], use_container_width=True):
                st.session_state['selected_id'] = row['Search_ID']
                st.rerun()

# --- 5. Main Content (ส่วนแสดงผล HTML) ---

# ตรวจสอบว่ามีการเลือก ID หรือยัง
current_id = st.session_state.get('selected_id')

if current_id:
    # กรองข้อมูลลูกค้าคนนั้น
    customer_data = df[df['Search_ID'] == current_id]
    
    # เตรียมข้อมูลสำหรับใส่ใน HTML
    info = customer_data.iloc[0]
    branch_name = info[col_map['BRANCH']] if col_map['BRANCH'] in df.columns else '-'
    
    # คำนวณตัวเลข
    total_spend = customer_data[col_map['AMOUNT']].sum()
    total_items = customer_data[col_map['QTY']].sum()
    
    try:
        top_cat = customer_data[col_map['GROUP']].mode()[0]
    except:
        top_cat = "-"

    # สร้าง HTML ของตารางรายการสินค้า (Loop)
    table_rows_html = ""
    for _, row in customer_data.iterrows():
        item_name = row.get(col_map['ITEM'], '-')
        group_name = str(row.get(col_map['GROUP'], '-'))[:20] # ตัดคำยาวเกิน
        qty = row.get(col_map['QTY'], 0)
        unit = row.get(col_map['UNIT'], '')
        price = row.get(col_map['PRICE'], 0)
        amount = row.get(col_map['AMOUNT'], 0)
        
        table_rows_html += f"""
        <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0">
            <td class="px-6 py-4 font-medium text-slate-800">{item_name}</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">
                    {group_name}
                </span>
            </td>
            <td class="px-6 py-4 text-right text-slate-600">{qty:,.0f} {unit}</td>
            <td class="px-6 py-4 text-right text-slate-600">฿{price:,.2f}</td>
            <td class="px-6 py-4 text-right font-bold text-slate-800">฿{amount:,.2f}</td>
        </tr>
        """

    # --- HTML Template (ดีไซน์หลัก) ---
    # ใช้ f-string ใส่ตัวแปร Python ลงไปใน HTML
    main_html = f"""
    <div class="flex-1 min-h-screen bg-[#f5f7f8] p-6 xl:p-8 relative">
        
        <div class="absolute top-0 right-0 w-96 h-96 bg-blue-400/5 rounded-full blur-3xl -z-10 pointer-events-none translate-x-1/2 -translate-y-1/2"></div>

        <div class="max-w-6xl mx-auto space-y-6">
            
            <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div class="flex items-start md:items-center gap-5">
                    <div class="h-20 w-20 rounded-2xl bg-gradient-to-br from-[#0da2e7] to-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 shrink-0">
                        <span class="text-3xl font-bold">{str(info['Search_Name'])[0]}</span>
                    </div>
                    <div>
                        <div class="flex items-center gap-3 mb-1">
                            <h2 class="text-2xl font-bold text-slate-800">{info['Search_Name']}</h2>
                            <span class="bg-emerald-100 text-emerald-700 text-xs px-2.5 py-0.5 rounded-full font-bold border border-emerald-200">Active Customer</span>
                        </div>
                        <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 text-slate-500">
                            <div class="flex items-center gap-1.5">
                                <span class="material-icons-outlined text-lg">call</span>
                                <span class="font-medium text-slate-700">{info['Search_ID']}</span>
                            </div>
                            <div class="hidden sm:block w-1 h-1 bg-slate-300 rounded-full"></div>
                            <div class="flex items-center gap-1.5">
                                <span class="material-icons-outlined text-lg">store</span>
                                <span class="text-sm">{branch_name}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden group">
                    <div class="absolute right-0 top-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                        <span class="material-icons-outlined text-6xl text-[#0da2e7]">payments</span>
                    </div>
                    <p class="text-sm text-slate-500 font-medium mb-1">ยอดซื้อรวม (Total Spend)</p>
                    <h3 class="text-3xl font-bold text-slate-800 mb-2">฿{total_spend:,.2f}</h3>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden group">
                    <div class="absolute right-0 top-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                        <span class="material-icons-outlined text-6xl text-[#0da2e7]">shopping_bag</span>
                    </div>
                    <p class="text-sm text-slate-500 font-medium mb-1">จำนวนรายการ (Items)</p>
                    <h3 class="text-3xl font-bold text-slate-800 mb-2">{total_items:,.0f}</h3>
                </div>
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 relative overflow-hidden group">
                    <div class="absolute right-0 top-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                        <span class="material-icons-outlined text-6xl text-[#0da2e7]">category</span>
                    </div>
                    <p class="text-sm text-slate-500 font-medium mb-1">กลุ่มสินค้าหลัก (Top Category)</p>
                    <h3 class="text-xl font-bold text-slate-800 mb-2 truncate">{top_cat}</h3>
                </div>
            </div>

            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 flex flex-col min-h-[400px]">
                <div class="p-6 border-b border-slate-100">
                    <h3 class="text-lg font-bold text-slate-800">ประวัติการสั่งซื้อ (Order History)</h3>
                    <p class="text-sm text-slate-500">รายการสินค้าทั้งหมดที่ลูกค้าเคยสั่งซื้อ</p>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead class="bg-slate-50 sticky top-0">
                            <tr>
                                <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">สินค้า</th>
                                <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">กลุ่ม</th>
                                <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">จำนวน</th>
                                <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">ราคา/หน่วย</th>
                                <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">ยอดรวม</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 text-sm">
                            {table_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
    """
    
    # Render หน้าเว็บออกมา
    st.markdown(main_html, unsafe_allow_html=True)

else:
    # --- หน้า Welcome (กรณีเปิดเว็บมายังไม่เลือกใคร) ---
    st.markdown("""
    <div class="flex flex-col items-center justify-center h-screen bg-[#f5f7f8] text-slate-400">
        <div class="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 text-center max-w-md">
            <span class="material-icons-outlined text-6xl mb-4 text-[#0da2e7]/50">manage_search</span>
            <h3 class="text-xl font-bold text-slate-700 mb-2">Customer Lookup System</h3>
            <p class="text-sm text-slate-500">กรุณาพิมพ์ชื่อ หรือ เบอร์โทรศัพท์ ที่เมนูด้านซ้าย<br>เพื่อดูข้อมูลและประวัติการสั่งซื้อ</p>
            <div class="mt-4 text-xs text-slate-400 bg-slate-50 p-2 rounded">
                สถานะ: พร้อมใช้งาน (Data Loaded from GitHub)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

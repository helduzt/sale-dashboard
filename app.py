import streamlit as st
import pandas as pd

# ตั้งค่าหน้าเว็บให้กว้างเต็มจอ
st.set_page_config(page_title="PharmaSales Dashboard", layout="wide", page_icon="💊")

# --- 1. โหลดและเตรียมข้อมูล ---
@st.cache_data
def load_data():
    # อ่านไฟล์ CSV (สมมติชื่อไฟล์ data.csv ถ้าชื่ออื่นให้แก้ตรงนี้)
    df = pd.read_csv("data.csv") 
    
    # แปลงข้อมูลเบื้องต้น
    df['PERSONID'] = df['PERSONID'].astype(str).str.replace(r'[^0-9]', '', regex=True) # คลีนเบอร์โทร
    df['Fullname'] = df['FNAME'].fillna('') + ' ' + df['LNAME'].fillna('')
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("ไม่พบไฟล์ data.csv กรุณาอัปโหลดไฟล์ข้อมูลเข้าสู่ GitHub หรือ Folder เดียวกัน")
    st.stop()

# --- 2. ส่วน Sidebar (ใช้ Streamlit Widget แทน HTML Input เพื่อให้ค้นหาได้จริง) ---
with st.sidebar:
    st.title("🔍 ค้นหาลูกค้า")
    search_query = st.text_input("พิมพ์ชื่อ หรือ เบอร์โทร...", placeholder="เช่น 0812345678 หรือ สมชาย")
    
    selected_customer_id = None
    
    if search_query:
        # Logic การค้นหา (หาทั้งชื่อและเบอร์)
        results = df[
            df['PERSONID'].str.contains(search_query, na=False) | 
            df['FNAME'].str.contains(search_query, na=False) |
            df['LNAME'].str.contains(search_query, na=False)
        ]
        
        # ดึงรายชื่อคนที่ไม่ซ้ำกันมาแสดง
        unique_customers = results[['PERSONID', 'Fullname', 'NAME']].drop_duplicates()
        
        if not unique_customers.empty:
            st.write(f"พบ {len(unique_customers)} รายชื่อ:")
            # สร้างปุ่มเลือกรายชื่อ
            for index, row in unique_customers.iterrows():
                # สร้าง Label สวยๆ บนปุ่ม
                label = f"{row['Fullname']}\n({row['PERSONID']}) - {row['NAME']}"
                if st.button(label, key=row['PERSONID'], use_container_width=True):
                    selected_customer_id = row['PERSONID']
                    st.session_state['selected_id'] = row['PERSONID']
        else:
            st.warning("ไม่พบข้อมูล")

    # ตรวจสอบว่ามีการเลือก ID ค้างไว้ใน Session หรือไม่ (เพื่อให้หน้าไม่รีเฟรชหาย)
    if 'selected_id' in st.session_state:
        selected_customer_id = st.session_state['selected_id']

# --- 3. ส่วน Main Content (ใช้ HTML/Tailwind เดิมมา Render ข้อมูลจริง) ---

# Inject Tailwind CSS และ Font
st.markdown("""
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700&family=Noto+Sans+Thai:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Outlined" rel="stylesheet"/>
<style>
    body { font-family: 'Manrope', 'Noto Sans Thai', sans-serif; background-color: #f5f7f8; }
    .stApp { background-color: #f5f7f8; }
</style>
""", unsafe_allow_html=True)

if selected_customer_id:
    # กรองข้อมูลเฉพาะคนที่เลือก
    customer_data = df[df['PERSONID'] == selected_customer_id]
    
    # คำนวณ Metrics
    info = customer_data.iloc[0] # ข้อมูลส่วนตัว (เอาแถวแรก)
    total_spend = customer_data['AMOUNT'].sum()
    total_items = customer_data['BASEQUANTITY'].sum()
    
    # หาหมวดหมู่ที่ซื้อบ่อยสุด
    try:
        top_category = customer_data['CF_ITEMGROUPL1_GROUPNAME'].mode()[0]
    except:
        top_category = "N/A"

    # สร้าง HTML Table Rows จากข้อมูลจริง
    table_rows_html = ""
    for index, row in customer_data.iterrows():
        table_rows_html += f"""
        <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
            <td class="px-6 py-4 font-medium text-slate-800">{row['ITEMNAME']}</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {str(row['CF_ITEMGROUPL1_GROUPNAME'])[:20]}
                </span>
            </td>
            <td class="px-6 py-4 text-right text-slate-600">{int(row['BASEQUANTITY'])} {row['CF_UNITNAME']}</td>
            <td class="px-6 py-4 text-right text-slate-600">฿{row['PRICE']:,.2f}</td>
            <td class="px-6 py-4 text-right font-bold text-slate-800">฿{row['AMOUNT']:,.2f}</td>
        </tr>
        """

    # --- ส่วน HTML Template ที่ Mapping ตัวแปร Python ({...}) ลงไป ---
    html_content = f"""
    <div class="max-w-6xl mx-auto space-y-6 pt-2">
        <div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div class="flex items-start md:items-center gap-5">
                <div class="h-20 w-20 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white shadow-lg shrink-0">
                    <span class="text-3xl font-bold">{info['FNAME'][0] if pd.notna(info['FNAME']) else '?'}</span>
                </div>
                <div>
                    <div class="flex items-center gap-3 mb-1">
                        <h2 class="text-2xl font-bold text-slate-800">{info['Fullname']}</h2>
                        <span class="bg-emerald-100 text-emerald-700 text-xs px-2.5 py-0.5 rounded-full font-bold border border-emerald-200">Customer</span>
                    </div>
                    <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 text-slate-500">
                        <div class="flex items-center gap-1.5">
                            <span class="material-icons-outlined text-lg">call</span>
                            <span class="font-medium text-slate-700">{info['PERSONID']}</span>
                        </div>
                        <div class="hidden sm:block w-1 h-1 bg-slate-300 rounded-full"></div>
                        <div class="flex items-center gap-1.5">
                            <span class="material-icons-outlined text-lg">store</span>
                            <span class="text-sm">{info['NAME']}</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="text-right">
                 <button class="px-4 py-2 rounded-lg bg-blue-500 text-white font-medium shadow-md">
                    Member Info
                 </button>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 relative overflow-hidden">
                <div class="absolute right-0 top-0 p-4 opacity-5">
                    <span class="material-icons-outlined text-6xl text-blue-500">payments</span>
                </div>
                <p class="text-sm text-slate-500 font-medium mb-1">ยอดซื้อรวม (Total Spend)</p>
                <h3 class="text-3xl font-bold text-slate-800 mb-2">฿{total_spend:,.2f}</h3>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 relative overflow-hidden">
                <div class="absolute right-0 top-0 p-4 opacity-5">
                    <span class="material-icons-outlined text-6xl text-blue-500">shopping_bag</span>
                </div>
                <p class="text-sm text-slate-500 font-medium mb-1">จำนวนสินค้าที่ซื้อ (Items)</p>
                <h3 class="text-3xl font-bold text-slate-800 mb-2">{int(total_items):,}</h3>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 relative overflow-hidden">
                <div class="absolute right-0 top-0 p-4 opacity-5">
                    <span class="material-icons-outlined text-6xl text-blue-500">category</span>
                </div>
                <p class="text-sm text-slate-500 font-medium mb-1">กลุ่มสินค้าที่ซื้อบ่อย</p>
                <h3 class="text-xl font-bold text-slate-800 mb-2 truncate">{top_category}</h3>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col">
            <div class="p-6 border-b border-slate-100 flex justify-between items-center">
                <div>
                    <h3 class="text-lg font-bold text-slate-800">ประวัติการสั่งซื้อ (Purchase History)</h3>
                    <p class="text-sm text-slate-500">รายการสินค้าทั้งหมดที่ลูกค้าเคยสั่ง</p>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-slate-50">
                        <tr>
                            <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase">สินค้า</th>
                            <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase">กลุ่ม</th>
                            <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase text-right">จำนวน</th>
                            <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase text-right">ราคา/หน่วย</th>
                            <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase text-right">รวม</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 text-sm">
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    
    # Render HTML ลงใน Streamlit
    st.markdown(html_content, unsafe_allow_html=True)

else:
    # กรณีหน้าแรกยังไม่ได้เลือกใคร
    st.markdown("""
    <div class="flex flex-col items-center justify-center h-[50vh] text-slate-400">
        <span class="material-icons-outlined text-6xl mb-4">search</span>
        <h3 class="text-xl font-medium">กรุณาค้นหาและเลือกลูกค้าจากเมนูด้านซ้าย</h3>
    </div>
    """, unsafe_allow_html=True)

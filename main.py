import streamlit as st
import sqlite3
import pandas as pd

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(
    page_title="Care360Plus - หน้าแรก",
    page_icon="🛡️",
    layout="wide"
)

# ฟังก์ชันสำหรับดึงข้อมูลภาคเรียนทั้งหมดที่มีในระบบมาให้เลือก
def get_all_terms():
    try:
        conn = sqlite3.connect('care360plus.db')
        # ดึงรายชื่อภาคเรียนที่ไม่ซ้ำกันจากตาราง assessments
        query = "SELECT DISTINCT term FROM assessments ORDER BY term DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            return df['term'].tolist()
    except:
        pass
    return ["2/2569", "1/2569"] # ค่าตั้งต้นเริ่มต้นหากยังไม่มีข้อมูลในระบบ

# ฟังก์ชันสำหรับประมวลผลสถิติแบบระบุภาคเรียน (term)
def load_dashboard_data(selected_term):
    conn = sqlite3.connect('care360plus.db')
    
    # ใช้ LEFT JOIN เพื่อตรวจสอบการประเมินในภาคเรียนที่เลือก
    # ถ้าประเมินแล้ว field term ในตาราง assessments จะไม่เป็น NULL
    query = f"""
        SELECT 
            s.st_id, 
            s.classroom,
            CASE 
                WHEN a.term IS NOT NULL THEN 1 
                ELSE 0 
            END as is_evaluated
        FROM students s
        LEFT JOIN assessments a 
            ON s.st_id = a.st_id AND a.term = '{selected_term}'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ส่วนหัวของหน้าเว็บ
st.title("🛡️ ระบบ Care360Plus")
st.subheader("โรงเรียนบ้านควนตีหมุน")
st.markdown("---")

# 2. แถบเลือกภาคเรียนสำหรับดูสถิติ
terms_list = get_all_terms()
selected_term = st.selectbox("📅 เลือกภาคเรียนที่ต้องการดูสถิติ:", terms_list)

try:
    # โหลดข้อมูลตามเทอมที่เลือก
    df = load_dashboard_data(selected_term)
    
    # 3. คำนวณสถิติหลัก
    total_students = len(df)
    evaluated_count = df['is_evaluated'].sum()
    
    if total_students > 0:
        evaluation_percentage = (evaluated_count / total_students) * 100
    else:
        evaluation_percentage = 0.0

    # 4. แสดงผลแถบสถิติหลัก (KPI Cards)
    st.markdown(f"### 📊 ภาพรวมการประเมินประจำภาคเรียนที่ {selected_term}")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="จำนวนนักเรียนทั้งหมดในระบบ", value=f"{total_students} คน")
    with col2:
        st.metric(label="ทำแบบประเมินแล้ว", value=f"{evaluated_count} คน", delta=f"คิดเป็น {evaluation_percentage:.1f}%")
    with col3:
        st.metric(label="ยังไม่ได้ประเมิน", value=f"{total_students - evaluated_count} คน")

    st.markdown("---")

    # 5. แสดงผลสถิติแยกตามชั้นเรียน
    st.markdown("### 🏫 ความคืบหน้าแยกตามระดับชั้นเรียน")
    
    # จัดกลุ่มข้อมูลแยกรายชั้น (class)
    class_stats = df.groupby('classroom').agg(
        นักเรียนทั้งหมด=('st_id', 'count'),
        ประเมินแล้ว=('is_evaluated', 'sum')
    ).reset_index()
    
    # คำนวณคอลัมน์เพิ่มเติม
    class_stats['ยังไม่ประเมิน'] = class_stats['นักเรียนทั้งหมด'] - class_stats['ประเมินแล้ว']
    class_stats['ความคืบหน้า (ร้อยละ)'] = (class_stats['ประเมินแล้ว'] / class_stats['นักเรียนทั้งหมด'] * 100).round(2)
    
    # ตกแต่งชื่อหัวตารางให้เป็นภาษาไทยสวยงาม
    class_stats.rename(columns={'classroom': 'ระดับชั้น'}, inplace=True)
    
    # แสดงผลตารางแดชบอร์ดแยกชั้น
    st.dataframe(
        class_stats[['ระดับชั้น', 'นักเรียนทั้งหมด', 'ประเมินแล้ว', 'ยังไม่ประเมิน', 'ความคืบหน้า (ร้อยละ)']], 
        use_container_width=True, 
        hide_index=True
    )

except Exception as e:
    st.warning("⚠️ ไม่สามารถดึงข้อมูลสถิติได้ กรุณาตรวจสอบว่ามีตาราง students และ assessments ในฐานข้อมูลแล้ว")
    st.error(f"รายละเอียดข้อผิดพลาด: {e}") # ปลดคอมเมนต์ออกเพื่อดูข้อผิดพลาดจริงหากรันไม่ผ่าน

st.markdown("---")
st.info("💡 กรุณาเลือกเมนูจากแถบด้านข้างเพื่อเริ่มต้นใช้งานระบบบันทึกข้อมูลและดูแดชบอร์ดอย่างละเอียด")
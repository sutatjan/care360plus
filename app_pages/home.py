import streamlit as st
import sqlite3
import pandas as pd

# 🚨 เอา st.set_page_config ออกแล้ว เนื่องจากระบบจะใช้การตั้งค่าจากหน้า login.py หลักแทนครับ

# ดึงข้อมูลผู้ใช้จาก Session State
if "user_info" in st.session_state and st.session_state["user_info"] is not None:
    user = st.session_state["user_info"]
    full_name = f"{user['prefix']}{user['first_name']} {user['last_name']}"
else:
    full_name = "ผู้ใช้งานระบบ"

# ส่วนหัวแสดงความยินดีต้อนรับ
st.write(f"ยินดีต้อนรับ: **{full_name}**")

# ฟังก์ชันสำหรับดึงข้อมูลภาคเรียนทั้งหมดที่มีในระบบมาให้เลือก
def get_all_terms():
    try:
        conn = sqlite3.connect('care360plus.db')
        # ดึงรายชื่อภาคเรียนที่ไม่ซ้ำกันจากตาราง assessments
        query = "SELECT DISTINCT term FROM assessments ORDER BY term DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty and df['term'].notna().any():
            return [str(t) for t in df['term'].dropna().tolist()]
    except Exception as e:
        # พิมพ์บอกเบื้องหลังเบา ๆ เผื่อใช้ตรวจสอบตารางในฐานข้อมูล
        st.sidebar.warning(f"⚠️ กำลังใช้ภาคเรียนเริ่มต้น (เชื่อมต่อตาราง assessments ไม่สำเร็จ)")
    
    return ["2/2569", "1/2569"] # ค่าตั้งต้นเริ่มต้นหากยังไม่มีข้อมูลในระบบ

# ฟังก์ชันสำหรับประมวลผลสถิติแบบระบุภาคเรียน (term)
def load_dashboard_data(selected_term):
    conn = sqlite3.connect('care360plus.db')
    
    # ใช้ LEFT JOIN เพื่อตรวจสอบการประเมินในภาคเรียนที่เลือก
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
    
    if df.empty:
        st.warning("⚠️ ไม่พบข้อมูลนักเรียนในตาราง students กรุณาเพิ่มข้อมูลนักเรียนก่อนครับ")
    else:
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
        
        # จัดกลุ่มข้อมูลแยกรายชั้น (classroom)
        class_stats = df.groupby('classroom').agg(
            นักเรียนทั้งหมด=('st_id', 'count'),
            ประเมินแล้ว=('is_evaluated', 'sum')
        ).reset_index()
        
        # คำนวณคอลัมน์เพิ่มเติม โดยป้องกันการหารด้วยศูนย์
        class_stats['ยังไม่ประเมิน'] = class_stats['นักเรียนทั้งหมด'] - class_stats['ประเมินแล้ว']
        class_stats['ความคืบหน้า (ร้อยละ)'] = (
            class_stats['ประเมินแล้ว'] / class_stats['นักเรียนทั้งหมด'].replace(0, 1) * 100
        ).round(2)
        
        # ตกแต่งชื่อหัวตารางให้เป็นภาษาไทยสวยงาม
        class_stats.rename(columns={'classroom': 'ระดับชั้น'}, inplace=True)
        
        # จัดเรียงลำดับคอลัมน์และแสดงผลตารางแดชบอร์ดแยกชั้น
        display_df = class_stats[['ระดับชั้น', 'นักเรียนทั้งหมด', 'ประเมินแล้ว', 'ยังไม่ประเมิน', 'ความคืบหน้า (ร้อยละ)']]
        
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "ความคืบหน้า (ร้อยละ)": st.column_config.NumberColumn(
                    "ความคืบหน้า",
                    format="%.2f %%"
                )
            }
        )

except Exception as e:
    st.warning("⚠️ ไม่สามารถดึงข้อมูลสถิติได้ กรุณาตรวจสอบว่ามีตาราง students และ assessments ในฐานข้อมูลแล้ว")
    st.error(f"รายละเอียดข้อผิดพลาด: {e}")

st.markdown("---")

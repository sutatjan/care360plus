import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px

# 1. ตั้งค่าหน้าเพจ
st.set_page_config(
    page_title="Care360Plus - สรุปผลรายด้าน",
    page_icon="📊",
    layout="wide"
)

# ฟังก์ชันดึงภาคเรียนทั้งหมด
def get_all_terms():
    try:
        conn = sqlite3.connect('care360plus.db')
        query = "SELECT DISTINCT term FROM assessments ORDER BY term DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['term'].tolist()
    except:
        return ["2/2569", "1/2569"]

# ฟังก์ชันดึงและประมวลผลข้อมูลรายห้องแยกตามด้าน
def load_detailed_summary(selected_term):
    conn = sqlite3.connect('care360plus.db')
    
    # ดึงคอลัมน์ระดับชั้นเรียน และคอลัมน์ผลประเมินทั้ง 6 ด้าน
    query = f"""
        SELECT 
            s.classroom,
            a.score_academic,
            a.score_health,
            a.score_behavior,
            a.score_economy,
            a.score_safety,
            a.score_drug
        FROM students s
        INNER JOIN assessments a ON s.st_id = a.st_id
        WHERE a.term = '{selected_term}'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ส่วนหัวของหน้าเว็บ
st.title("📊 ระบบสรุปผลสถานะนักเรียนแยกรายด้านรายห้อง")
st.subheader("โรงเรียนบ้านควนตีหมุน")
st.markdown("---")

# เลือกภาคเรียน
terms_list = get_all_terms()
selected_term = st.selectbox("📅 เลือกภาคเรียนเพื่อดูรายงานสรุป:", terms_list)

try:
    df = load_detailed_summary(selected_term)
    
    if df.empty:
        st.warning(f"📝 ยังไม่มีข้อมูลการประเมินในภาคเรียนที่ {selected_term}")
    else:
        # 2. ทำการคำนวณนับจำนวนแยกรายด้านและเงื่อนไข (1, 2, 3) ด้วย Pandas Groupby
        # เพื่อสร้างตารางรายงานสรุปรายห้อง
        summary_rooms = df.groupby('classroom').agg(
            # นักเรียนทั้งหมดในห้องที่ทำประเมินแล้ว
            นักเรียนทั้งหมด=('classroom', 'count'),
            
            # นิยามคำว่า "ปกติ": คือนักเรียนที่ได้เลข 1 ครบทุกด้าน (ไม่มีด้านใดเสี่ยงหรือมีปัญหาเลย)
            ปกติ_ทุกด้าน=(
                'classroom', 
                lambda x: ((df.loc[x.index, ['score_academic', 'score_health', 'score_behavior', 'score_economy', 'score_safety', 'score_drug']] == 1).all(axis=1)).sum()
            ),
            
            # นับกลุ่ม "เสี่ยง" (ค่าเท่ากับ 2) แยกเป็นรายด้าน
            เสี่ยง_การเรียน=('score_academic', lambda x: (x == 2).sum()),
            เสี่ยง_สุขภาพ=('score_health', lambda x: (x == 2).sum()),
            เสี่ยง_พฤติกรรม=('score_behavior', lambda x: (x == 2).sum()),
            เสี่ยง_เศรษฐกิจ=('score_economy', lambda x: (x == 2).sum()),
            เสี่ยง_ความปลอดภัย=('score_safety', lambda x: (x == 2).sum()),
            เสี่ยง_ยาเสพติด=('score_drug', lambda x: (x == 2).sum()),
            
            # นับกลุ่ม "มีปัญหา" (ค่าเท่ากับ 3) แยกเป็นรายด้าน
            มีปัญหา_การเรียน=('score_academic', lambda x: (x == 3).sum()),
            มีปัญหา_สุขภาพ=('score_health', lambda x: (x == 3).sum()),
            มีปัญหา_พฤติกรรม=('score_behavior', lambda x: (x == 3).sum()),
            มีปัญหา_เศรษฐกิจ=('score_economy', lambda x: (x == 3).sum()),
            มีปัญหา_ความปลอดภัย=('score_safety', lambda x: (x == 3).sum()),
            มีปัญหา_ยาเสพติด=('score_drug', lambda x: (x == 3).sum())
        ).reset_index()
        
        # เปลี่ยนชื่อคอลัมน์หลักให้สวยงาม
        summary_rooms.rename(columns={'classroom': 'ระดับชั้นเรียน'}, inplace=True)
        
        # เพิ่มแถว "รวมทั้งสิ้น" ของทั้งโรงเรียนไว้บรรทัดล่างสุด
        total_row = summary_rooms.sum(numeric_only=True).to_frame().T
        total_row.insert(0, 'ระดับชั้นเรียน', 'รวมทั้งสิ้น')
        summary_table = pd.concat([summary_rooms, total_row], ignore_index=True)
        
        # 3. แสดงตารางแบ่งโซนข้อมูลให้ดูง่ายชัดเจน
        st.markdown(f"### 📋 ตารางวิเคราะห์ข้อมูลความเสี่ยง 6 ด้าน จำแนกรายห้องเรียน ({selected_term})")
        
        # ใช้ container_width เพื่อให้ตารางขยายเต็มหน้าจอ และซ่อน index ดั้งเดิม
        st.dataframe(summary_table, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # 4. ฟีเจอร์พิเศษ: คัดเลือกห้องเรียนเพื่อดูสถิติเชิงลึกในรูปแบบกราฟ
        st.markdown("### 🎯 เจาะลึกสถานการณ์ความเสี่ยงรายห้องเรียน")
        room_list = summary_rooms['ระดับชั้นเรียน'].tolist()
        selected_room = st.selectbox("🏫 เลือกห้องเรียนที่ต้องการดูสรุปรายด้านแบบกราฟ:", room_list)
        
        # ดึงแถวข้อมูลของห้องที่เลือกมาทำกราฟเปรียบเทียบ
        room_data = summary_rooms[summary_rooms['ระดับชั้นเรียน'] == selected_room].iloc[0]
        
        # จัดรูปแบบโครงสร้างข้อมูลใหม่ (Melt) เพื่อนำมาพล็อตแผนภูมิแท่งเปรียบเทียบ 6 ด้าน
        chart_data = pd.DataFrame({
            'ด้านความเสี่ยง': ['การเรียน', 'สุขภาพ', 'พฤติกรรม', 'เศรษฐกิจ', 'ความปลอดภัย', 'ยาเสพติด'],
            'กลุ่มเสี่ยง (คน)': [
                room_data['เสี่ยง_การเรียน'], room_data['เสี่ยง_สุขภาพ'], 
                room_data['เสี่ยง_พฤติกรรม'], room_data['เสี่ยง_เศรษฐกิจ'], 
                room_data['เสี่ยง_ความปลอดภัย'], room_data['เสี่ยง_ยาเสพติด']
            ],
            'กลุ่มมีปัญหา (คน)': [
                room_data['มีปัญหา_การเรียน'], room_data['มีปัญหา_สุขภาพ'], 
                room_data['มีปัญหา_พฤติกรรม'], room_data['มีปัญหา_เศรษฐกิจ'], 
                room_data['มีปัญหา_ความปลอดภัย'], room_data['มีปัญหา_ยาเสพติด']
            ]
        })
        
        # แปลงข้อมูลให้อยู่ในแนวตั้ง (Long Format) สำหรับ Plotly
        chart_melted = pd.melt(chart_data, id_vars=['ด้านความเสี่ยง'], value_vars=['กลุ่มเสี่ยง (คน)', 'กลุ่มมีปัญหา (คน)'],
                               var_name='สถานะความรุนแรง', value_name='จำนวนนักเรียน')
        
        # แสดงผลกราฟแท่งเปรียบเทียบรายด้านของห้องนั้นๆ
        fig = px.bar(
            chart_melted,
            x='ด้านความเสี่ยง',
            y='จำนวนนักเรียน',
            color='สถานะความรุนแรง',
            barmode='group',
            color_discrete_map={'กลุ่มเสี่ยง (คน)': '#f1c40f', 'กลุ่มมีปัญหา (คน)': '#e74c3c'},
            title=f"แผนภูมิแท่งเปรียบเทียบระดับความรุนแรงแยกตามรายด้าน ของชั้นเรียน {selected_room}"
        )
        fig.update_layout(yaxis_title="จำนวนนักเรียน (คน)", xaxis_title="มิติด้านการดูแลช่วยเหลือนักเรียน")
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error("⚠️ เกิดข้อผิดพลาดในการประมวลผลตารางความเสี่ยง")
    st.info("💡 โปรดตรวจสอบว่าชื่อคอลัมน์ทั้ง 6 ด้านในตาราง assessments สะกดตรงตามตัวแปรในโค้ดหรือไม่")
    # st.error(f"รายละเอียดเทคนิค: {e}")
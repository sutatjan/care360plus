import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px

# ตั้งค่าหน้าเว็บให้รองรับการแสดงผล Dashboard
st.set_page_config(page_title="รายงานผล CARE 360 Plus", layout="wide")

def load_data():
    """ดึงข้อมูลจากฐานข้อมูล care360plus.db"""
    with sqlite3.connect('care360plus.db') as conn:
        query = """
        SELECT a.*, s.fname, s.lname, s.classroom 
        FROM assessments a
        JOIN students s ON a.st_id = s.st_id
        ORDER BY a.eval_date DESC
        """
        return pd.read_sql_query(query, conn)

# --- ส่วนควบคุมหลัก ---
st.title("📊 ระบบรายงานผลการดูแลช่วยเหลือนักเรียน")
df = load_data()

if df.empty:
    st.warning("⚠️ ไม่พบข้อมูลการประเมินในระบบ กรุณาบันทึกข้อมูลก่อนครับ")
else:
    # --- Sidebar Filters ---
    st.sidebar.header("📍 ตัวกรองรายงาน")
    
    # เลือกปีการศึกษา/ภาคเรียน
    all_terms = sorted(df['term'].unique())
    selected_terms = st.sidebar.multiselect("เลือกภาคเรียน", options=all_terms, default=all_terms)
    
    # เลือกชั้นเรียน
    all_classes = ["ทั้งหมด"] + sorted(df['classroom'].unique().tolist())
    selected_class = st.sidebar.selectbox("เลือกชั้นเรียน", all_classes)
    
    # เลือกนักเรียนรายคน (สำหรับเจาะลึก)
    mask_basic = df['term'].isin(selected_terms)
    if selected_class != "ทั้งหมด":
        mask_basic = mask_basic & (df['classroom'] == selected_class)
    
    current_df = df[mask_basic]
    
    all_students = ["ทั้งหมด"] + sorted((current_df['fname'] + " " + current_df['lname']).unique().tolist())
    selected_student = st.sidebar.selectbox("เจาะลึกข้อมูลรายคน", all_students)

    if selected_student != "ทั้งหมด":
        current_df = current_df[(current_df['fname'] + " " + current_df['lname']) == selected_student]

    # --- ระบบ Tabs 4 ส่วน ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 The Big Picture", 
        "🏫 Classroom Insights", 
        "🚩 Tracking & Action",
        "📊 Compare Terms"
    ])

    # --- ส่วนที่ 1: The Big Picture ---
    with tab1:
        st.subheader("🌐 ภาพรวมสถานะความเสี่ยง (The Big Picture)")
        c1, c2 = st.columns([1, 2])
        with c1:
            # Gauge Chart (ความปลอดภัยรวม)
            total = len(current_df)
            normal = len(current_df[current_df['summary_status'] == 'ปกติ'])
            s_rate = (normal / total * 100) if total > 0 else 0
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number", value=s_rate, title={'text': "ดัชนีความปลอดภัย (%)"},
                gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#2ecc71"},
                       'steps': [{'range': [0, 50], 'color': "#ff4b4b"}, {'range': [80, 100], 'color': "#2ecc71"}]}))
            st.plotly_chart(fig_gauge, use_container_width=True)
        with c2:
            # Radar Chart เฉลี่ย 6 ด้าน
            categories = ['การเรียน', 'สุขภาพ', 'พฤติกรรม', 'เศรษฐกิจ', 'ปลอดภัย', 'ยาเสพติด']
            fig_radar = go.Figure()
            for t in selected_terms:
                t_df = current_df[current_df['term'] == t]
                if not t_df.empty:
                    v = [t_df['score_academic'].mean(), t_df['score_health'].mean(), t_df['score_behavior'].mean(),
                         t_df['score_economy'].mean(), t_df['score_safety'].mean(), t_df['score_drug'].mean()]
                    fig_radar.add_trace(go.Scatterpolar(r=v, theta=categories, fill='toself', name=f'เทอม {t}'))
            fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[1, 3])))
            st.plotly_chart(fig_radar, use_container_width=True)

    # --- ส่วนที่ 2: Classroom Insights ---
    # --- ส่วนที่ 2: Classroom Insights ---
    with tab2:
        st.subheader("🏫 เจาะลึกข้อมูลเชิงห้องเรียน (Classroom Insights)")
        
        if not current_df.empty:
            st.write("🚦 Heatmap สัญญาณไฟจราจรรายบุคคล (เขียว=ปกติ, เหลือง=เสี่ยง, แดง=มีปัญหา)")
            
            # แก้ไขจุดนี้: เอา "ชื่อ" มารวมกับ "เทอม" เพื่อป้องกันชื่อซ้ำกันตอนสลับแกน กราฟจะได้ไม่พังครับ
            hm_raw = current_df.copy()
            hm_raw['ชื่อ_เทอม'] = hm_raw['fname'] + " (เทอม " + hm_raw['term'] + ")"
            
            # ดึงเฉพาะคอลัมน์ที่ต้องใช้แสดงผล
            hm_display = hm_raw[['ชื่อ_เทอม', 'score_academic', 'score_health', 'score_behavior', 'score_economy', 'score_safety', 'score_drug']].copy()
            hm_display.columns = ['ชื่อนักเรียน', 'การเรียน', 'สุขภาพ', 'พฤติกรรม', 'เศรษฐกิจ', 'ปลอดภัย', 'ยาเสพติด']
            
            # วาดกราฟ Heatmap โดยใช้ 'ชื่อนักเรียน' ที่ไม่ซ้ำแล้วเป็น Index
            fig_hm = px.imshow(hm_display.set_index('ชื่อนักเรียน').T, 
                               color_continuous_scale=['#2ecc71', '#ffa117', '#ff4b4b'],
                               labels=dict(color="ระดับความเสี่ยง"))
            st.plotly_chart(fig_hm, use_container_width=True)
            
            st.write("📊 เปรียบเทียบจำนวนกลุ่มเสี่ยงระหว่างห้องเรียน")
            class_comp = current_df[current_df['summary_status'] != 'ปกติ'].groupby(['classroom', 'summary_status']).size().reset_index(name='จำนวน')
            if not class_comp.empty:
                st.plotly_chart(px.bar(class_comp, x='classroom', y='จำนวน', color='summary_status', barmode='group'), use_container_width=True)
            else:
                st.success("🎉 ยอดเยี่ยมมาก! ไม่พบนักเรียนกลุ่มเสี่ยงในชั้นเรียนที่เลือก")
        else:
            st.info("ไม่พบข้อมูลสำหรับการแสดงผลในเงื่อนไขนี้")

    # --- ส่วนที่ 3: Tracking & Action ---
    with tab3:
        st.subheader("🚩 ระบบแจ้งเตือนและติดตาม (Tracking & Action)")
        col_w, col_t = st.columns(2)
        with col_w:
            st.write("🔦 กลุ่มเฝ้าระวัง (Watchlist)")
            watch = current_df[(current_df.iloc[:, 3:9] == 3).any(axis=1)]
            if not watch.empty:
                for _, r in watch.iterrows():
                    st.error(f"🆘 {r['fname']} {r['lname']} ({r['classroom']}) - มีปัญหาเร่งด่วน")
            else:
                st.success("✅ ไม่พบนักเรียนกลุ่มวิกฤต")
        with col_t:
            st.write("📈 Trend Analysis (แนวโน้มรวม)")
            if len(selected_terms) >= 2:
                terms = sorted(selected_terms)
                c1 = len(df[(df['term'] == terms[0]) & (df['summary_status'] != 'ปกติ')])
                c2 = len(df[(df['term'] == terms[1]) & (df['summary_status'] != 'ปกติ')])
                st.metric("จำนวนกลุ่มเสี่ยงล่าสุด", f"{c2} คน", delta=f"{c2-c1} คน", delta_color="inverse")

    # --- ส่วนที่ 4: Compare Terms ---
    with tab4:
        st.subheader("📊 เปรียบเทียบ 2 ภาคเรียน (Comparison)")
        if len(selected_terms) >= 2:
            st.write("📉 การเปลี่ยนแปลงความเสี่ยงรายด้าน (เทอม 1 vs เทอม 2)")
            # Grouped Bar Chart
            comp_data = current_df.groupby('term')[['score_academic', 'score_health', 'score_behavior', 'score_economy', 'score_safety', 'score_drug']].mean().reset_index()
            comp_melt = comp_data.melt(id_vars='term', var_name='ด้านการประเมิน', value_name='คะแนนเฉลี่ย')
            fig_comp = px.bar(comp_melt, x='ด้านการประเมิน', y='คะแนนเฉลี่ย', color='term', barmode='group',
                              color_discrete_map={all_terms[0]: '#3498db', all_terms[1]: '#f39c12'})
            st.plotly_chart(fig_comp, use_container_width=True)
            
            st.info("💡 หากพื้นที่กราฟใยแมงมุม (ใน Tab 1) ของเทอม 2 เล็กลง แสดงว่าการพัฒนานักเรียนของโรงเรียนบ้านควนติหมุนได้ผลดีครับ")
        else:
            st.info("กรุณาเลือกอย่างน้อย 2 ภาคเรียนที่แถบด้านข้างเพื่อเปรียบเทียบข้อมูลครับ")
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time

def get_existing_eval(st_id, term):
    with sqlite3.connect('care360plus.db', timeout=20) as conn:
        query = "SELECT * FROM assessments WHERE st_id=? AND term=? ORDER BY eval_id DESC LIMIT 1"
        main_df = pd.read_sql_query(query, conn, params=(st_id, term))
        
        if not main_df.empty:
            ev_id = main_df.iloc[0]['eval_id']            
            acad = pd.read_sql_query(f"SELECT * FROM academic_details WHERE eval_id={ev_id}", conn)
            health = pd.read_sql_query(f"SELECT * FROM health_details WHERE eval_id={ev_id}", conn)
            beh = pd.read_sql_query(f"SELECT * FROM behavior_details WHERE eval_id={ev_id}", conn)
            econ = pd.read_sql_query(f"SELECT * FROM economy_details WHERE eval_id={ev_id}", conn)
            safe = pd.read_sql_query(f"SELECT * FROM safety_details WHERE eval_id={ev_id}", conn)
            drug = pd.read_sql_query(f"SELECT * FROM drug_details WHERE eval_id={ev_id}", conn)
            
            return (main_df.iloc[0], 
                    acad.iloc[0] if not acad.empty else None, 
                    health.iloc[0] if not health.empty else None,
                    beh.iloc[0] if not beh.empty else None,
                    econ.iloc[0] if not econ.empty else None,
                    safe.iloc[0] if not safe.empty else None,
                    drug.iloc[0] if not drug.empty else None)
    return None, None, None, None, None, None, None

def get_summary_value(scores):
    if 3 in scores: return 3
    if 2 in scores: return 2
    return 1

def get_label(val):
    labels = {1: "ปกติ", 2: "เสี่ยง", 3: "มีปัญหา"}
    return labels.get(val, "ไม่ระบุ")

def get_idx(df, col_name):
    if df is not None and col_name in df:
        return int(df[col_name]) - 1
    return 0

# --- เริ่มต้นส่วนแสดงผล ---
st.title("📝 บันทึกการประเมินนักเรียนรายบุคคล")

# ดึงข้อมูลนักเรียนและเรียงตามรหัสตามที่ท่าน ผอ. ต้องการ
conn = sqlite3.connect('care360plus.db')
df_std = pd.read_sql_query("SELECT st_id, prefix, fname, lname, classroom FROM students ORDER BY st_id ASC", conn)
conn.close()

if df_std.empty:
    st.warning("⚠️ ยังไม่มีข้อมูลนักเรียนในระบบ กรุณาเพิ่มข้อมูลนักเรียนก่อนครับ")
    st.stop()

with st.sidebar:
    st.header("📍 ตัวกรองข้อมูล")
    class_list = sorted(df_std['classroom'].unique())
    sel_class = st.selectbox("เลือกชั้นเรียน", class_list)
    
    filtered_std = df_std[df_std['classroom'] == sel_class]
    std_options = {f"{r['st_id']} - {r['prefix']}{r['fname']} {r['lname']}": r['st_id'] for _, r in filtered_std.iterrows()}
    sel_std_label = st.selectbox("เลือกรายชื่อนักเรียน", list(std_options.keys()))
    current_st_id = std_options[sel_std_label]

# --- 3. แบบฟอร์มการประเมิน ---
with st.form("assessment_form"):
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        term = st.text_input("ภาคเรียน/ปีการศึกษา", value="1/2569")
    with col_h2:
        eval_date = st.date_input("วันที่ประเมิน", datetime.now())
    
    existing_main, ex_acad, ex_health, ex_beh, ex_econ, ex_safe, ex_drug = get_existing_eval(current_st_id, term)
   
    if existing_main is not None:
        st.info(f"🔔 ท่านประเมินแล้ว : เมื่อ {existing_main['eval_date']} (ท่านสามารถแก้ไขและกดอัปเดตได้)")
    
    # สร้าง Tabs ให้ทุกคนเห็น
    tabs = st.tabs(["📚 การเรียน", "🏥 สุขภาพ", "🧠 พฤติกรรม", "💰 เศรษฐกิจ", "🦺 ปลอดภัย", "🚫 ยาเสพติด"])
    m = {"ปกติ": 1, "เสี่ยง": 2, "มีปัญหา": 3}

    with tabs[0]: # academic_details
        d_acad = {
            "reading": st.radio("การอ่าน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'reading'), horizontal=True),
            "writing": st.radio("การเขียน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'writing'), horizontal=True),
            "achievement": st.radio("ผลสัมฤทธิ์ทางการเรียน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'achievement'), horizontal=True),
            "responsibility": st.radio("ความรับผิดชอบ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'responsibility'), horizontal=True),
            "interest": st.radio("ความสนใจ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'interest'), horizontal=True),
            "attendance": st.radio("การเข้าเรียน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_acad, 'attendance'), horizontal=True)
        }
        
    with tabs[1]: # health_details
        d_health = {
            "physical_growth": st.radio("ความสมบูรณ์ (น้ำหนัก-ส่วนสูง)", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'physical_growth'), horizontal=True),
            "medical_condition": st.radio("โรคประจำตัว/ภาวะสุขภาพ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'medical_condition'), horizontal=True),
            "hygiene": st.radio("ความสะอาดของร่างกาย", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'hygiene'), horizontal=True),
            "dental_health": st.radio("สุขภาพฟัน/ช่องปาก", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'dental_health'), horizontal=True),
            "physical_fitness": st.radio("สมรรถภาพร่างกาย", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'physical_fitness'), horizontal=True),
            "health_attendance": st.radio("การเจ็บป่วยบ่อย", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_health, 'health_attendance'), horizontal=True)
        }

    with tabs[2]: # behavior_details
        d_beh = {
            "mental_stability": st.radio("ความมั่นคงทางจิตใจ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_beh, 'mental_stability'), horizontal=True),
            "emotional_control": st.radio("การควบคุมอารมณ์", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_beh, 'emotional_control'), horizontal=True),
            "peer_relationship": st.radio("ความสัมพันธ์กับเพื่อน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_beh, 'peer_relationship'), horizontal=True),
            "risk_behavior": st.radio("พฤติกรรมเสี่ยง", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_beh, 'risk_behavior'), horizontal=True),
            "sexual_behavior": st.radio("พฤติกรรมทางเพศ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_beh, 'sexual_behavior'), horizontal=True)
        }

    with tabs[3]: # economy_details
        d_econ = {
            "parent_occupation": st.radio("อาชีพผู้ปกครอง", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'parent_occupation'), horizontal=True),
            "family_expense": st.radio("ภาระค่าใช้จ่ายครอบครัว", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'family_expense'), horizontal=True),
            "school_supplies": st.radio("อุปกรณ์การเรียน/เครื่องแบบ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'school_supplies'), horizontal=True),
            "commute_cost": st.radio("ค่าใช้จ่ายมาโรงเรียน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'commute_cost'), horizontal=True),
            "work_burden": st.radio("ภาระงานหาเลี้ยงชีพ", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'work_burden'), horizontal=True),
            "poverty_status": st.radio("สถานะความยากจน (กสศ.)", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_econ, 'poverty_status'), horizontal=True)
        }

    with tabs[4]: # safety_details
        d_safe = {
            "commute_safety": st.radio("การเดินทางมาโรงเรียน", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'commute_safety'), horizontal=True),
            "family_safety": st.radio("ความปลอดภัยในครอบครัว", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'family_safety'), horizontal=True),
            "abuse_risk": st.radio("การถูกทำร้าย/ละเมิด", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'abuse_risk'), horizontal=True),
            "environment_safety": st.radio("สภาพแวดล้อมที่อยู่อาศัย", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'environment_safety'), horizontal=True),
            "bullying_risk": st.radio("การถูกกลั่นแกล้ง", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'bullying_risk'), horizontal=True),
            "online_safety": st.radio("การใช้สื่อออนไลน์", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_safe, 'online_safety'), horizontal=True)
        }

    with tabs[5]: # drug_details
        d_drug = {
            "substance_use": st.radio("พฤติกรรมเกี่ยวข้องยาเสพติด", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'substance_use'), horizontal=True),
            "risk_group": st.radio("การคบเพื่อนกลุ่มเสี่ยง", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'risk_group'), horizontal=True),
            "smoking": st.radio("สูบบุหรี่/บุหรี่ไฟฟ้า", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'smoking'), horizontal=True),
            "alcohol": st.radio("ดื่มแอลกอฮอล์", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'alcohol'), horizontal=True),
            "night_out": st.radio("ออกนอกบ้านยามวิกาล", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'night_out'), horizontal=True),
            "drug_environment": st.radio("สภาพแวดล้อมยาเสพติด", ["ปกติ", "เสี่ยง", "มีปัญหา"], index=get_idx(ex_drug, 'drug_environment'), horizontal=True)
        }

    note_val = existing_main['note'] if existing_main is not None else ""
    note = st.text_area("✍️ หมายเหตุเพิ่มเติมจากคุณครู", value=note_val)
    btn_save = st.form_submit_button("💾 บันทึกผลการประเมินลงฐานข้อมูล")

    if btn_save:
        # 1. รวบรวมและแปลงค่าคะแนน
        v_acad = [m[v] for v in d_acad.values()]
        v_health = [m[v] for v in d_health.values()]
        v_beh = [m[v] for v in d_beh.values()]
        v_econ = [m[v] for v in d_econ.values()]
        v_safe = [m[v] for v in d_safe.values()]
        v_drug = [m[v] for v in d_drug.values()] 
        
        s_acad = get_summary_value(v_acad)
        s_health = get_summary_value(v_health)
        s_beh = get_summary_value(v_beh)
        s_econ = get_summary_value(v_econ)
        s_safe = get_summary_value(v_safe)
        s_drug = get_summary_value(v_drug)
        
        final_val = get_summary_value([s_acad, s_health, s_beh, s_econ, s_safe, s_drug])
        final_label = get_label(final_val)

        # 2. เริ่มการเชื่อมต่อฐานข้อมูล
        conn_db = sqlite3.connect('care360plus.db', timeout=20)
        c = conn_db.cursor()
        
        try:
            if existing_main is not None:
                # ดึง eval_id ที่ต้องการอัปเดตออกมาให้ชัวร์
                ev_id = int(existing_main['eval_id'])
                
                # UPDATE ตารางหลัก (assessments)
                c.execute("""UPDATE assessments SET 
                             eval_date = ?, 
                             score_academic = ?, 
                             score_health = ?, 
                             score_behavior = ?, 
                             score_economy = ?, 
                             score_safety = ?, 
                             score_drug = ?, 
                             summary_status = ?, 
                             note = ? 
                             WHERE eval_id = ?""", 
                          (eval_date, s_acad, s_health, s_beh, s_econ, s_safe, s_drug, final_label, note, ev_id))
                
                # UPDATE ตารางย่อยทีละตาราง
                c.execute("UPDATE academic_details SET reading=?, writing=?, achievement=?, responsibility=?, interest=?, attendance=? WHERE eval_id=?", (*v_acad, ev_id))
                c.execute("UPDATE health_details SET physical_growth=?, medical_condition=?, hygiene=?, dental_health=?, physical_fitness=?, health_attendance=? WHERE eval_id=?", (*v_health, ev_id))
                c.execute("UPDATE behavior_details SET mental_stability=?, emotional_control=?, peer_relationship=?, risk_behavior=?, sexual_behavior=? WHERE eval_id=?", (*v_beh, ev_id))
                c.execute("UPDATE economy_details SET parent_occupation=?, family_expense=?, school_supplies=?, commute_cost=?, work_burden=?, poverty_status=? WHERE eval_id=?", (*v_econ, ev_id))
                c.execute("UPDATE safety_details SET commute_safety=?, family_safety=?, abuse_risk=?, environment_safety=?, bullying_risk=?, online_safety=? WHERE eval_id=?", (*v_safe, ev_id))
                c.execute("UPDATE drug_details SET substance_use=?, risk_group=?, smoking=?, alcohol=?, night_out=?, drug_environment=? WHERE eval_id=?", (*v_drug, ev_id))
                
                msg = f"🆙 อัปเดตข้อมูลของ {sel_std_label} เรียบร้อยแล้ว"
            else:
                # กรณีเพิ่มข้อมูลใหม่ (Insert)
                c.execute("""INSERT INTO assessments 
                             (st_id, term, eval_date, score_academic, score_health, score_behavior, 
                             score_economy, score_safety, score_drug, summary_status, note) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)""", 
                          (current_st_id, term, eval_date, s_acad, s_health, s_beh, s_econ, s_safe, s_drug, final_label, note))
                
                new_id = c.lastrowid
                c.execute("INSERT INTO academic_details VALUES (NULL,?,?,?,?,?,?,?)", (new_id, *v_acad))
                c.execute("INSERT INTO health_details VALUES (NULL,?,?,?,?,?,?,?)", (new_id, *v_health))
                c.execute("INSERT INTO behavior_details VALUES (NULL,?,?,?,?,?,?)", (new_id, *v_beh))
                c.execute("INSERT INTO economy_details VALUES (NULL,?,?,?,?,?,?,?)", (new_id, *v_econ))
                c.execute("INSERT INTO safety_details VALUES (NULL,?,?,?,?,?,?,?)", (new_id, *v_safe))
                c.execute("INSERT INTO drug_details VALUES (NULL,?,?,?,?,?,?,?)", (new_id, *v_drug))
                msg = "💾 บันทึกการประเมินใหม่เรียบร้อยแล้ว"

            conn_db.commit() # ยืนยันการเปลี่ยนแปลงลงไฟล์ .db
            st.success(msg)
            st.balloons()
            time.sleep(1.5)
            st.rerun()

        except Exception as e:
            conn_db.rollback() # ถ้าพลาดให้ย้อนกลับทั้งหมด
            st.error(f"❌ เกิดข้อผิดพลาด: {e}")
        finally:
            conn_db.close() # ปิดการเชื่อมต่อเสมอ
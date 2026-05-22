import streamlit as st
import sqlite3
import pandas as pd

# --- 1. ฟังก์ชันเชื่อมต่อฐานข้อมูล ---
def get_connection():
    return sqlite3.connect('care360plus.db')

# --- 2. ฟังก์ชันจัดการข้อมูล (CRUD) ---
def add_student_to_db(st_id, prefix, fname, lname, gender, classroom):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO students (st_id, prefix, fname, lname, gender, classroom) 
                     VALUES (?,?,?,?,?,?)''', (st_id, prefix, fname, lname, gender, classroom))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_student(st_id, prefix, fname, lname, gender, classroom):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''UPDATE students 
                 SET prefix=?, fname=?, lname=?, gender=?, classroom=? 
                 WHERE st_id=?''', (prefix, fname, lname, gender, classroom, st_id))
    conn.commit()
    conn.close()

def delete_student(st_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE st_id=?", (st_id,))
    conn.commit()
    conn.close()

# --- 3. เตรียมตัวแปรสำหรับโหมดแก้ไข (Session State) ---
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'student_to_edit' not in st.session_state:
    st.session_state.student_to_edit = {}

# --- 4. หน้า UI ---
st.title("➕ จัดการข้อมูลนักเรียนรายชั้น")

# ส่วนที่ 1: แบบฟอร์ม (บันทึก / แก้ไข)
with st.container(border=True):
    st.subheader("📝 แบบฟอร์มข้อมูลนักเรียน")
    s = st.session_state.student_to_edit # ดึงข้อมูลมาพักไว้กรณีแก้ไข
    
    with st.form("student_form", clear_on_submit=not st.session_state.edit_mode):
        col1, col2, col3 = st.columns(3)
        with col1:
            # ถ้าแก้โหมดแก้ไข ห้ามแก้รหัส (เพราะเป็น Primary Key)
            new_st_id = st.text_input("รหัสนักเรียน", value=s.get('st_id', ''), disabled=st.session_state.edit_mode)
            new_prefix = st.selectbox("คำนำหน้า", ["เด็กชาย", "เด็กหญิง", "นาย", "นางสาว"], 
                                      index=["เด็กชาย", "เด็กหญิง", "นาย", "นางสาว"].index(s.get('prefix', 'เด็กชาย')))
        with col2:
            new_fname = st.text_input("ชื่อจริง", value=s.get('fname', ''))
            new_lname = st.text_input("นามสกุล", value=s.get('lname', ''))
        with col3:
            class_list = [f"ป.{i}/1" for i in range(1,7)] + [f"ม.{i}/1" for i in range(1,4)]
            current_class = s.get('classroom', 'ป.1/1')
            new_class = st.selectbox("ชั้นเรียน", class_list, 
                                     index=class_list.index(current_class) if current_class in class_list else 0)
            new_gender = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True, 
                                  index=0 if s.get('gender', 'ชาย') == 'ชาย' else 1)
        
        btn_col1, btn_col2 = st.columns([1, 4])
        with btn_col1:
            btn_label = "💾 อัปเดต" if st.session_state.edit_mode else "➕ บันทึก"
            submitted = st.form_submit_button(btn_label)
        with btn_col2:
            if st.session_state.edit_mode:
                if st.form_submit_button("❌ ยกเลิกแก้ไข"):
                    st.session_state.edit_mode = False
                    st.session_state.student_to_edit = {}
                    st.rerun()

        if submitted:
            if not (new_st_id and new_fname and new_lname):
                st.error("กรุณากรอกข้อมูลให้ครบถ้วน")
            elif st.session_state.edit_mode:
                update_student(new_st_id, new_prefix, new_fname, new_lname, new_gender, new_class)
                st.success("อัปเดตข้อมูลสำเร็จ!")
                st.session_state.edit_mode = False
                st.session_state.student_to_edit = {}
                st.rerun()
            else:
                if add_student_to_db(new_st_id, new_prefix, new_fname, new_lname, new_gender, new_class):
                    st.success("บันทึกนักเรียนใหม่สำเร็จ!")
                    st.rerun()
                else:
                    st.error("รหัสนักเรียนซ้ำ!")

# --- ส่วนแสดงรายชื่อพร้อมปุ่มจัดการ และระบบค้นหา ---
st.divider()
st.subheader("📋 รายชื่อนักเรียนและเครื่องมือจัดการ")

# 1. ส่วนตัวกรอง (Filters)
f_col1, f_col2 = st.columns([1, 2])
with f_col1:
    search_class = st.selectbox("กรองตามชั้นเรียน", ["ทั้งหมด"] + [f"ป.{i}/1" for i in range(1,7)] + [f"ม.{i}/1" for i in range(1,4)])
with f_col2:
    search_name = st.text_input("🔍 ค้นหาด้วย ชื่อ หรือ นามสกุล", placeholder="พิมพ์ชื่อเพื่อค้นหา...")

# 2. ดึงข้อมูลและทำการกรอง (Filtering Logic)
conn = get_connection()
query = "SELECT * FROM students ORDER BY st_id ASC"
df = pd.read_sql_query(query, conn)
conn.close()

# กรองตามชั้นเรียน
if search_class != "ทั้งหมด":
    df = df[df['classroom'] == search_class]

# กรองตามชื่อหรือนามสกุล (ถ้ามีการพิมพ์ค้นหา)
if search_name:
    df = df[df['fname'].str.contains(search_name) | df['lname'].str.contains(search_name)]

# 3. แสดงผลตารางที่กรองแล้ว
if not df.empty:
    # ส่วนหัวตาราง
    h_col = st.columns([1, 2.5, 1.5, 1, 1, 1])
    h_col[0].markdown("**รหัส**")
    h_col[1].markdown("**ชื่อ-นามสกุล**")
    h_col[2].markdown("**ชั้นเรียน**")
    h_col[3].markdown("**เพศ**")
    h_col[4].markdown("**แก้ไข**")
    h_col[5].markdown("**ลบ**")
    st.divider()

    for idx, row in df.iterrows():
        r_col = st.columns([1, 2.5, 1.5, 1, 1, 1])
        r_col[0].write(row['st_id'])
        r_col[1].write(f"{row['prefix']}{row['fname']} {row['lname']}")
        r_col[2].write(row['classroom'])
        r_col[3].write(row['gender'])
        
        # ปุ่มแก้ไข
        if r_col[4].button("📝", key=f"edit_btn_{row['st_id']}"):
            st.session_state.edit_mode = True
            st.session_state.student_to_edit = row.to_dict()
            st.rerun()
        
        # ปุ่มลบ (มีระบบยืนยัน)
        with r_col[5]:
            # สร้าง Key พิเศษสำหรับเช็กสถานะการยืนยัน
            confirm_key = f"confirm_del_{row['st_id']}"
            
            # ถ้ายังไม่ได้กดลบ ให้โชว์ปุ่มถังขยะปกติ
            if confirm_key not in st.session_state:
                if st.button("🗑️", key=f"del_btn_{row['st_id']}", help="ลบข้อมูล"):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                # ถ้ากดถังขยะแล้ว ให้เปลี่ยนเป็นปุ่มยืนยัน (สีแดง) และปุ่มยกเลิก
                c_del, c_can = st.columns(2)
                with c_del:
                    if st.button("✅", key=f"yes_{row['st_id']}", help="ยืนยันการลบ"):
                        delete_student(row['st_id'])
                        del st.session_state[confirm_key] # ลบสถานะออกหลังทำเสร็จ
                        st.toast(f"ลบข้อมูล {row['fname']} สำเร็จ")
                        st.rerun()
                with c_can:
                    if st.button("❌", key=f"no_{row['st_id']}", help="ยกเลิก"):
                        del st.session_state[confirm_key] # ลบสถานะออกเพื่อกลับไปหน้าปกติ
                        st.rerun()
else:
    st.info("🔎 ไม่พบข้อมูลนักเรียนที่ตรงกับเงื่อนไขการค้นหา")
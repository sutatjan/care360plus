import sqlite3
import streamlit as st

# 1. ตั้งค่าสถานะเริ่มต้นของระบบและช่องกรอกข้อมูล (เซ็ตเป็นค่าว่างตั้งแต่แรกเริ่ม)
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["user_info"] = None

# 🌟 บังคับตั้งค่าในหน่วยความจำของกล่องข้อความเป็นค่าว่างเปล่าไว้ก่อน
if "input_user" not in st.session_state:
    st.session_state["input_user"] = ""
if "input_pass" not in st.session_state:
    st.session_state["input_pass"] = ""


# ฟังก์ชันสำหรับเช็กข้อมูลล็อกอินกับฐานข้อมูล
def login_user(username, password):
    conn = sqlite3.connect("care360plus.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT prefix, first_name, last_name, role 
        FROM users 
        WHERE username = ? AND password = ? AND status = 'active'
    """,
        (username, password),
    )
    user = cursor.fetchone()
    conn.close()
    return user


# ========================================================
# 🛑 กรณีที่ 1: ยังไม่ได้ล็อกอิน -> บังคับหน้าจอล็อกอินแบบไร้ Sidebar 100%
# ========================================================
if not st.session_state["logged_in"]:
    st.set_page_config(
        page_title="CARE 360 Plus - เข้าสู่ระบบ", page_icon="🛡️", layout="centered"
    )

    # โค้ด CSS ซ่อนแถบด้านข้างทั้งหมด
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="collapsedSidebarCreator"] {
                display: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 style='text-align: center; color: #1E3A8A;'>🛡️ CARE 360 Plus</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #6B7280;'>โรงเรียนบ้านควนตีหมุน</p>",
        unsafe_allow_html=True,
    )
    st.write("---")

    with st.form(key="login_form"):
        st.subheader("🔑 ลงชื่อเข้าใช้งานระบบ")

        # ผูกตัวแปรเข้ากับสถานะโดยตรง (สังเกตว่าเมื่อสั่งทับค่าว่างเปล่า กล่องนี้จะว่างทันที)
        username = st.text_input(
            "Username", key="input_user", placeholder="กรอกชื่อผู้ใช้งาน"
        )
        password = st.text_input(
            "Password", type="password", key="input_pass", placeholder="กรอกรหัสผ่าน"
        )

        submit_button = st.form_submit_button(label="เข้าสู่ระบบ")

    if submit_button:
        if username and password:
            user_data = login_user(username, password)
            if user_data:
                st.session_state["logged_in"] = True
                st.session_state["user_info"] = dict(user_data)
                st.success("🔓 รหัสผ่านถูกต้อง...")
                st.rerun()
            else:
                st.error("❌ ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
        else:
            st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

# ========================================================
# 🔓 กรณีที่ 2: ล็อกอินผ่านแล้ว -> แสดงหน้าเมนูและเปิดสิทธิ์แถบด้านข้างปกติ
# ========================================================
else:
    # กำหนดเส้นทางไฟล์ในโฟลเดอร์ app_pages
    page_home = st.Page(
        "app_pages/home.py", title="หน้าแรก", icon="🏠", default=True
    )
    page_student = st.Page(
        "app_pages/student_info.py", title="จัดการข้อมูลนักเรียน", icon="📁"
    )
    page_screening = st.Page(
        "app_pages/screening.py", title="บันทึกการประเมิน", icon="📝"
    )
    page_summary = st.Page("app_pages/summary.py", title="สรุปผล", icon="📊")
    page_analysis = st.Page(
        "app_pages/analysis.py", title="ผลการวิเคราะห์", icon="🧠"
    )
    page_download = st.Page(
        "app_pages/download.py", title="ดาวน์โหลดผลสรุป", icon="📥"
    )

    # ประกาศระบบนำทาง
    pg = st.navigation(
        [
            page_home,
            page_student,
            page_screening,
            page_summary,
            page_analysis,
            page_download,
        ]
    )

    # ปุ่มออกจากระบบส่วนกลางที่แถบด้านข้าง
    with st.sidebar:
        st.write("---")
        st.write(f"👤 ผู้ใช้: **{st.session_state['user_info']['first_name']}**")

        if st.button(
            "🔒 ออกจากระบบ (Logout)", type="primary", use_container_width=True
        ):
            # 1. เคลียร์สถานะการล็อกอิน
            st.session_state["logged_in"] = False
            st.session_state["user_info"] = None

            # 2. 🔥 เปลี่ยนจาก "del" เป็นการบังคับ "เขียนทับด้วยค่าว่างเปล่า" ทันที
            # วิธีนี้จะเข้าไปล้างตัวหนังสือในช่องกรอกบนหน้าจอให้หายวับไป 100% ครับ
            st.session_state["input_user"] = ""
            st.session_state["input_pass"] = ""

            # 3. สั่งดีดหน้าจอรีสตาร์ทระบบ
            st.rerun()

    # ทำงานหน้าเพจปัจจุบันที่เลือก
    pg.run()
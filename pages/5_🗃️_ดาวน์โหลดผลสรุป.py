import streamlit as st
import sqlite3
import pandas as pd
import io

# นำเข้าเครื่องมือสำหรับสร้าง PDF ของ reportlab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 1. ตั้งค่าหน้าเพจ Streamlit
st.set_page_config(
    page_title="Care360Plus - ส่งออก PDF",
    page_icon="📄",
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

# ฟังก์ชันดึงข้อมูลเฉพาะกลุ่มเสี่ยง/มีปัญหา
def load_risk_students(selected_term):
    conn = sqlite3.connect('care360plus.db')
    # ดึงเฉพาะคนที่ด้านใดด้านหนึ่งเป็น 2 (เสี่ยง) หรือ 3 (มีปัญหา)
    query = f"""
        SELECT 
            s.classroom,
            s.st_id,
            s.fname,
            s.lname,
            a.score_academic,
            a.score_health,
            a.score_behavior,
            a.score_economy,
            a.score_safety,
            a.score_drug
        FROM students s
        INNER JOIN assessments a ON s.st_id = a.st_id
        WHERE a.term = '{selected_term}'
          AND (a.score_academic > 1 OR a.score_health > 1 OR a.score_behavior > 1 
               OR a.score_economy > 1 OR a.score_safety > 1 OR a.score_drug > 1)
        ORDER BY s.classroom ASC, s.st_id ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ฟังก์ชันช่วยแปลงตัวเลขเกณฑ์เป็นข้อความสั้นใน PDF
def format_status(score, aspect_name):
    if score == 2:
        return f"เสี่ยง ({aspect_name})"
    elif score == 3:
        return f"มีปัญหา ({aspect_name})"
    return ""

# ฟังก์ชันหลักในการสร้างไฟล์ PDF (Memory Buffer)
def generate_pdf(df_data, term):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    # ลงทะเบียนฟอนต์ภาษาไทยมาตรฐานระบบ (แนะนำใช้ TH Sarabun New หรือฟอนต์ระบบที่มีในเครื่องเซิร์ฟเวอร์)
    # ในกรณีทดสอบทั่วไปหรือรันบน Cloud สามารถใช้ชุดมาตรฐานดั้งเดิมอย่าง 'HeiseiMin-W3' หรือโหลด THSarabun มาใส่ในโฟลเดอร์โปรเจกต์ได้ครับ
    # ตัวอย่างนี้ขอใช้ชุดลงทะเบียนสากลเพื่อให้รันผ่านง่าย:
    try:
        pdfmetrics.registerFont(TTFont('THSarabunNew', 'THSarabunNew.ttf'))
        font_main = 'THSarabunNew'
    except:
        # หากเซิร์ฟเวอร์ไม่มีฟอนต์ตระกูลสารบรรณ จะใช้ฟอนต์สากลสำรอง (แต่แนะนำให้โหลด .ttf มาใส่ในโปรเจกต์จะดีที่สุดครับ)
        font_main = 'Helvetica'
        
    styles = getSampleStyleSheet()
    
    # สร้างสไตล์ตัวอักษรภาษาไทย
    title_style = ParagraphStyle(
        'PDFTitle', parent=styles['Normal'], fontName=font_main, fontSize=18, leading=22, alignment=1
    )
    subtitle_style = ParagraphStyle(
        'PDFSubTitle', parent=styles['Normal'], fontName=font_main, fontSize=14, leading=18, alignment=1
    )
    class_header_style = ParagraphStyle(
        'PDFClassHeader', parent=styles['Normal'], fontName=font_main, fontSize=14, leading=18, textColor=colors.HexColor('#1f77b4'), spaceBefore=10
    )
    cell_style = ParagraphStyle(
        'PDFCell', parent=styles['Normal'], fontName=font_main, fontSize=11, leading=14
    )
    cell_header = ParagraphStyle(
        'PDFCellHeader', parent=styles['Normal'], fontName=font_main, fontSize=11, leading=14, textColor=colors.whitesmoke
    )

    story = []
    
    # ส่วนหัวรายงาน
    story.append(Paragraph("รายงานสรุปข้อมูลนักเรียนกลุ่มเสี่ยงและมีปัญหา", title_style))
    story.append(Paragraph(f"โรงเรียนบ้านควนตีหมุน | ภาคเรียนที่ {term}", subtitle_style))
    story.append(Spacer(1, 15))
    
    # จัดกลุ่มข้อมูลรายชั้นเรียนเพื่อวนลูปสร้างตารางทีละห้อง
    classrooms = df_data['classroom'].unique()
    
    for room in classrooms:
        story.append(Paragraph(f"ระดับชั้นเรียน: {room}", class_header_style))
        story.append(Spacer(1, 5))
        
        # กรองข้อมูลเฉพาะห้องนั้นๆ
        room_df = df_data[df_data['classroom'] == room]
        
        # หัวข้อตาราง PDF
        table_data = [[
            Paragraph("<b>รหัสนักเรียน</b>", cell_header),
            Paragraph("<b>ชื่อ - นามสกุล</b>", cell_header),
            Paragraph("<b>รายการสถานะความเสี่ยง / มีปัญหา ที่ตรวจพบ</b>", cell_header)
        ]]
        
        # วนลูปรายคนในห้องนั้นๆ เพื่อกรองพฤติกรรมความเสี่ยง
        for _, row in room_df.iterrows():
            aspects = []
            if row['score_academic'] > 1: aspects.append(format_status(row['score_academic'], "การเรียน"))
            if row['score_health'] > 1: aspects.append(format_status(row['score_health'], "สุขภาพ"))
            if row['score_behavior'] > 1: aspects.append(format_status(row['score_behavior'], "พฤติกรรม"))
            if row['score_economy'] > 1: aspects.append(format_status(row['score_economy'], "เศรษฐกิจ"))
            if row['score_safety'] > 1: aspects.append(format_status(row['score_safety'], "ความปลอดภัย"))
            if row['score_drug'] > 1: aspects.append(format_status(row['score_drug'], "ยาเสพติด"))
            
            # รวมรายการความเสี่ยงเป็นข้อความยาว 1 บรรทัดย่อย
            risk_text = ", ".join(aspects)
            
            table_data.append([
                Paragraph(str(row['st_id']), cell_style),
                Paragraph(f"{row['fname']} {row['lname']}", cell_style),
                Paragraph(risk_text, cell_style)
            ])
            
        # สร้างตารางและกำหนดขนาดคอลัมน์ (ความกว้างรวมประมาณ 520 pt สำหรับ A4 หักขอบซ้ายขวา)
        t = Table(table_data, colWidths=[80, 140, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')), # หัวตารางสีเทาเข้มดูเป็นทางการ
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9f9f9')]) # แถวสลับสีให้ดูง่าย
        ]))
        
        story.append(t)
        story.append(Spacer(1, 10))
        
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    return pdf_bytes

# สู่หน้าแสดงผลหลักบน Streamlit
st.title("📄 ระบบออกรายงานกลุ่มเสี่ยง กล่มมีปัญหารายชั้นเรียน (PDF)")
st.subheader("โรงเรียนบ้านควนตีหมุน")
st.markdown("---")

selected_term = st.selectbox("📅 เลือกภาคเรียนที่ต้องการออกเล่มรายงาน PDF:", get_all_terms())

try:
    df_risk = load_risk_students(selected_term)
    
    if df_risk.empty:
        st.success(f"🎉 ยอดเยี่ยมมาก! ไม่พบข้อมูลนักเรียนที่มีความเสี่ยงหรือมีปัญหาในภาคเรียนที่ {selected_term}")
    else:
        st.markdown(f"### 📋 รายชื่อนักเรียนกลุ่มเสี่ยง กลุ่มมีปัญหาจำแนกรายชั้นเรียน(รวม {len(df_risk)} คน)")
        
        # แสดงรายการพรีวิวบนหน้าเว็บให้ ผอ. ดูก่อนพิมพ์จริง
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ปุ่มเจนไฟล์ PDF
        pdf_data = generate_pdf(df_risk, selected_term)
        
        st.download_button(
            label="📥 ดาวน์โหลดเล่มรายงานสรุปรายชั้น (ไฟล์ PDF)",
            data=pdf_data,
            file_name=f"เล่มรายงานสรุปความเสี่ยง_{selected_term.replace('/', '_')}.pdf",
            mime="application/pdf"
        )
        st.info("💡 ข้อแนะนำ: เมื่อดาวน์โหลดไปแล้ว คุณครูสามารถเปิดสั่งพิมพ์ผ่านโปรแกรมเปิด PDF ได้ทันที โครงสร้างหน้าเอกสารจะไม่ขยับเขยื้อนครับ")

except Exception as e:
    st.error("⚠️ ไม่สามารถพิมพ์เอกสาร PDF ได้ในขณะนี้")
    st.info("💡 ข้อแนะนำ: โปรดนำไฟล์ฟอนต์ภาษาไทย เช่น `THSarabunNew.ttf` ไปวางไว้ในโฟลเดอร์หลักของโปรเจกต์คู่กับไฟล์ Python นี้ เพื่อให้ระบบสามารถจัดรูปแบบสระภาษาไทยได้อย่างสมบูรณ์แบบครับ")
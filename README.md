# IndoHotel Data Warehouse & Analytics Platform

แพลตฟอร์มคลังข้อมูล (Data Warehouse) และระบบวิเคราะห์ข้อมูลอัจฉริยะสำหรับธุรกิจโรงแรมและรีสอร์ท (Hospitality & Tourism Industry) โดยใช้สถาปัตยกรรมแบบ Star Schema ร่วมกับเครื่องมือ Modern Data Stack (dbt และ DuckDB)

---

## 👥 สมาชิกในกลุ่ม (Team Members)
* **673020253-2 ธนพล ท้าวนอ**
* **673020255-8 บุญญานุช นันดี**
* **673020271-0 อุดมศักดิ์ พระเสนา**
* **673020627-7 ศุภณัฏฐ์ ปุณมา**
* **673020638-7 พิชญธิดา ขัตติยะ**
* **673020639-5 ศศิภัทชา เจียรเจริญกิจ**

---

## 🏨 ข้อมูลจำเพาะของโครงงาน (Domain & Architecture)
* **Domain:** ธุรกิจโรงแรมและรีสอร์ท (ครอบคลุมการจองห้องพัก, อาหารและเครื่องดื่ม F&B, สปา, การจัดงาน/Venue และทรัพยากรบุคคล HR)
* **Operational Database (ER Diagram):** ออกแบบระบบ OLTP แบบ Normalized (3NF) ครบถ้วน 23 ตาราง รองรับการทำงานประจำวัน
* **Data Warehouse (Star Schema):** ออกแบบระบบ OLAP สำหรับวิเคราะห์ข้อมูล ประกอบด้วย:
  * **Fact Tables (5 ตาราง):** เช่น `fact_hotel_bookings`, `fact_fnb_operations`, `fact_hotel_operations_hr`, `fact_ancillary_services`, และ `fact_daily_occupancy`
  * **Dimension Tables (8 ตาราง):** เช่น `dim_date`, `dim_property`, `dim_guest`, `dim_room`, `dim_employee`, `dim_fnb_outlet`, `dim_venue`, และ `dim_event_type`

---

## 📊 คำถามทางธุรกิจ (Business Questions $\ge$ 15 ข้อ)
โปรเจกต์นี้ตอบคำถามเชิงวิเคราะห์และสนับสนุนการตัดสินใจทางธุรกิจรวม 15 ข้อ ครอบคลุม 4 มิติหลัก:
1. **รายได้และผลประกอบการ (Revenue & Performance):** วิเคราะห์ภาพรวมรายได้, แนวโน้มตามฤดูกาล (Seasonality), และอัตราการเข้าพัก (Occupancy Rate)
2. **ลูกค้าและพฤติกรรม (Customer Analysis):** วิเคราะห์พฤติกรรมตามระดับสมาชิก (Loyalty Tier), สัญชาติหลัก (Top Nationalities), และระยะเวลาเข้าพัก (ALOS)
3. **ห้องพักและการจอง (Room & Booking Patterns):** วิเคราะห์ Lead Time, โครงสร้างประเภทห้องพัก, และอัตราการยกเลิกการจอง (Cancellation Rate)
4. **ปฏิบัติการและสถานที่ (Operations & Venue):** วิเคราะห์การใช้ประโยชน์จากพื้นที่จัดงาน (Venue Utilization) และประเภทอีเวนต์ที่สร้างรายได้สูงสุด

---

## 🔄 กระบวนการ ETL / ELT Pipeline
กระบวนการ ETL/ELT ของโปรเจกต์นี้ใช้สถาปัตยกรรม **Modern Data Stack (dbt + DuckDB)** ในการสกัด แปลง และโหลดข้อมูลจากระบบปฏิบัติการ (OLTP) เข้าสู่ Data Warehouse (OLAP) โดยแบ่งออกเป็น 3 ขั้นตอนหลัก:

---

### 1. Extract (การสกัดข้อมูลดิบ)
* **Data Sources:** สกัดข้อมูลดิบจากไฟล์ Flat Files (CSV ทั้งหมด 23 ไฟล์) ในโฟลเดอร์ `datasets/` ซึ่งจำลองจากระบบปฏิบัติการของโรงแรม
* **DuckDB Source Integration:** ใช้ไฟล์กำหนดค่า `src_indohotel.yml` เพื่อเชื่อมต่อ DuckDB เข้ากับไฟล์ CSV โดยตรง ทำให้สามารถ Query ข้อมูลดิบได้ด้วย SQL โดยไม่ต้องโหลดเข้า Database อื่นก่อน

---

### 2. Transform (การแปลงและทำความสะอาดข้อมูล)

กระบวนการ Transform แบ่งออกเป็น 2 ชั้นหลัก (Layered Architecture):

#### **A. Staging Layer (`stg_*.sql`):**
ทำความสะอาดข้อมูลดิบ จัดระเบียบชนิดข้อมูล (Type Casting) และใส่ Business Logic ระดับเริ่มต้นรวม 23 โมเดล โดยเฉพาะตาราง **`stg_guests`** ที่ต้องผ่านกระบวนการ Data Cleaning เชิงลึก เนื่องจาก **ข้อมูลดิบ (Raw Data) ในไฟล์ CSV ต้นทางมีความสกปรกและไม่เป็นมาตรฐาน (Messy & Inconsistent Data)** ดังนี้:
* **การแก้ปัญหาความหมายเดียวกันแต่เขียนไม่เหมือนกัน (Variations & Synonyms):** ข้อมูลดิบปะปนกันระหว่างชื่อประเทศ ชื่อเมือง และดินแดน (เช่น มีทั้ง `'KOREA'`, `'SOUTH KOREA'`, `'REPUBLIC OF KOREA'`, `'SEOUL'`, `'BUSAN'`) จึงต้องใช้ `CASE WHEN` ร่วมกับ `upper()` และ `trim()` เพื่อรวมให้เป็นมาตรฐานสากลเดียวคือ `'South Korea'`
* **การแก้ปัญหาคำย่อและรูปแบบไม่เป็นทางการ (Abbreviations):** แปลงคำย่อกระจัดกระจาย เช่น `'USA'`, `'US'`, `'UK'`, `'PRC'`, `'UAE'` ให้เป็นชื่อทางการที่ถูกต้อง
* **การจัดการชื่อประเทศทางประวัติศาสตร์หรือชื่อทางการยาวๆ (Historical & Formal Names):** แปลงชื่อเก่าหรือชื่อทางการ เช่น `'SWAZILAND'` เป็น `'Eswatini'` หรือ `'LIBYAN ARAB JAMAHIRIYA'` เป็น `'Libya'`
* **การจัดการค่าว่างและความผิดปกติ (Nulls, Blanks & Typos):** ดักเคสค่าที่เป็น `NULL`, ข้อความว่าง (`''`), หรือดินแดนกำกวม ให้ถูกจัดหมวดหมู่รวมกันไปที่ `'Others'` อย่างปลอดภัย
* **Metadata Logging:** เพิ่มฟิลด์ `ingestion_timestamp` ด้วย `current_localtimestamp()` เพื่อบันทึกเวลาที่ข้อมูลถูกดึงเข้าสู่ Pipeline
* **Staging อื่นๆ:** เช่น `stg_bookings` (ทำความสะอาดสถานะการจอง), `stg_fnb_transactions` (คำนวณราคาขายและต้นทุน), และ `stg_employees` (จัดกลุ่มแผนกและระดับการเข้าถึง)

#### **B. Warehouse Layer (`dim_*.sql` และ `fact_*.sql`):**
รวมข้อมูลจาก Staging Layer มาสร้างเป็น **Star Schema** รวม 13 ตาราง:
* **Surrogate Key Generation:** สร้าง Primary Key ใหม่ของตาราง Dimension โดยการทำ Hashing แบบ MD5 จาก Business Keys (เช่น `guest_key`, `property_key`, `room_key`) และสร้าง `date_key` แบบ Integer (`YYYYMMDD`)
* **Fact Calculation & Metrics:** คำนวณค่าตัวชี้วัดเชิงปริมาณ (Measures) เช่น `total_revenue`, `cost_of_goods_sold`, `waste_cost`, `lead_time_days`, `occupancy_rate`, `adr`, และ `revpar`

---

### 3. Load & Data Quality Testing (การโหลดและการทดสอบข้อมูล)
* **Automated Load Execution:** โหลดข้อมูลที่แปลงแล้วลงสู่คลังข้อมูล DuckDB ด้วยคำสั่ง `dbt run` โดยระบบจะจัดการลำดับการสร้างตาราง Dimension ก่อน Fact Tables เพื่อรักษาความสัมพันธ์ของข้อมูล (Referential Integrity)
* **Data Quality Control:** ทำการทดสอบคุณภาพข้อมูลอัตโนมัติด้วยคำสั่ง `dbt test` ครอบคลุม 24 Data Tests ผ่านไฟล์ `schema.yml`:
  * **`unique` Test:** ตรวจสอบความซ้ำซ้อนของ Surrogate Primary Keys ในทุก Dimension Tables
  * **`not_null` Test:** ตรวจสอบว่าไม่มีค่า Null ในคอลัมน์ Primary Keys และ Business Keys สำคัญ
* **ผลการทดสอบ:** ผ่านการทดสอบคุณภาพข้อมูลสำเร็จ 100% 

## 📈 Interactive Dashboard
* เชื่อมต่อข้อมูลจริงจาก Data Warehouse สู่เครื่องมือ Visualization สำหรับแสดงผลตัวชี้วัดสำคัญ (KPIs) เช่น RevPAR, ADR, Occupancy Rate และสัดส่วนรายได้แยกตามสาขา
* **[คลิกที่นี่เพื่อเข้าชม Dashboard (ใส่ลิงก์ของคุณที่นี่)]**

---

## 🚀 วิธีการรันโปรเจกต์ (Quickstart Guide)

ทำตามขั้นตอนด้านล่างเพื่อรันโปรเจกต์ในเครื่องของคุณ:

1. **โคลน Repository และเข้าไปที่โฟลเดอร์โปรเจกต์:**
   ```bash
   git clone <repository-url>
   cd indohotel
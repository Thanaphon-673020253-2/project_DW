# Business Questions → Data Warehouse Schema

เอกสารนี้อธิบายการเชื่อม Business Questions Q1–Q15 กับ Schema ที่มีอยู่จริง

หลักการคิด:

```text
Business Question
→ Business Process
→ Measure
→ Grain
→ Fact
→ Dimension
```

---

# 1. หลักการหา Fact และ Dimension

1. **Business Question** — ต้องการรู้อะไร?
2. **Business Process** — เกี่ยวข้องกับกระบวนการใด?
3. **Measure** — ต้องการวัดอะไร เช่น Revenue, Nights, Occupancy?
4. **Grain** — 1 row ใน Fact หมายถึงอะไร?
5. **Fact** — เลือกตารางที่เก็บเหตุการณ์และตัวเลขที่ต้องการวิเคราะห์
6. **Dimension** — เลือกมุมมองที่ใช้วิเคราะห์ เช่น Date, Property, Guest, Room

### Fact Tables

- `fact_hotel_bookings`
- `fact_fnb_operations`
- `fact_ancillary_services`
- `fact_daily_occupancy`
- `fact_hotel_operations_hr`

### Dimension Tables

- `dim_date`
- `dim_property`
- `dim_guest`
- `dim_room`
- `dim_employee`
- `dim_fnb_outlet`
- `dim_venue`
- `dim_event_type`

---

# 2. Revenue & Performance

## Q1. Total Revenue & Nights Sold

**Question:** รายได้รวมและจำนวนคืนที่ขายได้เท่าไร?

- Process: Hotel Booking
- Event: Booking
- Measure: `total_revenue`, `nights`, Booking Count
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_date`, `dim_property`, `dim_guest`, `dim_room`

**Business Use:** ดู Revenue และ Nights Sold และเปรียบเทียบตามโรงแรม ช่วงเวลา ลูกค้า และ Room Type

---

## Q2. Seasonality Trend

**Question:** รายได้แตกต่างกันตามฤดูกาลหรือไม่?

- Process: Hotel Booking
- Event: Booking
- Measure: Revenue, Nights, Booking Count
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_date`, `dim_property`

**Business Use:** หา Peak / Low Season เพื่อวาง Pricing, Promotion และ Resource Planning

---

## Q3. Weekday vs Weekend Distribution

**Question:** รายได้และ Booking เกิดในวันธรรมดาหรือวันหยุดมากกว่ากัน?

- Process: Hotel Booking
- Event: Booking
- Measure: Revenue, Booking Count, Nights
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_date`, `dim_property`

**Business Use:** เปรียบเทียบ Weekday / Weekend เพื่อวาง Corporate และ Staycation Package

---

## Q4. Ancillary Services Growth Structure

**Question:** บริการเสริมใดสร้างรายได้หรือมีการใช้งานมากที่สุด?

- Process: F&B / Ancillary Services
- Event: F&B Transaction / Spa Service / Event
- Measure: Revenue, Transaction Count, Attendees
- Grain: Transaction / Service Record
- Fact: `fact_fnb_operations`, `fact_ancillary_services`
- Dimension: `dim_date`, `dim_property`, `dim_guest`, `dim_fnb_outlet`, `dim_venue`, `dim_event_type`

**Business Use:** หา Revenue Driver และโอกาส Cross-selling

---

## Q5. Occupancy Rate Efficiency

**Question:** โรงแรมแต่ละแห่งใช้ห้องพักได้มีประสิทธิภาพเพียงใด?

- Process: Daily Occupancy
- Event: Daily Hotel Operation
- Measure: `rooms_sold`, `occupancy_rate`, `adr`, `revpar`
- Grain: 1 Property × 1 Day
- Fact: `fact_daily_occupancy`
- Dimension: `dim_date`, `dim_property`

**Business Use:** เปรียบเทียบ Occupancy, ADR และ RevPAR

---

# 3. Customer Analysis

## Q6. Loyalty Program Repeat Stay Trends

**Question:** ลูกค้าแต่ละ Loyalty Tier มีพฤติกรรมการกลับมาเข้าพักต่างกันหรือไม่?

- Process: Hotel Booking
- Event: Booking
- Measure: Booking Count, Nights, Revenue, Booking ต่อ Guest
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_guest`, `dim_date`, `dim_property`

**Business Use:** เปรียบเทียบพฤติกรรมของแต่ละ Loyalty Tier

> หมายเหตุ: Repeat Stay ควรกำหนดเกณฑ์ เช่น Guest ที่มีมากกว่า 1 Booking

---

## Q7. Top 5 Geographic Nationalities

**Question:** ลูกค้าสัญชาติใดเป็นกลุ่มลูกค้าหลัก?

- Process: Hotel Booking
- Event: Booking
- Measure: Booking Count, Revenue, Nights
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_guest`, `dim_date`, `dim_property`

**Business Use:** หา Geographic Market ที่สำคัญ

---

## Q8. F&B vs Spa Behavioral Differences

**Question:** Domestic และ Foreign ใช้ F&B / Spa ต่างกันหรือไม่?

- Process: F&B / Spa
- Event: F&B Transaction / Spa Service
- Measure: Sales Amount, Transaction Count, Spa Revenue
- Grain: Transaction / Service Record
- Fact: `fact_fnb_operations`, `fact_ancillary_services`
- Dimension: `dim_guest`, `dim_date`, `dim_property`, `dim_fnb_outlet`

**Business Use:** เปรียบเทียบพฤติกรรมเพื่อออกแบบ Package และ Promotion

---

## Q9. Average Length of Stay (ALOS)

**Question:** ลูกค้าเข้าพักเฉลี่ยกี่คืนต่อ Booking?

- Process: Hotel Booking
- Event: Booking
- Measure: Nights, Booking Count
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_guest`, `dim_property`, `dim_date`

```text
ALOS = Total Nights / Number of Bookings
```

**Business Use:** วางแผน Long-stay Promotion

---

# 4. Room & Booking Patterns

## Q10. Booking Lead Time Patterns

**Question:** ลูกค้าจองห้องล่วงหน้ากี่วัน?

- Process: Hotel Booking
- Event: Booking
- Measure: `lead_time_days`, Booking Count, Revenue
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_date`, `dim_property`, `dim_guest`, `dim_room`

**Business Use:** วิเคราะห์ Early / Last-minute Booking เพื่อวาง Pricing

---

## Q11. Room Type Revenue & Booking Structure

**Question:** Room Type ใดมี Booking และ Revenue สูงที่สุด?

- Process: Hotel Booking
- Event: Booking
- Measure: Booking Count, Revenue, Nights
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_room`, `dim_property`, `dim_date`

**Business Use:** วาง Room Mix, Pricing และ Upselling

---

## Q12. Room Cancellation Risk Analysis

**Question:** Room Type ใดมี Cancellation Risk สูง?

- Process: Hotel Booking
- Event: Booking
- Measure: Total Booking, Cancelled Booking, Cancellation Rate
- Grain: 1 Booking
- Fact: `fact_hotel_bookings`
- Dimension: `dim_room`, `dim_property`, `dim_date`

```text
Cancellation Rate
= Cancelled Bookings / Total Bookings
```

**Business Use:** ประเมินความเสี่ยงและวางนโยบายการจอง

---

# 5. Operations & Venue

## Q13. Venue Utilization Volume

**Question:** Venue ประเภทใดถูกใช้งานมากที่สุด?

- Process: Event Booking
- Event: Event Booking
- Measure: Event Count, Attendees, Event Revenue
- Grain: 1 Event / Service Record
- Fact: `fact_ancillary_services`
- Dimension: `dim_venue`, `dim_event_type`, `dim_date`, `dim_property`

**Business Use:** วาง Capacity, Facility Improvement และ Resource Allocation

---

## Q14. Event Type Frequency

**Question:** Event ประเภทใดเกิดขึ้นบ่อยที่สุด?

- Process: Event Booking
- Event: Event Booking
- Measure: Event Count, Attendees
- Grain: 1 Event / Service Record
- Fact: `fact_ancillary_services`
- Dimension: `dim_event_type`, `dim_date`, `dim_property`, `dim_venue`

**Business Use:** วาง Marketing และ Target Customer

---

## Q15. Event Revenue Drivers

**Question:** Event ประเภทใดสร้างรายได้สูงที่สุด?

- Process: Event Booking
- Event: Event Booking
- Measure: `event_revenue`, Event Count, `attendees_count`
- Grain: 1 Event / Service Record
- Fact: `fact_ancillary_services`
- Dimension: `dim_event_type`, `dim_venue`, `dim_property`, `dim_date`

**Business Use:** หา Revenue Driver และวาง Package / Marketing

---

# 6. สรุป Business Process → Fact

| Business Process | Fact Table | Grain |
|---|---|---|
| Hotel Booking | `fact_hotel_bookings` | 1 Booking |
| F&B Operations | `fact_fnb_operations` | 1 F&B Transaction |
| Ancillary Services | `fact_ancillary_services` | 1 Service / Event Record |
| Daily Occupancy | `fact_daily_occupancy` | 1 Property × 1 Day |
| Hotel Operations & HR | `fact_hotel_operations_hr` | 1 Operation Record ตามข้อมูลต้นทาง |

---

# 7. สรุป Dimension

| Dimension | ใช้วิเคราะห์ |
|---|---|
| `dim_date` | วัน เดือน ปี Quarter Weekend และ Season |
| `dim_property` | โรงแรม / Property |
| `dim_guest` | Guest, Nationality, Domestic / Foreign, Loyalty Tier |
| `dim_room` | Room, Room Type, Floor |
| `dim_employee` | Employee, Role, Department |
| `dim_fnb_outlet` | F&B Outlet และ Outlet Type |
| `dim_venue` | Venue, Capacity และพื้นที่ |
| `dim_event_type` | Event Type |

---

# 8. Q1–Q15 → Fact / Dimension Summary

| Q | Business Process | Grain | Fact Table | Dimension หลัก |
|---|---|---|---|---|
| Q1 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Date, Property, Guest, Room |
| Q2 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Date, Property |
| Q3 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Date, Property |
| Q4 | F&B / Ancillary | Transaction / Service | `fact_fnb_operations`, `fact_ancillary_services` | Date, Property, Guest, Outlet, Venue, Event Type |
| Q5 | Daily Occupancy | Property × Day | `fact_daily_occupancy` | Date, Property |
| Q6 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Guest, Date, Property |
| Q7 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Guest, Date, Property |
| Q8 | F&B / Spa | Transaction / Service | `fact_fnb_operations`, `fact_ancillary_services` | Guest, Date, Property, Outlet |
| Q9 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Guest, Property, Date |
| Q10 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Date, Property, Guest, Room |
| Q11 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Room, Property, Date |
| Q12 | Hotel Booking | 1 Booking | `fact_hotel_bookings` | Room, Property, Date |
| Q13 | Event Booking | Event / Service | `fact_ancillary_services` | Venue, Event Type, Date, Property |
| Q14 | Event Booking | Event / Service | `fact_ancillary_services` | Event Type, Date, Property, Venue |
| Q15 | Event Booking | Event / Service | `fact_ancillary_services` | Event Type, Venue, Property, Date |

---

# 9. สรุป Schema


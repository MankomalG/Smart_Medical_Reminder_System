# Smart Medical Reminder System

# Smart Medical Reminder System (AI-Enabled)

## 📌 Overview
The Smart Medical Reminder System is an embedded AI-enabled solution designed to improve medication adherence. It integrates real-time monitoring, intelligent reminders, and verification mechanisms to ensure patients take their medication correctly and on time.

This system combines embedded hardware (FRDM-K66F), real-time operating systems (FreeRTOS), networking (lwIP), and a server-based digital twin to create a complete end-to-end smart healthcare solution.

---

## 🎯 Key Features

### 🔔 Intelligent Reminder System
- Time-based medication scheduling
- Multi-stage reminder flow:
  - Pre-alert (for high-risk cases)
  - Active reminder with buzzer
  - Post-timeout verification
- Snooze functionality with delay handling

---

### 🤖 AI-Based Risk Assessment
- Onboard AI-inspired risk scoring system
- Factors considered:
  - Missed doses
  - Reminder attempts
  - Dispense failures
  - User acknowledgement behavior
- Dynamic adjustment of reminder intensity:
  - HIGH → frequent alerts
  - MEDIUM → moderate alerts
  - LOW → minimal alerts

---

### 💊 Smart Dispense Verification
- Servo-controlled pill dispensing
- Load cell (HX711) measures weight before and after dispense
- Determines:
  - Successful dispense
  - Failed dispense
- Ensures real-world validation instead of assumptions

---

### 🌐 Ethernet-Based Communication
- Uses lwIP stack for networking
- Sends real-time data to Flask server via HTTP
- API endpoints:
  - `/api/events`
  - `/api/twin/update`
  - `/api/dispense_verification`
  - `/api/command`

---

### 🧠 Digital Twin (Live Dashboard)
- Real-time synchronization between MCU and server
- Displays:
  - Reminder state
  - AI risk level
  - Servo state
  - Weight readings
- Supports remote commands:
  - ACK
  - SNOOZE
  - DISPENSE
  - TAKEN

---

### 💾 Dual Logging System
- **Onboard Flash Logging**
  - Stores all events locally
  - Recovers logs after reboot
- **Server Logging**
  - Sends logs via Ethernet to Flask server
  - Stored in SQLite database

---

### 🔄 Fault Recovery & Reliability
- Flash log replay on reboot
- Reconstructs:
  - Risk history
  - Reminder states
- Ensures no data loss

---

## 🛠️ System Architecture

### Embedded System
- Board: FRDM-K66F (ARM Cortex-M4)
- RTOS: FreeRTOS
- Communication: lwIP Ethernet
- Peripherals:
  - DS3231 RTC (I2C)
  - SSD1306 OLED Display
  - HX711 Load Cell
  - Servo Motor
  - Buzzer
  - Push Buttons (ACK / Snooze)

---

### Server
- Python Flask backend
- SQLite database
- REST API communication
- Digital twin dashboard

---

## ⚙️ Technologies Used
- C (Embedded Firmware)
- FreeRTOS
- lwIP Networking Stack
- Python (Flask)
- SQLite
- I2C / PWM / ADC interfaces

---

## 🧪 How It Works

1. System schedules medication using RTC
2. At dose time:
   - AI checks risk level
   - May trigger pre-alert (high risk only)
3. Reminder activates:
   - Buzzer + notification
4. User action:
   - Takes medication OR snoozes
5. System verifies using weight sensor:
   - Detects pill removal
6. Logs event locally and sends to server
7. Digital twin updates in real-time

---

## 📊 AI Justification
This system is AI-enabled because it:
- Learns from historical user behavior
- Uses dynamic risk scoring
- Adapts reminder frequency and intensity
- Makes decisions based on patterns, not fixed rules

Unlike static systems, it evolves with user habits.

---


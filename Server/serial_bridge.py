import serial
import requests
import time
from datetime import datetime

print("BRIDGE VERSION: UNIFIED_AI_EVENTS_TWIN")

COM_PORT = "COM5"
BAUD_RATE = 115200

FLASK_EVENTS_URL = "http://127.0.0.1:5000/api/events"
FLASK_AI_URL = "http://127.0.0.1:5000/api/ai_lines"
FLASK_TWIN_URL = "http://127.0.0.1:5000/api/twin/update"

# Optional behavior
AUTO_ACK_ON_ACTIVE = False   # True = send CMD,ACK when reminder becomes active
SERIAL_TIMEOUT = 0.2

# Track state transitions
was_active = False


# ------------------------------------------------------------
# TWIN parsing
# ------------------------------------------------------------
def parse_twin_line(line: str):
    """
    Parse:
      TWIN,<timestamp_ms>,<reminder_active>,<ai_high_risk>,<servo_state_deg>,<weight_grams>
    Example:
      TWIN,62605,0,0,0,-1
    """
    if not line.startswith("TWIN,"):
        return None

    parts = line.strip().split(",")
    if len(parts) != 6:
        return None

    try:
        return {
            "timestamp_ms": int(parts[1]),
            "reminder_active": int(parts[2]),
            "ai_high_risk": int(parts[3]),
            "servo_state_deg": int(parts[4]),
            "weight_grams": int(parts[5]),
        }
    except Exception:
        return None


def post_twin_to_flask(twin_data: dict):
    try:
        r = requests.post(FLASK_TWIN_URL, json=twin_data, timeout=3)
        # print("POST TWIN:", r.status_code, twin_data)
    except Exception as e:
        print("POST TWIN error:", e)


def pretty_print_twin(twin_data: dict, raw_line: str):
    reminder_text = "ACTIVE" if int(twin_data["reminder_active"]) == 1 else "IDLE"
    risk_text = "HIGH" if int(twin_data["ai_high_risk"]) == 1 else "LOW"

    servo = twin_data["servo_state_deg"]
    weight = twin_data["weight_grams"]

    servo_text = "UNKNOWN" if servo < 0 else str(servo)
    weight_text = "UNKNOWN" if weight < 0 else str(weight)

    # print("--------------------------------------------------")
    # print("✅ TWIN PARSED:")
    # print(f"   Time:        {twin_data['timestamp_ms']} ms")
    # print(f"   Reminder:    {reminder_text}")
    # print(f"   AI Risk:     {risk_text}")
    # print(f"   Servo:       {servo_text}")
    # print(f"   Weight:      {weight_text}")
    # print(f"   RAW:         {raw_line}")
    # print("--------------------------------------------------")


# ------------------------------------------------------------
# LOG line parsing -> final dose event payload
# ------------------------------------------------------------
def parse_kv_log_line(line: str):
    """
    Parse MCU line like:
    LOG,SEQ=5,TS=0000-00-00 13:48:05,TYPE=DOSE_EVENT,MED=MedB,STATUS=TAKEN,REM=1,DELAY=0,VAL=0,EXTRA=0
    """
    if not line.startswith("LOG,"):
        return None

    try:
        parts = line.strip().split(",")
        data = {}

        for part in parts[1:]:
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            data[k.strip()] = v.strip()

        return data
    except Exception:
        return None


def log_to_event_payload(log_data: dict):
    """
    Convert parsed LOG line into Flask /api/events payload
    ONLY for final medication outcome logs.
    """
    if not log_data:
        return None

    event_type = log_data.get("TYPE", "").upper()
    if event_type != "DOSE_EVENT":
        return None

    status = log_data.get("STATUS", "").upper()
    if status not in ("TAKEN", "MISSED", "SNOOZED"):
        return None

    ts = log_data.get("TS", "").strip()
    med_id = log_data.get("MED", "").strip() or "unknown"

    try:
        reminder_count = int(log_data.get("REM", "0"))
    except Exception:
        reminder_count = 0

    try:
        delay_minutes = int(log_data.get("DELAY", "0"))
    except Exception:
        delay_minutes = 0

    # If MCU timestamp has fake date 0000-00-00, replace with PC timestamp
    if ts.startswith("0000-00-00") or not ts:
        timestamp = datetime.now().isoformat(timespec="seconds")
    else:
        try:
            timestamp = datetime.fromisoformat(ts.replace(" ", "T")).isoformat(timespec="seconds")
        except Exception:
            timestamp = datetime.now().isoformat(timespec="seconds")

    return {
        "timestamp": timestamp,
        "med_id": med_id,
        "status": status,
        "reminder_count": reminder_count,
        "delay_minutes": delay_minutes,
    }


def post_event_to_flask(event: dict):
    try:
        r = requests.post(FLASK_EVENTS_URL, json=event, timeout=3)
        # print("POST EVENT:", r.status_code, event)
    except Exception as e:
        print("POST EVENT error:", e)


# ------------------------------------------------------------
# AI boot sync
# ------------------------------------------------------------
# def fetch_ai_lines():
#     try:
#         r = requests.get(FLASK_AI_URL, timeout=3)
#         r.raise_for_status()
#         text = r.text.strip()
#         if not text:
#             return []
#         return [line.strip() for line in text.splitlines() if line.strip()]
#     except Exception as e:
#         print("AI fetch error:", e)
#         return []



def fetch_ai_lines():
    try:
        print("Fetching AI lines from Flask...")
        r = requests.get(FLASK_AI_URL, timeout=11)
        r.raise_for_status()

        text = r.text.strip()

        print("Raw AI response:", text)   # 

        if not text:
            return []

        print("AI fetch HTTP OK")
        return [line.strip() for line in text.splitlines() if line.strip()]

    except Exception as e:
        print("AI fetch error:", e)
        return []


# def send_ai_boot_packet(ser, lines):
#     for line in lines:
#         ser.write((line + "\n").encode("utf-8"))
#         ser.flush()
#         print("TX:", line)
#         time.sleep(0.5)

#     ser.write(b"AI_DONE\n")
#     ser.flush()
#     print("TX: AI_DONE")






def wait_for_serial_token(ser, expected, timeout=2.0):
    import time

    end_time = time.time() + timeout
    while time.time() < end_time:
        raw = ser.readline()
        if not raw:
            continue

        line = raw.decode(errors="ignore").strip()
        if line:
            print("RX during AI sync:", line)

        if line == expected:
            return True

    return False


# def send_ai_boot_packet(ser, lines):
#     import time

#     print("Sending full AI boot packet with ACK handshake...")

#     # small pause after SYS,AI_READY
#     time.sleep(0.3)

#     for line in lines:
#         msg = line + "\r\n"
#         ser.write(msg.encode("utf-8"))
#         ser.flush()
#         print("TX:", line)

#         ok = wait_for_serial_token(ser, "SYS,AI_LINE_OK", timeout=2.0)
#         if not ok:
#             print("ERROR: no ACK for line:", line)
#             return False

#     ser.write(b"AI_DONE\r\n")
#     ser.flush()
#     print("TX: AI_DONE")

#     done = wait_for_serial_token(ser, "SYS,AI_SYNC_DONE", timeout=2.0)
#     if not done:
#         print("ERROR: no AI sync done ACK")
#         return False

#     return True




# def send_line_slow(ser, text, char_delay=0.003):
#     import time
#     payload = text + "\r\n"
#     for ch in payload:
#         ser.write(ch.encode("utf-8"))
#         ser.flush()
#         time.sleep(char_delay)

# def send_ai_boot_packet(ser, lines):
#     import time

#     print("Sending filtered AI boot packet WITH ACK handshake...")

#     filtered = [line for line in lines if line.startswith("AI,MedA,")]

#     if not filtered:
#         print("No matching AI lines for current test.")
#         return False

#     for line in filtered:
#         print("TX:", line)
#         send_line_slow(ser, line, char_delay=0.003)

#         if not wait_for_serial_token(ser, "SYS,AI_LINE_OK", timeout=6.0):
#             print("ERROR: no ACK for line:", line)
#             return False

#         time.sleep(0.2)

#     print("TX: AI_DONE")
#     send_line_slow(ser, "AI_DONE", char_delay=0.003)

#     if not wait_for_serial_token(ser, "SYS,AI_SYNC_DONE", timeout=6.0):
#         print("ERROR: no final AI sync done ACK")
#         return False

#     print("AI boot packet sent successfully.")
#     return True









def send_line_slow(ser, text, char_delay=0.003):
    import time
    payload = text + "\r\n"
    for ch in payload:
        ser.write(ch.encode("utf-8"))
        ser.flush()
        time.sleep(char_delay)




def wait_for_serial_token_multi(ser, tokens, timeout=6.0):
    import time

    deadline = time.time() + timeout

    while time.time() < deadline:
        raw = ser.readline()
        if not raw:
            continue

        try:
            line = raw.decode("utf-8", errors="ignore").strip()
        except Exception:
            continue

        if not line:
            continue

        print("RX during AI sync:", line)

        for token in tokens:
            if token in line:
                return token

    return None




def send_ai_boot_packet(ser, lines):
    import time

    print("Sending full AI boot packet WITH retries...")

    ai_lines = [line for line in lines if line.startswith("AI,")]
    if not ai_lines:
        print("No AI lines to send.")
        return False

    applied_count = 0
    bad_count = 0

    for line in ai_lines:
        delivered = False

        for attempt in range(3):
            print(f"TX attempt {attempt+1}: {line}")
            send_line_slow(ser, line, char_delay=0.003)

            token = wait_for_serial_token_multi(
                ser,
                ["SYS,AI_LINE_OK", "SYS,AI_LINE_BAD"],
                timeout=6.0
            )

            if token == "SYS,AI_LINE_OK":
                print(f"AI line applied: {line}")
                applied_count += 1
                delivered = True
                break

            if token == "SYS,AI_LINE_BAD":
                print(f"AI line rejected by MCU: {line}")
                bad_count += 1
                delivered = True
                break

            print("No response, retrying...")
            time.sleep(0.5)

        if not delivered:
            print(f"ERROR: failed to deliver line after retries: {line}")
            return False

        time.sleep(0.2)

    print("TX: AI_DONE")
    send_line_slow(ser, "AI_DONE", char_delay=0.003)

    if not wait_for_serial_token(ser, "SYS,AI_SYNC_DONE", timeout=6.0):
        print("ERROR: no final AI sync done ACK")
        return False

    print(f"AI boot packet sent successfully. applied={applied_count}, bad={bad_count}")
    return True








# def send_ai_boot_packet(ser, lines):
#     import time

#     print("Sending filtered AI boot packet WITH retries...")

#     filtered = [line for line in lines if line.startswith("AI,")]
#     if not filtered:
#         print("No matching AI lines for current test.")
#         return False

#     line = filtered[0]

#     for attempt in range(3):
#         print(f"TX attempt {attempt+1}: {line}")
#         send_line_slow(ser, line, char_delay=0.003)

#         if wait_for_serial_token(ser, "SYS,AI_LINE_OK", timeout=6.0):
#             print("AI line ACK received")
#             break

#         print("No ACK, retrying...")
#         time.sleep(0.5)
#     else:
#         print("ERROR: failed to deliver AI line after retries")
#         return False

#     time.sleep(0.3)
#     print("TX: AI_DONE")
#     send_line_slow(ser, "AI_DONE", char_delay=0.003)

#     if not wait_for_serial_token(ser, "SYS,AI_SYNC_DONE", timeout=6.0):
#         print("ERROR: no final AI sync done ACK")
#         return False

#     print("AI boot packet sent successfully.")
#     return True








# def send_ai_boot_packet(ser, lines):
#     import time

#     print("Sending full AI boot packet WITH ACK handshake...")

#     for line in lines:
#         msg = line + "\r\n"
#         ser.write(msg.encode("utf-8"))
#         ser.flush()
#         print("TX:", line)

#         if not wait_for_serial_token(ser, "SYS,AI_LINE_OK", timeout=6.0):
#             print("ERROR: no ACK for line:", line)
#             return False

#         time.sleep(0.2)

#     ser.write(b"AI_DONE\r\n")
#     ser.flush()
#     print("TX: AI_DONE")

#     if not wait_for_serial_token(ser, "SYS,AI_SYNC_DONE", timeout=6.0):
#         print("ERROR: no final AI sync done ACK")
#         return False

#     print("AI boot packet sent successfully.")
#     return True












# def send_ai_boot_packet(ser, lines):
#     import time

#     # 🔥 TEMP: ignore server lines, send ONE clean test
#     test_lines = ["AI,MedA,1,15"]

#     print("Sending TEST AI line only...")

#     # Wait a bit after READY
#     time.sleep(0.3)

#     for line in test_lines:
#         msg = line + "\r\n"   # ✅ FIXED
#         ser.write(msg.encode("utf-8"))
#         ser.flush()
#         print("TX:", line)
#         time.sleep(0.5)       # ✅ SLOWER (very important)

#     ser.write(b"AI_DONE\r\n")  # ✅ FIXED
#     ser.flush()
#     print("TX: AI_DONE")
#     time.sleep(0.2)

# ------------------------------------------------------------
# Optional auto-ACK
# ------------------------------------------------------------
def handle_auto_ack(ser, twin_data: dict):
    global was_active

    now_active = bool(int(twin_data["reminder_active"]))

    if AUTO_ACK_ON_ACTIVE and now_active and not was_active:
        print("🔔 Reminder ACTIVE -> sending CMD,ACK")
        ser.write(b"CMD,ACK\r\n")
        ser.flush()

    was_active = now_active


# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------
def main():
    global was_active

    print(f"Opening serial port {COM_PORT} at {BAUD_RATE}...")
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
    time.sleep(2)

    print("Unified bridge running...")
    print(f"Auto-ACK on active: {'ON' if AUTO_ACK_ON_ACTIVE else 'OFF'}")
    ai_sent_for_this_boot = False
    was_active = False

    while True:
        try:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode(errors="ignore").strip()
            if not line:
                continue

            print("RX:", line)

            # ------------------------------------------------
            # 1) TWIN snapshot lines
            # ------------------------------------------------
            twin_data = parse_twin_line(line)
            if twin_data is not None:
                pretty_print_twin(twin_data, line)
                post_twin_to_flask(twin_data)
                handle_auto_ack(ser, twin_data)
                continue

            # ------------------------------------------------
            # 2) Structured LOG lines -> Flask events
            # ------------------------------------------------
            log_data = parse_kv_log_line(line)
            if log_data is not None:
                event = log_to_event_payload(log_data)
                if event is not None:
                    post_event_to_flask(event)
                continue

            # ------------------------------------------------
            # 3) Boot / AI sync handling
            # ------------------------------------------------
            if line == "SYS,BOOT":
                print("Trigger reset on BOOT")
                ai_sent_for_this_boot = False
                was_active = False
                continue

            # if line == "SYS,AI_READY" and not ai_sent_for_this_boot:
            #     print("Trigger matched: SYS,AI_READY")
            #     ai_lines = fetch_ai_lines()
            #     print("Fetched AI lines:", ai_lines)

            #     time.sleep(0.2)
            #     send_ai_boot_packet(ser, ai_lines)
            #     ai_sent_for_this_boot = True
            #     continue


            if line == "SYS,AI_READY" and not ai_sent_for_this_boot:

                print("Trigger matched: SYS,AI_READY")
                ai_lines = fetch_ai_lines()
                print("Fetched AI lines:", ai_lines)

                # IMPORTANT: give MCU time to enter its RX loop cleanly
                time.sleep(2.0)

                ok = send_ai_boot_packet(ser, ai_lines)

                if ok:

                    ai_sent_for_this_boot = True
                    print("AI sync marked complete for this boot")
                else:
                    ai_sent_for_this_boot = False
                    print("AI sync failed; will retry if SYS,AI_READY appears again")

                continue

            # ------------------------------------------------
            # 4) Optional visibility for useful plain-text lines
            # ------------------------------------------------
            if any(x in line for x in ["SYS,", "Reminder", "dispense", "ACK", "SNOOZE", "AI "]):
                print("INFO:", line)

        except KeyboardInterrupt:
            print("Stopped by user.")
            break
        except serial.SerialException as e:
            print("SERIAL ERROR:", e)
            print("Check COM port, baud rate, cable, or whether another app is using the port.")
            time.sleep(1)
        except Exception as e:
            print("ERROR:", e)
            time.sleep(1)

    try:
        ser.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()


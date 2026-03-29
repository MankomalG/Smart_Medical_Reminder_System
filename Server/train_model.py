import sqlite3
import joblib
from datetime import datetime
from sklearn.linear_model import LogisticRegression

DB_NAME = "med_logs.db"
MODEL_FILE = "med_model.pkl"


def parse_dt(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "").replace(" ", "T"))
    except Exception:
        return None


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def build_features(dt: datetime, reminders: int, delay: int):
    hour = dt.hour if dt else 0
    dow = dt.weekday() if dt else 0

    x = []

    # hour normalized
    x.append(hour / 23.0 if 23 else 0.0)

    # day-of-week one-hot
    for i in range(7):
        x.append(1.0 if dow == i else 0.0)

    # reminders normalized
    x.append(clamp(reminders / 10.0, 0.0, 1.0))

    # delay normalized
    x.append(clamp(delay / 60.0, 0.0, 1.0))

    # interaction term
    x.append((hour / 23.0) * clamp(reminders / 10.0, 0.0, 1.0))

    return x


def load_events():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT timestamp, med_id, status, reminder_count, delay_minutes
        FROM events
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    events = []
    for r in rows:
        events.append({
            "timestamp": r[0],
            "med_id": r[1],
            "status": r[2],
            "reminder_count": r[3],
            "delay_minutes": r[4],
        })
    return events


def main():
    events = load_events()

    if len(events) < 10:
        print("Not enough data to train. Need at least 10 events.")
        return

    X = []
    y = []

    for e in events:
        dt = parse_dt(e["timestamp"])
        if dt is None:
            continue

        status = str(e["status"]).upper()

        # Train as binary classification:
        # MISSED = 1
        # TAKEN / SNOOZED = 0
        label = 1 if status == "MISSED" else 0

        X.append(
            build_features(
                dt,
                int(e["reminder_count"]),
                int(e["delay_minutes"])
            )
        )
        y.append(label)

    if len(X) < 10:
        print("Not enough valid parsed rows to train.")
        return

    unique_labels = set(y)
    if len(unique_labels) < 2:
        print("Training failed: need both MISSED and non-MISSED examples.")
        return

    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)

    joblib.dump(model, MODEL_FILE)

    print(f"Model trained successfully and saved to: {MODEL_FILE}")
    print(f"Total rows used: {len(X)}")
    print(f"MISSED rows: {sum(y)}")
    print(f"Non-MISSED rows: {len(y) - sum(y)}")
    print(f"Feature count: {len(X[0])}")


if __name__ == "__main__":
    main()
import sqlite3

DB_NAME = "med_logs.db"

# Map all old/variant IDs to the exact firmware IDs you want
NORMALIZATION_MAP = {
    "MED_A": "MedA",
    "med_a": "MedA",
    "MEDA": "MedA",
    "meda": "MedA",
    "MedA": "MedA",

    "MED_B": "MedB",
    "med_b": "MedB",
    "MEDB": "MedB",
    "medb": "MedB",
    "MedB": "MedB",

    "MED_C": "MedC",
    "med_c": "MedC",
    "MEDC": "MedC",
    "medc": "MedC",
    "MedC": "MedC",

    "MED_D": "MedD",
    "med_d": "MedD",
    "MEDD": "MedD",
    "medd": "MedD",
    "MedD": "MedD",

    "MED_E": "MedE",
    "med_e": "MedE",
    "MEDE": "MedE",
    "mede": "MedE",
    "MedE": "MedE",
}


def show_distinct(cur, title):
    print(f"\n{title}")
    rows = cur.execute("SELECT DISTINCT med_id FROM events ORDER BY med_id").fetchall()
    if not rows:
        print("  (none)")
    else:
        for r in rows:
            print(" ", r[0])


def main():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    show_distinct(cur, "Before cleanup:")

    rows = cur.execute("SELECT id, med_id FROM events").fetchall()

    updated = 0
    for row_id, med_id in rows:
        if med_id in NORMALIZATION_MAP:
            normalized = NORMALIZATION_MAP[med_id]
            if normalized != med_id:
                cur.execute(
                    "UPDATE events SET med_id=? WHERE id=?",
                    (normalized, row_id)
                )
                updated += 1

    conn.commit()

    show_distinct(cur, "After cleanup:")
    print(f"\nUpdated rows: {updated}")

    conn.close()


if __name__ == "__main__":
    main()
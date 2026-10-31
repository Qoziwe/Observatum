import json
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"

SURVEY_META = {
    "title": "Urban Digital Infrastructure & Internet Connectivity Experience in Kuala Lumpur (SDG 9 Research)",
    "description": (
        "Hello! We are a group of students from Asia Pacific University (APU) conducting an audience analysis "
        "aligned with UN Sustainable Development Goal 9 (Industry, Innovation, and Infrastructure). "
        "This survey investigates the issue of frequent network disconnections, bandwidth throttling, "
        "and inconsistent connection speeds in Kuala Lumpur."
    ),
    "note": "Note: Students currently enrolled in the DGCC (Digital Communication & Collaboration) module are NOT eligible to participate in this survey.",
}

OPTIONS = {
    "q2_dgcc_enrolled": [
        "No (Eligible to proceed)",
        "Yes (Please do not submit this form, thank you!)",
    ],
    "q3_occupation": [
        "University / College Student",
        "Working Professional (Office-based)",
        "Remote / Hybrid Worker",
        "Business Owner / Freelancer",
        "Other",
    ],
    "q4_area": [
        "Bukit Jalil / Sri Petaling / Sungai Besi",
        "KL City Centre (KLCC / Bukit Bintang / Cheras)",
        "Bangsar / Mid Valley / Brickfields",
        "Subang Jaya / Sunway / Petaling Jaya",
        "Setapak / Wangsa Maju / Ampang",
        "Cyberjaya / Serdang / Puchong",
        "Other",
    ],
    "q5_mobile_provider": [
        "CelcomDigi",
        "Maxis / Hotlink",
        "U Mobile",
        "Unifi Mobile",
        "Yes 5G (YTL Communications)",
        "Other",
    ],
    "q6_broadband_provider": [
        "Unifi (Telekom Malaysia)",
        "TIME dotCom",
        "Maxis Home Fibre",
        "CelcomDigi Fibre",
        "Campus / Accommodation Shared Wi-Fi",
        "I only use Mobile Data / Hotspot",
    ],
    "q7_disconnect_freq": [
        "Multiple times a day",
        "Once a day",
        "A few times a week",
        "Rarely (Once or twice a month)",
        "Never",
    ],
    "q8_phantom_signal": [
        "Yes, very frequently",
        "Yes, occasionally",
        "Rarely",
        "No, never",
    ],
    "q9_worst_conditions": [
        "Evening peak hours (7:00 PM – 11:00 PM)",
        "Daytime work/study hours (9:00 AM – 5:00 PM)",
        "During heavy rain / bad weather in KL",
        "Inside high-rise buildings (Condominiums, malls, campus blocks)",
        "While commuting (LRT/MRT/Highways)",
    ],
    "q11_impacted_activities": [
        "Academic tasks (Accessing Moodle/Teams, submitting assignments, online classes)",
        "Digital payments & E-Wallets (Failing to load QR codes/Touch ’n Go at checkout counters)",
        "Transport & Navigation (Booking Grab, loading Google Maps/Waze)",
        "Video/Voice calls with family, friends, or teammates (Lagging, robotic voice, dropping out)",
        "Entertainment & Gaming (High ping, buffering streams)",
        "Remote work / Cloud collaboration",
    ],
    "q12_coping_mechanisms": [
        "Switching between Wi-Fi and Mobile Hotspot constantly",
        "Buying extra mobile data passes / secondary SIM card from another provider",
        "Moving to another physical location (e.g., cafe, library, near a window) just to get a signal",
        "Restarting the router or toggling Airplane Mode repeatedly",
        "Missing deadlines or delaying urgent tasks",
    ],
    "q13_support_satisfaction": [
        "Very Dissatisfied (Trapped in unhelpful AI chatbot loops, slow resolution)",
        "Dissatisfied (Took too long to fix the issue)",
        "Neutral (Issue resolved, but average experience)",
        "Satisfied (Fast and helpful support)",
        "I have never contacted support because I don’t think they will help",
    ],
    "q14_price_value_match": [
        "Strongly Disagree (I pay for high speed, but get unstable service)",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly Agree",
    ],
    "q15_auto_backup_support": [
        "Yes, definitely! That would solve a major pain point.",
        "Maybe, depending on how seamlessly it works.",
        "No, I don’t think it is necessary.",
    ],
    "q16_top_improvements": [
        "Real-time outage & tower congestion map inside the app (with exact repair countdowns)",
        "Faster human customer support (bypassing repetitive AI chatbots during outages)",
        "Upgrading indoor building/condominium wiring and signal repeaters",
        "Automatic bill rebates when network uptime falls below standard",
        "Automatic backup eSIM / hotspot data during fiber cuts",
    ],
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    sql = (
        "CREATE TABLE IF NOT EXISTS responses ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "receipt_code TEXT NOT NULL UNIQUE, "
        "created_at TEXT NOT NULL, "
        "is_demo INTEGER NOT NULL DEFAULT 0, "
        "q1_participant_id TEXT NOT NULL, "
        "q2_dgcc_enrolled TEXT NOT NULL, "
        "q3_occupation TEXT NOT NULL, "
        "q4_area TEXT NOT NULL, "
        "q5_mobile_provider TEXT NOT NULL, "
        "q6_broadband_provider TEXT NOT NULL, "
        "q7_disconnect_freq TEXT NOT NULL, "
        "q8_phantom_signal TEXT NOT NULL, "
        "q9_worst_conditions TEXT NOT NULL, "
        "q10_frustration_scale INTEGER NOT NULL, "
        "q11_impacted_activities TEXT NOT NULL, "
        "q12_coping_mechanisms TEXT NOT NULL, "
        "q13_support_satisfaction TEXT NOT NULL, "
        "q14_price_value_match TEXT NOT NULL, "
        "q15_auto_backup_support TEXT NOT NULL, "
        "q16_top_improvements TEXT NOT NULL, "
        "q17_memorable_moment TEXT NOT NULL"
        ");"
    )
    with get_connection() as conn:
        conn.execute(sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_created_at ON responses(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_is_demo ON responses(is_demo);")
        conn.commit()


def insert_response(record: dict, is_demo: bool = False) -> dict:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    sql = (
        "INSERT INTO responses ("
        "receipt_code, created_at, is_demo, "
        "q1_participant_id, q2_dgcc_enrolled, q3_occupation, q4_area, "
        "q5_mobile_provider, q6_broadband_provider, "
        "q7_disconnect_freq, q8_phantom_signal, q9_worst_conditions, "
        "q10_frustration_scale, q11_impacted_activities, q12_coping_mechanisms, "
        "q13_support_satisfaction, q14_price_value_match, "
        "q15_auto_backup_support, q16_top_improvements, q17_memorable_moment"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with get_connection() as conn:
        cur = conn.execute(
            sql,
            (
                record["receipt_code"],
                now_iso,
                1 if is_demo else 0,
                record["q1_participant_id"],
                record.get("q2_dgcc_enrolled", "N/A"),
                record["q3_occupation"],
                record["q4_area"],
                record["q5_mobile_provider"],
                record["q6_broadband_provider"],
                record["q7_disconnect_freq"],
                record["q8_phantom_signal"],
                json.dumps(record["q9_worst_conditions"], ensure_ascii=False),
                int(record["q10_frustration_scale"]),
                json.dumps(record["q11_impacted_activities"], ensure_ascii=False),
                json.dumps(record["q12_coping_mechanisms"], ensure_ascii=False),
                record["q13_support_satisfaction"],
                record["q14_price_value_match"],
                record["q15_auto_backup_support"],
                json.dumps(record["q16_top_improvements"], ensure_ascii=False),
                record.get("q17_memorable_moment", "").strip(),
            ),
        )
        row_id = cur.lastrowid
        conn.commit()
    return {"id": row_id, "receipt_code": record["receipt_code"], "created_at": now_iso}


def fetch_all_responses() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM responses ORDER BY id DESC").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        for k in ("q9_worst_conditions", "q11_impacted_activities", "q12_coping_mechanisms", "q16_top_improvements"):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                d[k] = []
        result.append(d)
    return result


def delete_response_by_id(row_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM responses WHERE id = ?", (row_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_demo_responses() -> int:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM responses WHERE is_demo = 1")
        conn.commit()
        return cur.rowcount


def clear_all_responses() -> int:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM responses")
        conn.commit()
        return cur.rowcount


DEMO_STORIES = [
    "During my Moodle timed quiz at Bukit Jalil condo, Unifi dropped for 12 minutes right before submission.",
    "Stuck at LRT Sri Petaling station in heavy rain — 5G showed full bars on U Mobile but Grab refused to load for 25 mins.",
    "Touch ’n Go eWallet QR failed to load at Pavilion checkout counter with a queue of 8 people behind me.",
    "Final year project presentation on MS Teams froze mid-demo; had to tether to a friend’s Maxis hotspot.",
    "Trapped in an endless telco AI chatbot loop for 45 minutes while fiber was down across our entire block in Setapak.",
    "Evening 9 PM throttling makes cloud IDE and Git pushes time out constantly in student accommodation.",
    "Inside high-rise condo elevator lobby and lower floors, signal shows 4 bars of 4G but zero packets go through.",
    "During thunderstorm in Cyberjaya, both home fiber and mobile data became unusable during a client call.",
]


def seed_demo_data(count: int = 35) -> int:
    rng = random.Random()
    inserted = 0
    for _ in range(count):
        occ = rng.choices(OPTIONS["q3_occupation"], weights=[55, 16, 15, 9, 5], k=1)[0]
        area = rng.choices(OPTIONS["q4_area"], weights=[34, 16, 12, 14, 11, 10, 3], k=1)[0]
        mobile = rng.choices(OPTIONS["q5_mobile_provider"], weights=[28, 24, 22, 13, 10, 3], k=1)[0]
        broadband = rng.choices(OPTIONS["q6_broadband_provider"], weights=[32, 20, 11, 9, 18, 10], k=1)[0]
        freq = rng.choices(OPTIONS["q7_disconnect_freq"], weights=[30, 25, 27, 13, 5], k=1)[0]
        phantom = rng.choices(OPTIONS["q8_phantom_signal"], weights=[42, 36, 16, 6], k=1)[0]
        q9 = rng.sample(OPTIONS["q9_worst_conditions"], k=rng.randint(2, 4))
        frustration = rng.choices([1, 2, 3, 4, 5], weights=[3, 7, 18, 38, 34], k=1)[0]
        q11 = rng.sample(OPTIONS["q11_impacted_activities"], k=rng.randint(2, 4))
        q12 = rng.sample(OPTIONS["q12_coping_mechanisms"], k=rng.randint(2, 3))
        q13 = rng.choices(OPTIONS["q13_support_satisfaction"], weights=[38, 26, 14, 6, 16], k=1)[0]
        q14 = rng.choices(OPTIONS["q14_price_value_match"], weights=[36, 34, 16, 10, 4], k=1)[0]
        q15 = rng.choices(OPTIONS["q15_auto_backup_support"], weights=[74, 21, 5], k=1)[0]
        q16 = rng.sample(OPTIONS["q16_top_improvements"], k=2)
        story = rng.choice(DEMO_STORIES) if rng.random() < 0.65 else ""
        pid = f"TP0{rng.randint(61000, 89999)}" if "Student" in occ else f"IC-{rng.randint(1000, 9999)}"
        code = f"SDG9-DEMO-{rng.randint(100000, 999999)}"
        try:
            insert_response(
                {
                    "receipt_code": code,
                    "q1_participant_id": pid,
                    "q2_dgcc_enrolled": "No (Eligible to proceed)",
                    "q3_occupation": occ,
                    "q4_area": area,
                    "q5_mobile_provider": mobile,
                    "q6_broadband_provider": broadband,
                    "q7_disconnect_freq": freq,
                    "q8_phantom_signal": phantom,
                    "q9_worst_conditions": q9,
                    "q10_frustration_scale": frustration,
                    "q11_impacted_activities": q11,
                    "q12_coping_mechanisms": q12,
                    "q13_support_satisfaction": q13,
                    "q14_price_value_match": q14,
                    "q15_auto_backup_support": q15,
                    "q16_top_improvements": q16,
                    "q17_memorable_moment": story,
                },
                is_demo=True,
            )
            inserted += 1
        except sqlite3.IntegrityError:
            continue
    return inserted

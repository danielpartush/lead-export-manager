import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO

DB_NAME = "leads.db"

st.set_page_config(page_title="Lead Export Manager", layout="wide")

# ---------- עיצוב ----------
st.markdown("""
<style>
.main-title {
    text-align: center;
    font-size: 42px;
    font-weight: 900;
    margin-bottom: 10px;
}
.sub-title {
    text-align: center;
    font-size: 20px;
    color: #666;
    margin-bottom: 35px;
}
.stButton > button {
    height: 115px;
    font-size: 24px !important;
    font-weight: 800 !important;
    border-radius: 22px !important;
    border: 2px solid #ddd !important;
}
.small-btn > button {
    height: 45px !important;
    font-size: 16px !important;
}
</style>
""", unsafe_allow_html=True)


# ---------- פונקציות ----------
def now_str():
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def clean_tz(value):
    if pd.isna(value):
        return ""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits.zfill(9) if digits else ""


def clean_phone(value):
    if pd.isna(value):
        return ""

    phone = "".join(ch for ch in str(value) if ch.isdigit())

    if phone.startswith("972"):
        phone = "0" + phone[3:]

    if len(phone) == 9 and phone.startswith("5"):
        phone = "0" + phone

    if len(phone) == 10 and phone.startswith("05"):
        return phone

    return ""


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        tz TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        birth_date TEXT,
        phone TEXT,
        phone_clean TEXT,
        id_issue_date TEXT,
        created_at TEXT,
        updated_at TEXT,
        source TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS export_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        tz TEXT,
        exported_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_lead(row, source="ידני"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    tz = clean_tz(row.get("תז", ""))
    if not tz:
        conn.close()
        return False

    phone_clean = clean_phone(row.get("מס טלפון", ""))

    c.execute("SELECT created_at FROM leads WHERE tz = ?", (tz,))
    existing = c.fetchone()

    if existing:
        created_at = existing[0]
        updated_at = now_str()

        c.execute("""
        UPDATE leads
        SET first_name=?, last_name=?, birth_date=?, phone=?, phone_clean=?,
            id_issue_date=?, updated_at=?, source=?
        WHERE tz=?
        """, (
            row.get("שם פרטי", ""),
            row.get("שם משפחה", ""),
            row.get("תאריך לידה", ""),
            row.get("מס טלפון", ""),
            phone_clean,
            row.get("תאריך הנפקת תז", ""),
            updated_at,
            source,
            tz
        ))
    else:
        created_at = now_str()
        updated_at = created_at

        c.execute("""
        INSERT INTO leads
        (tz, first_name, last_name, birth_date, phone, phone_clean,
         id_issue_date, created_at, updated_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tz,
            row.get("שם פרטי", ""),
            row.get("שם משפחה", ""),
            row.get("תאריך לידה", ""),
            row.get("מס טלפון", ""),
            phone_clean,
            row.get("תאריך הנפקת תז", ""),
            created_at,
            updated_at,
            source
        ))

    conn.commit()
    conn.close()
    return True


def get_leads():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    return df


def add_client(name):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO clients (name, created_at) VALUES (?, ?)",
            (name, now_str())
        )
        conn.commit()
    except:
        pass
    conn.close()


def get_clients():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM clients ORDER BY name", conn)
    conn.close()
    return df


def export_for_client(client_name, amount):
    conn = sqlite3.connect(DB_NAME)

    query = """
    SELECT *
    FROM leads
    WHERE phone_clean != ''
    AND tz NOT IN (
        SELECT tz FROM export_history WHERE client_name = ?
    )
    LIMIT ?
    """

    df = pd.read_sql_query(query, conn, params=(client_name, amount))

    c = conn.cursor()
    for tz in df["tz"].tolist():
        c.execute(
            "INSERT INTO export_history (client_name, tz, exported_at) VALUES (?, ?, ?)",
            (client_name, tz, now_str())
        )

    conn.commit()
    conn.close()
    return df


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="לידים")
    return output.getvalue()


init_db()

if "page" not in st.session_state:
    st.session_state.page = "home"


def go(page):
    st.session_state.page = page
    st.rerun()


# ---------- מסך בית ----------
if st.session_state.page == "home":
    st.markdown('<div class="main-title">🚀 Lead Export Manager</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">מערכת לניהול לידים, לקוחות, ייצואים וחיפוש רשומות</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📤\n\nהעלאת קובץ", use_container_width=True):
            go("upload")

    with col2:
        if st.button("✍️\n\nהעלאת רשומה ידנית", use_container_width=True):
            go("manual")

    with col3:
        if st.button("📦\n\nמשיכת רשומות לפי לקוח", use_container_width=True):
            go("export")

    col4, col5 = st.columns(2)

    with col4:
        if st.button("📊\n\nכמה רשומות קיימות", use_container_width=True):
            go("reports")

    with col5:
        if st.button("🔎\n\nחיפוש לפי תז", use_container_width=True):
            go("search")

    st.stop()


# ---------- כפתור חזרה ----------
if st.button("⬅️ חזרה למסך הראשי"):
    go("home")


# ---------- העלאת קובץ ----------
if st.session_state.page == "upload":
    st.header("📤 העלאת קובץ")

    uploaded_file = st.file_uploader("העלה קובץ Excel או CSV", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("תצוגה מקדימה")
        st.dataframe(df.head(30), use_container_width=True)

        st.info("המערכת מחפשת עמודות: תז, שם פרטי, שם משפחה, תאריך לידה, מס טלפון, תאריך הנפקת תז")

        if st.button("🧹 נקה ושמור למאגר"):
            saved = 0

            df = df.rename(columns={
                'ת"ז': "תז",
                'תעודת זהות': "תז",
                'תאריך הנפקת ת"ז': "תאריך הנפקת תז",
                'טלפון': "מס טלפון",
                'מספר טלפון': "מס טלפון",
            })

            for _, row in df.iterrows():
                data = {
                    "תז": row.get("תז", ""),
                    "שם פרטי": row.get("שם פרטי", ""),
                    "שם משפחה": row.get("שם משפחה", ""),
                    "תאריך לידה": row.get("תאריך לידה", ""),
                    "מס טלפון": row.get("מס טלפון", ""),
                    "תאריך הנפקת תז": row.get("תאריך הנפקת תז", ""),
                }

                if save_lead(data, uploaded_file.name):
                    saved += 1

            st.success(f"נשמרו / עודכנו {saved} רשומות במאגר")


# ---------- רשומה ידנית ----------
elif st.session_state.page == "manual":
    st.header("✍️ העלאת רשומה ידנית")

    with st.form("manual_form"):
        tz = st.text_input("תז")
        first_name = st.text_input("שם פרטי")
        last_name = st.text_input("שם משפחה")
        birth_date = st.text_input("תאריך לידה")
        phone = st.text_input("מס טלפון")
        id_issue_date = st.text_input("תאריך הנפקת תז")

        submitted = st.form_submit_button("✅ צור / עדכן רשומה")

        if submitted:
            row = {
                "תז": tz,
                "שם פרטי": first_name,
                "שם משפחה": last_name,
                "תאריך לידה": birth_date,
                "מס טלפון": phone,
                "תאריך הנפקת תז": id_issue_date,
            }

            save_lead(row, "ידני")
            st.success("הרשומה נשמרה עם תאריך יצירה / עדכון אוטומטי")


# ---------- ייצוא ללקוח ----------
elif st.session_state.page == "export":
    st.header("📦 משיכת רשומות לפי לקוח")

    client_name = st.text_input("שם לקוח חדש")

    if st.button("➕ צור לקוח"):
        if client_name.strip():
            add_client(client_name.strip())
            st.success("לקוח נוצר / כבר קיים")

    clients_df = get_clients()

    if not clients_df.empty:
        selected_client = st.selectbox("בחר לקוח", clients_df["name"].tolist())
        amount = st.number_input("כמה רשומות למשוך?", min_value=1, max_value=10000, value=10)

        if st.button("📥 משוך רשומות וייצא Excel"):
            export_df = export_for_client(selected_client, int(amount))

            if export_df.empty:
                st.warning("אין רשומות חדשות זמינות ללקוח הזה")
            else:
                st.success(f"נמשכו {len(export_df)} רשומות ללקוח {selected_client}")
                st.dataframe(export_df, use_container_width=True)

                excel_file = to_excel(export_df)

                st.download_button(
                    "⬇️ הורד Excel",
                    data=excel_file,
                    file_name=f"leads_{selected_client}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("עדיין אין לקוחות. צור לקוח ראשון למעלה.")


# ---------- דוחות ----------
elif st.session_state.page == "reports":
    st.header("📊 כמה רשומות קיימות")

    leads_df = get_leads()

    total = len(leads_df)
    valid_phone = len(leads_df[leads_df["phone_clean"] != ""]) if not leads_df.empty else 0
    invalid_phone = total - valid_phone

    col1, col2, col3 = st.columns(3)
    col1.metric("סה״כ רשומות", total)
    col2.metric("טלפונים תקינים", valid_phone)
    col3.metric("טלפונים לא תקינים / חסרים", invalid_phone)

    st.subheader("מאגר רשומות")
    st.dataframe(leads_df, use_container_width=True)


# ---------- חיפוש לפי תז ----------
elif st.session_state.page == "search":
    st.header("🔎 חיפוש לפי תז")

    search_tz = st.text_input("הכנס תז לחיפוש")

    if st.button("🔍 חפש"):
        search_tz = clean_tz(search_tz)

        conn = sqlite3.connect(DB_NAME)

        lead_df = pd.read_sql_query(
            "SELECT * FROM leads WHERE tz = ?",
            conn,
            params=(search_tz,)
        )

        history_df = pd.read_sql_query(
            "SELECT * FROM export_history WHERE tz = ?",
            conn,
            params=(search_tz,)
        )

        conn.close()

        if lead_df.empty:
            st.warning("לא נמצאה רשומה")
        else:
            st.subheader("פרטי רשומה")
            st.dataframe(lead_df, use_container_width=True)

            st.subheader("היסטוריית ייצוא")
            if history_df.empty:
                st.info("הרשומה עדיין לא נשלחה לאף לקוח")
            else:
                st.dataframe(history_df, use_container_width=True)

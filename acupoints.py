import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import pytz

st.set_page_config(page_title="Pain Consult Log", page_icon="🩺", layout="centered")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
CSV_PATH = st.secrets.get("CSV_PATH", "pain_consult_log.csv")

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CSV_PATH}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

COLUMNS = [
    "timestamp_bkk",
    "id",
    "gender",
    "age",
    "chief_complaint",
    "chronicity_months",
    "visit_number",
    "expectations",
    "locations",
    "ashi_points",
    "acupoints",
    "peg_before",
    "peg_after",
    "other_rx",
    "follow_up",
    "satisfaction_score"
]


def bkk_timestamp():
    tz = pytz.timezone("Asia/Bangkok")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")


def get_csv_from_github():
    r = requests.get(API_URL, headers=HEADERS, params={"ref": GITHUB_BRANCH})

    if r.status_code == 404:
        return pd.DataFrame(columns=COLUMNS), None

    r.raise_for_status()
    data = r.json()
    sha = data["sha"]
    content = base64.b64decode(data["content"]).decode("utf-8")

    if content.strip() == "":
        return pd.DataFrame(columns=COLUMNS), sha

    df = pd.read_csv(StringIO(content))
    return df, sha


def save_csv_to_github(df, sha=None):
    csv_text = df.to_csv(index=False)
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"Update pain consult log {bkk_timestamp()}",
        "content": encoded,
        "branch": GITHUB_BRANCH
    }

    if sha:
        payload["sha"] = sha

    r = requests.put(API_URL, headers=HEADERS, json=payload)
    r.raise_for_status()


st.title("🩺 Pain Consult Log")
st.caption("English data entry form with automatic Bangkok timestamp and GitHub CSV storage")

with st.form("pain_form", clear_on_submit=True):
    patient_id = st.text_input("ID")

    gender = st.selectbox(
        "Gender",
        ["", "Male", "Female", "Other", "Prefer not to say"]
    )

    age = st.number_input("Age", min_value=0, max_value=120, step=1)

    chief_complaint = st.text_area("Chief complaint")

    chronicity_months = st.number_input(
        "Chronicity (months)",
        min_value=0.0,
        step=0.5,
        format="%.1f"
    )

    visit_number = st.number_input(
        "Visit #",
        min_value=1,
        step=1
    )

    expectations = st.text_area(
        "Expectations",
        placeholder="e.g. full recovery, pain reduction, better sleep, return to exercise"
    )

    locations = st.text_area(
        "Locations",
        placeholder="e.g. mid trapezius rt., mid scapula lt., low back, knee rt."
    )

    col1, col2 = st.columns(2)

    with col1:
        ashi_points = st.radio("Ashi points", ["No", "Yes"], horizontal=True)

    with col2:
        acupoints = st.radio("Acupoints", ["No", "Yes"], horizontal=True)

    st.subheader("PEG score")

    peg_before = st.slider("PEG score before", 0.0, 10.0, 0.0, 0.5)
    peg_after = st.slider("PEG score after", 0.0, 10.0, 0.0, 0.5)

    other_rx = st.text_area(
        "Other Rx",
        placeholder="e.g. education, stretching, NSAIDs, muscle relaxant, heat, breathing exercise"
    )

    follow_up = st.selectbox(
        "Follow up",
        ["", "Next week", "Next month", "PRN", "No follow-up", "Other"]
    )

    satisfaction_score = st.slider("Satisfaction score", 0, 10, 5)

    submitted = st.form_submit_button("Save to GitHub CSV")

if submitted:
    if not patient_id.strip():
        st.error("Please enter ID.")
    else:
        new_row = {
            "timestamp_bkk": bkk_timestamp(),
            "id": patient_id.strip(),
            "gender": gender,
            "age": age,
            "chief_complaint": chief_complaint.strip(),
            "chronicity_months": chronicity_months,
            "visit_number": visit_number,
            "expectations": expectations.strip(),
            "locations": locations.strip(),
            "ashi_points": ashi_points,
            "acupoints": acupoints,
            "peg_before": peg_before,
            "peg_after": peg_after,
            "other_rx": other_rx.strip(),
            "follow_up": follow_up,
            "satisfaction_score": satisfaction_score
        }

        try:
            df, sha = get_csv_from_github()

            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df = df[COLUMNS]

            save_csv_to_github(df, sha)

            st.success("Saved successfully to GitHub CSV.")
            st.dataframe(pd.DataFrame([new_row]), use_container_width=True)

        except Exception as e:
            st.error("Save failed.")
            st.exception(e)

st.divider()

with st.expander("View recent records"):
    try:
        df, _ = get_csv_from_github()
        if df.empty:
            st.info("No records yet.")
        else:
            st.dataframe(df.tail(20).sort_index(ascending=False), use_container_width=True)
    except Exception as e:
        st.warning("Cannot load CSV.")
        st.exception(e)

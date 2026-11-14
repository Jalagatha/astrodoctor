"""Streamlit dashboard backed by the shared Django/PostgreSQL data store."""
import os
import uuid
from zipfile import BadZipFile

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import authenticate
from django.db import close_old_connections
from openpyxl.utils.exceptions import InvalidFileException

from engine import INDICATORS, LEVELS
from health.models import DailyRecord, DatasetCalibration
from health.services import analyse_dataset, import_dataset, load_demo_dataset, parse_dataset, records_frame, save_checkin

st.set_page_config(page_title="Astro-Doctor", page_icon="🧑‍🚀", layout="wide")
COLORS = {"Green": "#23845c", "Yellow": "#b98514", "Orange": "#c66b24", "Red": "#c34747"}

st.markdown(
    """
    <style>
      .block-container {max-width: 1320px; padding-top: 1.8rem; padding-bottom: 3rem}
      [data-testid="stMetric"] {background: white; border: 1px solid #e4ebed; padding: 1rem; border-radius: 12px}
      [data-testid="stSidebar"] {background: #f3f7f7}
      div[data-testid="stProgressBar"] > div {background-color: #167968}
      .stAlert {border-radius: 10px}
    </style>
    """,
    unsafe_allow_html=True,
)


def operator_login():
    st.title("Astro-Doctor")
    st.subheader("Operator sign in")
    st.caption("Use your Django staff account. The same account works in the PWA.")
    with st.form("operator_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted:
        user = authenticate(username=username, password=password)
        if user is not None and user.is_active and user.is_staff:
            st.session_state.operator = user.get_username()
            st.rerun()
        st.error("Sign-in failed. Check your username and password.")


def import_panel():
    with st.sidebar:
        st.header("Mission control")
        upload = st.file_uploader("Import dataset", type=["csv", "xlsx"], help="CSV or Excel (.xlsx), at least 21 rows.")
        mode = st.selectbox("Import behavior", ["Replace dataset", "Append rows"])
        if st.button("Import file", disabled=upload is None, use_container_width=True):
            try:
                frame = parse_dataset(upload)
                import_dataset(frame, "replace" if mode == "Replace dataset" else "append")
            except (
                ValueError,
                pd.errors.ParserError,
                pd.errors.EmptyDataError,
                UnicodeDecodeError,
                OSError,
                BadZipFile,
                InvalidFileException,
            ) as exc:
                st.error(str(exc))
            else:
                st.success(f"Imported {len(frame)} daily rows.")
                st.rerun()

        st.divider()
        if st.button("Load demo dataset", use_container_width=True):
            if load_demo_dataset():
                st.success("Loaded synthetic 180-day demo data.")
                st.rerun()
            st.error("The database already contains data. Use Replace dataset to start over.")
        st.caption("The demo dataset is synthetic and for exploration only.")
        st.divider()
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("operator", None)
            st.rerun()


def main():
    close_old_connections()
    if "operator" not in st.session_state:
        operator_login()
        return

    import_panel()
    df = records_frame()
    st.title("🧑‍🚀 Astro-Doctor")
    st.caption("Crew health self-monitoring · Shared PostgreSQL database · PWA at your configured domain")

    if df.empty:
        st.info("No mission records yet. Import a CSV/XLSX file or load the clearly labeled demo dataset from Mission control.")
        st.caption("Decision support only. Not a substitute for the Crew Medical Officer or flight surgeon.")
        return

    day = st.slider("Mission day", int(df.day.min()), int(df.day.max()), int(df.day.max()))
    result = analyse_dataset(df, day)
    trained = DatasetCalibration.objects.filter(pk=1).first()
    if trained:
        st.caption(f"Saved baseline: {trained.baseline_rows} rows through mission day {trained.report['baseline_end_day']}.")
        if day < trained.report["baseline_end_day"]:
            st.info("This retrospective view uses a baseline that includes measurements after the selected mission day.")
    top_level = max(result["levels"].values(), key=LEVELS.index)

    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("Health readiness", f"{result['readiness']:.0f} / 100")
    c2.metric("Overall status", top_level)
    if result["radiation_pct"] is None:
        c3.caption("Radiation dose is unavailable in this dataset.")
    else:
        c3.progress(
            min(result["radiation_pct"] / 100, 1.0),
            text=f"Radiation dose budget: {result['radiation_pct']:.0f}% used "
            f"(projected 180-day dose: {result['radiation_projected']:.0f} mSv)",
        )

    st.subheader("Status by domain")
    domain_columns = st.columns(len(result["levels"]))
    for column, (domain, level) in zip(domain_columns, result["levels"].items()):
        column.markdown(
            f'<div style="border-left:5px solid {COLORS[level]};padding:8px 11px;background:white;border-radius:4px">'
            f"<strong>{domain}</strong><br><span style='color:{COLORS[level]}'>{level}</span></div>",
            unsafe_allow_html=True,
        )

    st.subheader("Alerts and recommended actions")
    if not result["alerts"]:
        st.success("All indicators are within the current personal baseline.")
    for alert in result["alerts"]:
        with st.expander(
            f"{alert['level']} · {alert['domain']} · {alert['why'].split(':')[0]}",
            expanded=alert["level"] in ("Orange", "Red"),
        ):
            st.write(alert["why"])
            for action in alert["actions"]:
                st.write(f"- {action}")
            if alert["level"] in ("Orange", "Red"):
                st.warning("Follow established medical protocols and contact the Crew Medical Officer.")

    st.subheader("Trends vs personal baseline")
    indicator = st.selectbox(
        "Indicator",
        list(INDICATORS),
        format_func=lambda key: f"{INDICATORS[key][2]} ({INDICATORS[key][3]})",
    )
    trend = df[df.day <= day].set_index("day")[[indicator]].copy()
    trend["Personal baseline"] = result["baseline"][indicator]
    st.line_chart(trend)
    st.caption("Drift score (higher means moving the wrong way; 3 = Yellow, 6 = Orange, 12 = Red)")
    st.line_chart(result["z"].set_index("day")[[indicator]])

    st.subheader("Daily check-in")
    with st.form("checkin"):
        first, second, third = st.columns(3)
        mood = first.slider("Mood", 1, 10, 7)
        stress = second.slider("Stress", 1, 10, 4)
        sleep = third.slider("Sleep (hours)", 0.0, 10.0, 7.0, 0.5)
        symptoms = st.multiselect(
            "Symptoms",
            ["Headache", "Cough", "Rash", "Back pain", "Blurred vision", "Dizziness on standing", "Palpitations"],
        )
        submitted = st.form_submit_button("Save check-in")
    if submitted:
        try:
            checkin, created = save_checkin(uuid.uuid4(), mood, stress, sleep, symptoms)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success(f"Saved check-in for mission day {checkin.day}." if created else "Check-in already saved.")
            if {"Palpitations", "Dizziness on standing"} & set(symptoms):
                st.error("Symptoms reported. Sit down and contact the Crew Medical Officer.")
            st.rerun()

    st.caption("Decision support only. It does not replace the Crew Medical Officer or ground flight surgeon.")


main()

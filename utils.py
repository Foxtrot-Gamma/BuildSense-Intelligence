
import pandas as pd
import streamlit as st


def format_date(value):

    if value is None or pd.isna(value):
        return "-"

    if isinstance(value, pd.Timestamp):
        value = value.date()

    return value.strftime("%d %b %Y")


def save_project():

    st.session_state.project = {
        "name": st.session_state.project_name.strip(),
        "location": st.session_state.project_location.strip(),
        "start_date": st.session_state.project_start_date,
        "description": st.session_state.project_description.strip()
    }


def create_activity_id():

    activities = st.session_state.activities

    if activities.empty:
        return "A001"

    return f"A{len(activities) + 1:03d}"


def add_activity(activity_data):

    new_row = pd.DataFrame([activity_data])

    st.session_state.activities = pd.concat(
        [st.session_state.activities, new_row],
        ignore_index=True
    )


def delete_activity(index):

    st.session_state.activities = (
        st.session_state.activities
        .drop(index)
        .reset_index(drop=True)
    )


def normalize_columns(df):

    df = df.copy()

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


def guess_column(columns, keywords):

    for column in columns:

        column_lower = str(column).lower().strip()

        for keyword in keywords:

            if keyword.lower() in column_lower:
                return column

    return None


def parse_number(value):

    """
    Converts common BOQ numeric formats such as:

    12,000
    "12,000"
    4.2
    1,300 kg

    into numbers where possible.
    """

    if value is None:
        return None

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()

    if not text:
        return None

    text = (
        text
        .replace(",", "")
        .replace('"', "")
        .replace("'", "")
    )

    try:
        return float(text)
    except Exception:
        return None


def parse_duration(value):

    """
    Attempts to convert common duration entries into days.

    Examples:
    10       -> 10
    "10"     -> 10
    "10 days" -> 10
    "2 weeks" -> 14
    "3 months" -> 90

    Returns None if no usable duration is found.
    """

    if value is None or pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None

    text = str(value).strip().lower()

    if not text:
        return None

    import re

    match = re.search(r"(\d+(?:\.\d+)?)", text)

    if not match:
        return None

    number = float(match.group(1))

    if "week" in text:
        number *= 7

    elif "month" in text:
        number *= 30

    return int(round(number)) if number > 0 else None

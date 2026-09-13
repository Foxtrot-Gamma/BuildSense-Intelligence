
import streamlit as st
import pandas as pd


ACTIVITY_COLUMNS = [
    "ID",
    "WBS",
    "Activity",
    "Description",
    "Duration",
    "Duration Source",
    "Relationship",
    "Predecessor",
    "BOQ Qty",
    "Unit",
    "Rate",
    "Amount"
]


def initialize_state():

    if "project" not in st.session_state:
        st.session_state.project = {
            "name": "",
            "location": "",
            "start_date": None,
            "description": ""
        }

    if "current_step" not in st.session_state:
        st.session_state.current_step = 0

    if "activities" not in st.session_state:
        st.session_state.activities = pd.DataFrame(
            columns=ACTIVITY_COLUMNS
        )

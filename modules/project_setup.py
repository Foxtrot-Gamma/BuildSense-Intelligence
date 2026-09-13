
import streamlit as st
from datetime import date
from utils import save_project


def render_project_setup():

    st.header("Step 1 — Project Setup")

    st.write(
        "Enter the basic project information to begin the planning process."
    )

    st.divider()

    st.subheader("Project Information")

    project_name = st.text_input(
        "Project Name *",
        value=st.session_state.project.get("name", ""),
        placeholder="Enter project name",
        key="project_name"
    )

    project_location = st.text_input(
        "Location",
        value=st.session_state.project.get("location", ""),
        placeholder="Enter project location (optional)",
        key="project_location"
    )

    default_start_date = (
        st.session_state.project.get("start_date")
    )

    if default_start_date is None:
        default_start_date = date.today()

    project_start_date = st.date_input(
        "Planned Project Start Date *",
        value=default_start_date,
        format="DD/MM/YYYY",
        key="project_start_date"
    )

    project_description = st.text_area(
        "Project Description",
        value=st.session_state.project.get("description", ""),
        placeholder="Enter a brief project description (optional)",
        height=120,
        key="project_description"
    )

    st.divider()

    if st.button(
        "Save Project & Continue →",
        type="primary",
        use_container_width=True
    ):

        if not project_name.strip():

            st.error("Project Name is required.")

        elif project_start_date is None:

            st.error("Planned Project Start Date is required.")

        else:

            save_project()

            st.session_state.current_step = 2

            st.success(
                "Project Setup saved successfully."
            )

            st.rerun()


import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules.html_export import generate_baseline_html
from modules.excel_export import generate_baseline_excel
from modules.progress_control import (
    initialize_progress_data,
    _calculate_status,
    _calculate_schedule_variance,
    _calculate_progress_status,
    _update_progress_data,
    render_progress_gantt,
)
from modules.dashboard import (
    render_dashboard,
    render_lookahead_plan,
)

from state import initialize_state
from modules.project_setup import render_project_setup
from modules.activity_data import render_activity_data
from modules.scheduling import render_scheduling


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Construction Planning & Control",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# GLOBAL APPLICATION FONT
# ============================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
    );

    /* Main application font */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Text and headings */
    .stApp p,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6,
    .stApp label {
        font-family: 'Inter', sans-serif;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# INITIALIZE APPLICATION STATE
# ============================================================

initialize_state()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # --------------------------------------------------------
    # BSI BRAND
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 5px;
            line-height: 1;
            margin-bottom: 28px;
        ">
            BSI
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # CLICKABLE WORKFLOW STEPS
    # --------------------------------------------------------

    steps = [
        "Project Setup",
        "BOQ/WBS & Activity Data",
        "Planning & Scheduling",
        "Review & Baseline",
        "Update Project Progress",
        "Project Dashboard"
    ]

    for i, step in enumerate(steps, start=1):

        if i == st.session_state.current_step:

            st.markdown(
                f"""
                <div style="
                    font-weight: 700;
                    padding: 8px 10px;
                    margin: 3px 0;
                    border-radius: 6px;
                ">
                    ▶ {i}. {step}
                </div>
                """,
                unsafe_allow_html=True
            )

        else:

            if st.button(
                f"{i}. {step}",
                key=f"sidebar_step_{i}",
                use_container_width=True
            ):

                st.session_state.current_step = i
                st.rerun()

    # --------------------------------------------------------
    # VERSION
    # --------------------------------------------------------

    st.markdown(
        "<div style='margin-top: 35px;'></div>",
        unsafe_allow_html=True
    )

    st.caption("Version 1.1")


# ==========================================================
# START PAGE
# ==========================================================

if st.session_state.current_step == 0:

    # ------------------------------------------------------
    # START PAGE ANIMATION / STYLING
    # ------------------------------------------------------

    st.markdown(
        """
        <style>
        
        .bsi-logo {
            text-align: center;
            font-size: 80px;
            font-weight: 900;
            letter-spacing: 12px;
            margin-top: 100px;
            animation: fadeIn 1.2s ease-in-out;
        }

        .bsi-title {
            text-align: center;
            font-size: 42px;
            font-weight: 700;
            margin-top: 15px;
            animation: slideUp 1.2s ease-in-out;
        }

        .bsi-tagline {
            text-align: center;
            font-size: 19px;
            opacity: 0.7;
            margin-top: 12px;
            margin-bottom: 45px;
            animation: slideUp 1.6s ease-in-out;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: scale(0.8);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(25px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # BRANDING
    # ------------------------------------------------------

    st.markdown(
        '<div class="bsi-logo">BSI</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="bsi-title">BuildSense Intelligence</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="bsi-tagline">'
        'AI-Powered BOQ-to-Schedule Automation'
        '</div>',
        unsafe_allow_html=True
    )

    # ------------------------------------------------------
    # GET STARTED BUTTON
    # ------------------------------------------------------

    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:

        if st.button(
            "Let's Get Started",
            type="primary",
            use_container_width=True
        ):

            st.session_state.current_step = 1
            st.rerun()


# ==========================================================
# STEP 1 — PROJECT SETUP
# ==========================================================

elif st.session_state.current_step == 1:

    render_project_setup()


# ==========================================================
# STEP 2 — BOQ / WBS & ACTIVITY DATA
# ==========================================================

elif st.session_state.current_step == 2:

    render_activity_data()


# ==========================================================
# STEP 3 — PLANNING & SCHEDULING
# ==========================================================

elif st.session_state.current_step == 3:

    render_scheduling()

# ==========================================================
# STEP 4 — BASELINE REVIEW & APPROVAL
# ==========================================================

elif st.session_state.current_step == 4:

    st.header("Step 4 — Baseline Review & Approval")

    st.write(
        "Review the finalized project schedule, critical path "
        "and activity float before approving the official "
        "project baseline."
    )

    st.divider()

    finalized = st.session_state.get(
        "finalized_schedule"
    )

    # ======================================================
    # CHECK FINALIZED SCHEDULE
    # ======================================================

    if finalized is None or finalized.empty:

        st.warning(
            "No finalized schedule is available. "
            "Please complete Step 3 first."
        )

        if st.button(
            "← Back to Planning & Scheduling",
            use_container_width=True
        ):

            st.session_state.current_step = 3
            st.rerun()

    else:

        # ==================================================
        # CHECK CPM DATA
        # ==================================================

        required_cpm_columns = [
            "Total Float",
            "Critical"
        ]

        missing_cpm_columns = [
            column
            for column in required_cpm_columns
            if column not in finalized.columns
        ]

        if missing_cpm_columns:

            st.error(
                "CPM data is missing from the finalized schedule. "
                "Please return to Step 3 and recalculate the "
                "proposed schedule."
            )

            if st.button(
                "← Back to Planning & Scheduling",
                use_container_width=True
            ):

                st.session_state.current_step = 3
                st.rerun()

        else:

            # ==================================================
            # 1. BASELINE SUMMARY
            # ==================================================

            st.subheader("1. Baseline Summary")

            baseline_start = pd.to_datetime(
                finalized["Planned Start"],
                errors="coerce"
            ).min()

            baseline_finish = pd.to_datetime(
                finalized["Planned Finish"],
                errors="coerce"
            ).max()

            if (
                pd.notna(baseline_start)
                and pd.notna(baseline_finish)
            ):

                baseline_duration = (
                    baseline_finish
                    - baseline_start
                ).days + 1

            else:

                baseline_duration = 0

            # --------------------------------------------------
            # CPM SUMMARY
            # --------------------------------------------------

            float_values = pd.to_numeric(
                finalized["Total Float"],
                errors="coerce"
            )

            valid_float_values = float_values.dropna()

            if not valid_float_values.empty:

                maximum_float = int(
                    valid_float_values.max()
                )

            else:

                maximum_float = 0

            critical_count = int(
                finalized["Critical"]
                .fillna(False)
                .astype(bool)
                .sum()
            )

            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.metric(
                    "Project Start",
                    baseline_start.strftime("%d %b %Y")
                    if pd.notna(baseline_start)
                    else "-"
                )

            with col2:

                st.metric(
                    "Project Finish",
                    baseline_finish.strftime("%d %b %Y")
                    if pd.notna(baseline_finish)
                    else "-"
                )

            with col3:

                st.metric(
                    "Project Duration",
                    f"{baseline_duration} days"
                )

            with col4:

                st.metric(
                    "Activities",
                    len(finalized)
                )

            col5, col6 = st.columns(2)

            with col5:

                st.metric(
                    "Maximum Activity Float",
                    f"{maximum_float} days"
                )

            with col6:

                st.metric(
                    "Critical Activities",
                    critical_count
                )

            st.divider()

            # ==================================================
            # 2. BASELINE SCHEDULE
            # ==================================================

            st.subheader("2. Baseline Schedule")

            st.write(
                "Review the planned dates, activity float and "
                "critical status before approving the baseline."
            )

            # --------------------------------------------------
            # CRITICAL HIGHLIGHT CONTROL
            # --------------------------------------------------

            highlight_critical = st.checkbox(
                "🔴 Highlight Critical Activities",
                key="highlight_critical_activities"
            )

            # --------------------------------------------------
            # PREPARE DISPLAY DATA
            # --------------------------------------------------

            baseline_columns = [
                "ID",
                "WBS",
                "Activity",
                "Duration",
                "Duration Source",
                "Relationship",
                "Predecessor",
                "Planned Start",
                "Planned Finish",
                "Total Float",
                "Critical"
            ]

            available_columns = [
                column
                for column in baseline_columns
                if column in finalized.columns
            ]

            baseline_display = finalized[
                available_columns
            ].copy()

            # --------------------------------------------------
            # FORMAT DATES
            # --------------------------------------------------

            if "Planned Start" in baseline_display.columns:

                baseline_display["Planned Start"] = (
                    pd.to_datetime(
                        baseline_display["Planned Start"],
                        errors="coerce"
                    ).dt.strftime("%d %b %Y")
                )

            if "Planned Finish" in baseline_display.columns:

                baseline_display["Planned Finish"] = (
                    pd.to_datetime(
                        baseline_display["Planned Finish"],
                        errors="coerce"
                    ).dt.strftime("%d %b %Y")
                )

            # --------------------------------------------------
            # FORMAT FLOAT
            # --------------------------------------------------

            if "Total Float" in baseline_display.columns:

                baseline_display["Total Float"] = (
                    pd.to_numeric(
                        baseline_display["Total Float"],
                        errors="coerce"
                    )
                    .fillna(0)
                    .astype(int)
                )

            # --------------------------------------------------
            # FORMAT CRITICAL STATUS
            # --------------------------------------------------

            if "Critical" in baseline_display.columns:

                baseline_display["Critical"] = (
                    baseline_display["Critical"]
                    .fillna(False)
                    .astype(bool)
                    .map(
                        lambda value:
                        "Yes" if value else "No"
                    )
                )

            # --------------------------------------------------
            # HIGHLIGHT CRITICAL ACTIVITIES
            # --------------------------------------------------

            if highlight_critical:

                def highlight_critical_row(row):

                    critical_value = str(
                        row.get(
                            "Critical",
                            ""
                        )
                    ).strip().lower()

                    if critical_value == "yes":

                        return [
                            "color: #c0392b; "
                            "font-weight: 600;"
                        ] * len(row)

                    return [""] * len(row)

                styled_baseline = (
                    baseline_display.style
                    .apply(
                        highlight_critical_row,
                        axis=1
                    )
                )

                st.dataframe(
                    styled_baseline,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Critical activities are highlighted in red. "
                    "This highlighting is for review only and "
                    "does not modify the baseline data."
                )

            else:

                st.dataframe(
                    baseline_display,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Click 'Highlight Critical Activities' to "
                    "visually identify the critical activities."
                )

            st.divider()

            # ==================================================
            # 3. BASELINE GANTT CHART
            # ==================================================

            st.subheader("3. Baseline Gantt Chart")

            st.write(
                "Visualize the baseline schedule timeline "
                "and identify critical activities."
            )

            # --------------------------------------------------
            # GANTT TIME SCALE
            # --------------------------------------------------

            gantt_scale = st.selectbox(
                "Time Scale",
                [
                    "Days",
                    "Weeks",
                    "Months",
                    "Quarters"
                ],
                key="baseline_gantt_scale"
            )

            # --------------------------------------------------
            # PREPARE GANTT DATA
            # --------------------------------------------------

            gantt_data = finalized.copy()

            gantt_data["Planned Start"] = pd.to_datetime(
                gantt_data["Planned Start"],
                errors="coerce"
            )

            gantt_data["Planned Finish"] = pd.to_datetime(
                gantt_data["Planned Finish"],
                errors="coerce"
            )

            gantt_data["Critical"] = (
                gantt_data["Critical"]
                .fillna(False)
                .astype(bool)
            )

            gantt_data = gantt_data[
                gantt_data["Planned Start"].notna()
                & gantt_data["Planned Finish"].notna()
            ].copy()

            if gantt_data.empty:

                st.warning(
                    "No calculated schedule dates are available "
                    "for the Gantt chart."
                )

            else:

                gantt_data = gantt_data.reset_index(
                    drop=True
                )

                # --------------------------------------------------
                # TIMELINE SCALE
                # --------------------------------------------------

                if gantt_scale == "Days":

                    dtick = (
                        24
                        * 60
                        * 60
                        * 1000
                    )

                    tickformat = "%d %b"

                elif gantt_scale == "Weeks":

                    dtick = (
                        7
                        * 24
                        * 60
                        * 60
                        * 1000
                    )

                    tickformat = "%d %b"

                elif gantt_scale == "Months":

                    dtick = "M1"

                    tickformat = "%b %Y"

                else:

                    dtick = "M3"

                    tickformat = "%b %Y"

                # --------------------------------------------------
                # CREATE GANTT TIMELINE
                # --------------------------------------------------

                fig = go.Figure()

                for position, activity in gantt_data.iterrows():

                    start = activity["Planned Start"]

                    finish = activity["Planned Finish"]

                    # --------------------------------------------------
                    # INCLUSIVE DATE LOGIC
                    # --------------------------------------------------

                    duration_days = (
                        finish - start
                    ).days + 1

                    duration_ms = (
                        duration_days
                        * 24
                        * 60
                        * 60
                        * 1000
                    )

                    # --------------------------------------------------
                    # CRITICAL ACTIVITY COLOUR
                    # --------------------------------------------------

                    is_critical = bool(
                        activity["Critical"]
                    )

                    if (
                        highlight_critical
                        and is_critical
                    ):

                        bar_color = "#c0392b"

                    else:

                        bar_color = "#9aa0a6"

                    # --------------------------------------------------
                    # ACTIVITY INFORMATION
                    # --------------------------------------------------

                    activity_name = str(
                        activity.get(
                            "Activity",
                            activity.get(
                                "ID",
                                ""
                            )
                        )
                    )

                    activity_id = str(
                        activity.get(
                            "ID",
                            ""
                        )
                    )

                    # --------------------------------------------------
                    # GANTT BAR
                    # --------------------------------------------------

                    fig.add_trace(
                        go.Bar(
                            x=[duration_ms],
                            y=[position],
                            base=[start],
                            orientation="h",

                            marker=dict(
                                color=bar_color
                            ),

                            hovertemplate=(
                                "<b>"
                                + activity_name
                                + "</b><br>"
                                "ID: "
                                + activity_id
                                + "<br>"
                                "Start: "
                                + start.strftime(
                                    "%d %b %Y"
                                )
                                + "<br>"
                                "Finish: "
                                + finish.strftime(
                                    "%d %b %Y"
                                )
                                + "<br>"
                                "Duration: "
                                + str(duration_days)
                                + " days"
                                + "<br>"
                                "Critical: "
                                + (
                                    "Yes"
                                    if is_critical
                                    else "No"
                                )
                                + "<extra></extra>"
                            ),

                            showlegend=False
                        )
                    )

                # --------------------------------------------------
                # TIMELINE LAYOUT
                # --------------------------------------------------

                fig.update_layout(

                    height=max(
                        450,
                        len(gantt_data) * 38
                    ),

                    barmode="overlay",

                    margin=dict(
                        l=220,
                        r=40,
                        t=30,
                        b=70
                    ),

                    plot_bgcolor="rgba(0,0,0,0)",

                    paper_bgcolor="rgba(0,0,0,0)",

                    showlegend=False,

                    xaxis=dict(
                        title="Project Timeline",
                        type="date",
                        dtick=dtick,
                        tickformat=tickformat,
                        showgrid=True,
                        gridcolor=(
                            "rgba(255,255,255,0.10)"
                        ),
                        zeroline=False,
                        rangeslider=dict(
                            visible=True
                        )
                    ),

                    yaxis=dict(
                        title="",
                        tickmode="array",

                        tickvals=list(
                            range(
                                len(gantt_data)
                            )
                        ),

                        ticktext=[
                            str(activity)
                            for activity in gantt_data[
                                "Activity"
                            ]
                        ],

                        autorange="reversed",

                        showgrid=False,

                        zeroline=False,

                        tickfont=dict(
                            size=12
                        )
                    ),

                    hovermode="closest"
                )

                # --------------------------------------------------
                # DISPLAY GANTT
                # --------------------------------------------------

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "displaylogo": False,
                        "scrollZoom": True,
                        "responsive": True
                    }
                )

                st.caption(
                    "Critical activities are shown in red when "
                    "Highlight Critical Activities is enabled. "
                    "All other activities remain neutral."
                )

            st.divider()

            # ==================================================
            # 4. BASELINE HTML EXPORT
            # ==================================================

            st.subheader("4. Baseline HTML Export")

            st.write(
                "Export the finalized baseline as a standalone "
                "HTML network and schedule report."
            )

            if st.button(
                "🌐 Export Baseline HTML",
                key="export_baseline_html"
            ):

                html_content = generate_baseline_html(
                    finalized
                )

                if html_content is None:

                    st.error(
                        "Unable to generate the baseline HTML report."
                    )

                else:

                    st.download_button(
                        label="⬇️ Download Baseline HTML",
                        data=html_content,
                        file_name="baseline_network_report.html",
                        mime="text/html",
                        key="download_baseline_html"
                    )

            st.divider()

            # ==================================================
            # 5. BASELINE EXCEL EXPORT
            # ==================================================

            st.subheader("5. Baseline Excel Export")

            st.write(
                "Export the finalized baseline schedule as a "
                "professionally formatted Excel workbook."
            )

            if st.button(
                "📊 Export Baseline Excel",
                key="export_baseline_excel"
            ):

                excel_file = generate_baseline_excel(
                    finalized
                )

                if excel_file is None:

                    st.error(
                        "Unable to generate the baseline Excel report."
                    )

                else:

                    st.download_button(
                        label="⬇️ Download Baseline Excel",
                        data=excel_file,
                        file_name="baseline_schedule.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        key="download_baseline_excel"
                    )

            st.divider()

            # ==================================================
            # 5. BASELINE APPROVAL
            # ==================================================

            st.subheader("6. Baseline Approval")

            st.info(
                "This schedule will become the official project "
                "baseline. Future project progress will be "
                "measured against these planned dates."
            )

            # ==================================================
            # BASELINE VALIDATION
            # ==================================================

            validation_errors = []

            required_baseline_columns = [
                "ID",
                "Activity",
                "Duration",
                "Planned Start",
                "Planned Finish",
                "Total Float",
                "Critical",
            ]

            missing_baseline_columns = [
                col
                for col in required_baseline_columns
                if col not in finalized.columns
            ]

            if missing_baseline_columns:

                validation_errors.append(
                    "Missing required baseline information: "
                    + ", ".join(missing_baseline_columns)
                )

            else:

                if finalized["Activity"].isna().any():

                    validation_errors.append(
                        "One or more activities have no activity name."
                    )

                if finalized["Planned Start"].isna().any():

                    validation_errors.append(
                        "One or more activities have no planned start date."
                    )

                if finalized["Planned Finish"].isna().any():

                    validation_errors.append(
                        "One or more activities have no planned finish date."
                    )

                if finalized["Duration"].isna().any():

                    validation_errors.append(
                        "One or more activities have no duration."
                    )

                invalid_dates = (
                    finalized["Planned Finish"]
                    < finalized["Planned Start"]
                )

                if invalid_dates.any():

                    validation_errors.append(
                        "One or more activities have a finish date "
                        "earlier than their start date."
                    )

                invalid_duration = (
                    pd.to_numeric(
                        finalized["Duration"],
                        errors="coerce"
                    ) < 0
                )

                if invalid_duration.any():

                    validation_errors.append(
                        "One or more activities have a negative duration."
                    )

            if validation_errors:

                st.error(
                    "Baseline validation failed. "
                    "Please correct the following before approval:"
                )

                for error in validation_errors:

                    st.write(f"• {error}")

            else:

                st.success(
                    "Baseline validation passed. "
                    "The schedule is ready for approval."
                )

            baseline_confirmation = st.checkbox(
                "I have reviewed the baseline schedule, "
                "critical activities and activity float, "
                "and confirm that it is approved for project control.",
                key="baseline_confirmation"
            )

            if st.button(
                "Approve & Lock Baseline",
                type="primary",
                use_container_width=True
            ):

                if not baseline_confirmation:

                    st.error(
                        "Please confirm that you have reviewed "
                        "the baseline schedule before locking it."
                    )

                else:

                    st.session_state.baseline_schedule = (
                        finalized.copy()
                    )

                    st.session_state.baseline_locked = True

                    st.session_state.current_step = 5

                    st.success(
                        "Project baseline approved and locked."
                    )

                    st.rerun()

            st.divider()

            # ==================================================
            # BACK TO STEP 3
            # ==================================================

            if st.button(
                "← Back to Planning & Scheduling",
                use_container_width=True
            ):

                st.session_state.current_step = 3
                st.rerun()

# ==========================================================
# STEP 5 — UPDATE PROJECT PROGRESS
# ==========================================================

elif st.session_state.current_step == 5:

    st.header("Step 5 — Update Project Progress")

    st.info(
        "Update actual project progress against the approved "
        "baseline. The approved baseline will remain unchanged."
    )

    baseline = st.session_state.get(
        "baseline_schedule"
    )

    if baseline is None or baseline.empty:

        st.error(
            "No approved baseline is available. "
            "Please return to Step 4 and approve the baseline first."
        )

    else:

        # --------------------------------------------------
        # INITIALIZE PROGRESS DATA
        # --------------------------------------------------

        if (
            "progress_data" not in st.session_state
            or st.session_state.progress_data is None
        ):

            st.session_state.progress_data = (
                initialize_progress_data(
                    baseline
                )
            )

        progress_data = st.session_state.progress_data

        if "Progress Update Date" not in progress_data.columns:
            progress_data["Progress Update Date"] = pd.NaT
            st.session_state.progress_data = progress_data


        # --------------------------------------------------
        # ACTIVITY SEARCH / FILTER
        # --------------------------------------------------

        search_text = st.text_input(
            "🔎 Search activities",
            placeholder=(
                "Search by activity name, ID, WBS, "
                "planned start or planned finish..."
            ),
            key="progress_search"
        )

        display_data = progress_data.copy()

        if search_text.strip():

            search_text = search_text.strip().lower()

            searchable_columns = [
                "ID",
                "WBS",
                "Activity",
                "Planned Start",
                "Planned Finish",
            ]

            search_mask = pd.Series(
                False,
                index=display_data.index
            )

            for column in searchable_columns:

                if column not in display_data.columns:
                    continue

                column_text = (
                    display_data[column]
                    .astype(str)
                    .str.lower()
                )

                search_mask = (
                    search_mask
                    | column_text.str.contains(
                        search_text,
                        na=False,
                        regex=False
                    )
                )

            display_data = display_data.loc[
                search_mask
            ]

        # --------------------------------------------------
        # PROJECT PROGRESS TABLE
        # --------------------------------------------------

        highlight_critical = st.checkbox(
            "🔴 Highlight Critical Activities",
            key="highlight_critical_progress"
        )

        st.subheader("Project Progress")

        st.write(
            "The table below is based on the approved baseline. "
            "Update the editable progress fields as the project progresses."
        )

        display_columns = [
            "ID",
            "WBS",
            "Activity",
            "Planned Start",
            "Actual Start",
            "Lag",
            "Planned Finish",
            "Actual Finish",
            "Planned %",
            "% Complete",
            "Progress Update Date",
            "Status",
            "Schedule Variance",
            "Total Float",
            "Schedule Impact",
            "Progress Status",
        ]

        available_columns = [
            col
            for col in display_columns
            if col in progress_data.columns
        ]

        # --------------------------------------------------
        # CRITICAL ACTIVITY INDICATOR
        # --------------------------------------------------

        table_data = display_data[available_columns].copy()

        if highlight_critical and "Critical" in display_data.columns:

            critical_mask = (
                display_data["Critical"]
                .fillna(False)
                .astype(bool)
            )

            table_data.loc[
                critical_mask,
                "Activity"
            ] = (
                "🔴 "
                + table_data.loc[
                    critical_mask,
                    "Activity"
                ].astype(str)
            )

        edited_progress = st.data_editor(
            table_data,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "ID",
                "WBS",
                "Activity",
                "Planned Start",
                "Lag",
                "Planned Finish",
                "Planned %",
                "Status",
                "Schedule Variance",
                "Total Float",
                "Schedule Impact",
                "Progress Status",
            ],
            column_config={
                "Planned Start": st.column_config.DateColumn(
                    "Planned Start",
                    format="DD MMM YY"
                ),
                "Planned Finish": st.column_config.DateColumn(
                    "Planned Finish",
                    format="DD MMM YY"
                ),
                "Actual Start": st.column_config.DateColumn(
                    "Actual Start",
                    format="DD MMM YY"
                ),
                "Actual Finish": st.column_config.DateColumn(
                    "Actual Finish",
                    format="DD MMM YY"
                ),
                "Progress Update Date": st.column_config.DateColumn(
                    "Progress Update Date",
                    format="DD MMM YY"
                ),
                "Planned %": st.column_config.NumberColumn(
                    "Planned %",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%"
                ),
                "% Complete": st.column_config.NumberColumn(
                    "% Complete",
                    min_value=0,
                    max_value=100,
                    step=1,
                    format="%.0f%%"
                ),
                "Total Float": st.column_config.NumberColumn(
                    "Total Float",
                    format="%.0f days"
                ),
            },
            key=f"progress_editor_{st.session_state.get('progress_editor_version', 0)}",
            on_change=_update_progress_data,
        )


        # Keep the main progress dataset synchronized
        progress_data = st.session_state.progress_data

        # --------------------------------------------------
        # INITIALIZE PROGRESS HISTORY
        # --------------------------------------------------

        if (
            "progress_history" not in st.session_state
            or st.session_state.progress_history is None
        ):
            st.session_state.progress_history = pd.DataFrame(
                columns=[
                    "ID",
                    "WBS",
                    "Activity",
                    "Progress Update Date",
                    "% Complete",
                    "Actual Start",
                    "Actual Finish",
                    "Planned %",
                    "Lag",
                    "Schedule Variance",
                    "Status",
                    "Recorded At",
                ]
            )


        # --------------------------------------------------
        # RECORD PROGRESS DATA ENTRY
        # --------------------------------------------------

        if st.button(
            "📌 Record Data Entry",
            type="primary",
            use_container_width=True
        ):

            today = pd.Timestamp.today().normalize()

            date_values = pd.to_datetime(
                progress_data["Progress Update Date"],
                errors="coerce"
            )

            non_today_dates = (
                date_values.notna()
                & (date_values.dt.normalize() != today)
            )

            if non_today_dates.any():

                st.session_state.confirm_record_progress = True

            else:

                history_snapshot = progress_data.copy()

                history_snapshot["Recorded At"] = (
                    pd.Timestamp.now()
                )

                st.session_state.progress_history = pd.concat(
                    [
                        st.session_state.progress_history,
                        history_snapshot
                    ],
                    ignore_index=True
                )

                st.success(
                    "Progress data entry recorded successfully."
                )


        # --------------------------------------------------
        # CONFIRM RECORDING WITH NON-TODAY DATES
        # --------------------------------------------------

        if st.session_state.get(
            "confirm_record_progress",
            False
        ):

            st.warning(
                "⚠️ Some Progress Update Dates are "
                "different from today. "
                "Do you want to proceed with recording?"
            )

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "Proceed with Recording",
                    type="primary",
                    use_container_width=True
                ):

                    history_snapshot = progress_data.copy()

                    history_snapshot["Recorded At"] = (
                        pd.Timestamp.now()
                    )

                    st.session_state.progress_history = pd.concat(
                        [
                            st.session_state.progress_history,
                            history_snapshot
                        ],
                        ignore_index=True
                    )

                    st.session_state.confirm_record_progress = False

                    st.success(
                        "Progress data entry recorded successfully."
                    )

            with col2:

                if st.button(
                    "Cancel",
                    use_container_width=True
                ):

                    st.session_state.confirm_record_progress = False
                    st.rerun()


        # --------------------------------------------------
        # PROGRESS HISTORY
        # --------------------------------------------------

        if st.button(
            "📊 View Progress History",
            type="primary",
            use_container_width=True
        ):

            @st.dialog(
                "📊 Progress History",
                width="large"
            )
            def show_progress_history():

                history = st.session_state.get(
                    "progress_history"
                )

                if history is None or history.empty:

                    st.info(
                        "No progress history has been recorded yet."
                    )

                    if st.button(
                        "Close",
                        use_container_width=True
                    ):

                        st.session_state[
                            "show_progress_history"
                        ] = False

                        st.rerun()

                    return

                history = history.copy()

                history["Recorded At"] = pd.to_datetime(
                    history["Recorded At"],
                    errors="coerce"
                )

                recorded_entries = (
                    history["Recorded At"]
                    .dropna()
                    .drop_duplicates()
                    .sort_values(
                        ascending=False
                    )
                )

                if recorded_entries.empty:

                    st.info(
                        "No valid progress history entries found."
                    )
                    return

                # --------------------------------------------------
                # SELECT HISTORY ENTRY
                # --------------------------------------------------

                entry_options = {
                    timestamp.strftime(
                        "%d %b %Y — %H:%M:%S"
                    ): timestamp
                    for timestamp in recorded_entries
                }

                entry_labels = list(
                    entry_options.keys()
                )

                current_timestamp = (
                    st.session_state.get(
                        "selected_progress_history_timestamp"
                    )
                )

                current_label = None

                if current_timestamp is not None:

                    current_timestamp = pd.to_datetime(
                        current_timestamp,
                        errors="coerce"
                    )

                    for label, timestamp in entry_options.items():

                        if timestamp == current_timestamp:

                            current_label = label
                            break

                if current_label not in entry_labels:

                    current_label = entry_labels[0]

                selected_label = st.selectbox(
                    "Recorded Entry",
                    entry_labels,
                    index=entry_labels.index(
                        current_label
                    ),
                    key="progress_history_entry_selector"
                )

                selected_timestamp = entry_options[
                    selected_label
                ]

                st.session_state[
                    "selected_progress_history_timestamp"
                ] = selected_timestamp

                # --------------------------------------------------
                # GET SELECTED SNAPSHOT
                # --------------------------------------------------

                snapshot = history.loc[
                    history["Recorded At"]
                    == selected_timestamp
                ].copy()

                st.caption(
                    f"Snapshot recorded at "
                    f"{selected_timestamp.strftime('%d %b %Y, %H:%M:%S')}"
                )

                # --------------------------------------------------
                # FILTERS
                # --------------------------------------------------

                st.subheader("Filter Snapshot")

                filter_col1, filter_col2 = st.columns(2)

                with filter_col1:

                    history_search = st.text_input(
                        "🔎 Search Activity",
                        placeholder=(
                            "Activity, ID or WBS..."
                        ),
                        key="history_activity_search"
                    )

                with filter_col2:

                    status_options = ["All"]

                    if "Status" in snapshot.columns:

                        status_values = (
                            snapshot["Status"]
                            .dropna()
                            .astype(str)
                            .unique()
                            .tolist()
                        )

                        status_options.extend(
                            sorted(status_values)
                        )

                    selected_status = st.selectbox(
                        "Status",
                        status_options,
                        key="history_status_filter"
                    )

                critical_only = st.checkbox(
                    "🔴 Critical Activities Only",
                    key="history_critical_only"
                )

                filtered_snapshot = snapshot.copy()

                # --------------------------------------------------
                # SEARCH FILTER
                # --------------------------------------------------

                if history_search.strip():

                    search_value = (
                        history_search
                        .strip()
                        .lower()
                    )

                    search_columns = [
                        "ID",
                        "WBS",
                        "Activity"
                    ]

                    search_mask = pd.Series(
                        False,
                        index=filtered_snapshot.index
                    )

                    for column in search_columns:

                        if column not in filtered_snapshot.columns:
                            continue

                        search_mask = (
                            search_mask
                            |
                            filtered_snapshot[column]
                            .astype(str)
                            .str.lower()
                            .str.contains(
                                search_value,
                                na=False,
                                regex=False
                            )
                        )

                    filtered_snapshot = (
                        filtered_snapshot.loc[
                            search_mask
                        ]
                    )

                # --------------------------------------------------
                # STATUS FILTER
                # --------------------------------------------------

                if (
                    selected_status != "All"
                    and "Status" in filtered_snapshot.columns
                ):

                    filtered_snapshot = (
                        filtered_snapshot.loc[
                            filtered_snapshot["Status"]
                            .astype(str)
                            == selected_status
                        ]
                    )

                # --------------------------------------------------
                # CRITICAL FILTER
                # --------------------------------------------------

                if (
                    critical_only
                    and "Critical" in filtered_snapshot.columns
                ):

                    critical_mask = (
                        filtered_snapshot["Critical"]
                        .fillna(False)
                        .astype(bool)
                    )

                    filtered_snapshot = (
                        filtered_snapshot.loc[
                            critical_mask
                        ]
                    )

                # --------------------------------------------------
                # DISPLAY SNAPSHOT
                # --------------------------------------------------

                st.subheader("Progress Snapshot")

                history_display_columns = [
                    "ID",
                    "WBS",
                    "Activity",
                    "Progress Update Date",
                    "% Complete",
                    "Actual Start",
                    "Actual Finish",
                    "Planned %",
                    "Lag",
                    "Schedule Variance",
                    "Status",
                    "Schedule Impact",
                    "Progress Status",
                ]

                history_available_columns = [
                    column
                    for column in history_display_columns
                    if column in filtered_snapshot.columns
                ]

                history_table = filtered_snapshot[
                    history_available_columns
                ].copy()

                st.dataframe(
                    history_table,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    f"Showing "
                    f"{len(history_table)} of "
                    f"{len(snapshot)} activities."
                )

                st.divider()

                # --------------------------------------------------
                # DELETE SNAPSHOT
                # --------------------------------------------------

                st.subheader("Delete History Entry")

                st.warning(
                    "Deleting this entry will remove the "
                    "complete project snapshot recorded at "
                    f"{selected_timestamp.strftime('%d %b %Y, %H:%M:%S')}."
                )

                delete_key = (
                    "confirm_delete_progress_history"
                )

                if not st.session_state.get(
                    delete_key,
                    False
                ):

                    if st.button(
                        "🗑️ Delete This Entry",
                        use_container_width=True
                    ):

                        st.session_state[
                            delete_key
                        ] = True

                else:

                    st.error(
                        "Are you sure you want to permanently "
                        "delete this progress history entry?"
                    )

                    delete_col1, delete_col2 = st.columns(2)

                    with delete_col1:

                        if st.button(
                            "Delete Permanently",
                            type="primary",
                            use_container_width=True
                        ):

                            remaining_history = (
                                history.loc[
                                    history["Recorded At"]
                                    != selected_timestamp
                                ].copy()
                            )

                            st.session_state.progress_history = (
                                remaining_history
                            )

                            st.session_state[
                                "confirm_delete_progress_history"
                            ] = False

                            # If the deleted entry was selected,
                            # select the next available entry.
                            remaining_entries = (
                                remaining_history[
                                    "Recorded At"
                                ]
                                .dropna()
                                .drop_duplicates()
                                .sort_values(
                                    ascending=False
                                )
                            )

                            if remaining_entries.empty:

                                st.session_state[
                                    "selected_progress_history_timestamp"
                                ] = None

                            else:

                                st.session_state[
                                    "selected_progress_history_timestamp"
                                ] = remaining_entries.iloc[0]

                    with delete_col2:

                        if st.button(
                            "Cancel",
                            use_container_width=True
                        ):

                            st.session_state[
                                "confirm_delete_progress_history"
                            ] = False

            show_progress_history()


        # --------------------------------------------------
        # PROGRESS GANTT
        # --------------------------------------------------

        if st.button(
            "📊 View Progress Gantt",
            type="primary",
            use_container_width=True
        ):

            @st.dialog(
                "📊 Project Progress Gantt",
                width="large"
            )
            def show_progress_gantt():

                render_progress_gantt(
                    st.session_state.progress_data
                )

            show_progress_gantt()

    # --------------------------------------------------
    # BACK TO STEP 4
    # --------------------------------------------------

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "← Back to Step 4 — Baseline Review",
            use_container_width=True
        ):

            st.session_state.current_step = 4

            st.rerun()

    with col2:

        if st.button(
            "📊 View Dashboard",
            type="primary",
            use_container_width=True
        ):

            st.session_state.current_step = 6

            st.rerun()

# ==========================================================
# STEP 6 — DASHBOARD & LOOKAHEAD PLAN
# ==========================================================

elif st.session_state.current_step == 6:

    render_dashboard(
        st.session_state.get(
            "progress_data"
        )
    )

    st.divider()

    render_lookahead_plan(
        st.session_state.get(
            "progress_data"
        )
    )

    # --------------------------------------------------
    # BACK TO STEP 5
    # --------------------------------------------------

    st.divider()

    if st.button(
        "← Back to Step 5 — Update Project Progress",
        use_container_width=True
    ):

        st.session_state.current_step = 5

        st.rerun()

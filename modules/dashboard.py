from datetime import timedelta

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from modules.progress_control import render_progress_gantt

from openai import OpenAI


# ============================================================
# DASHBOARD KPI CALCULATIONS
# ============================================================

def calculate_dashboard_kpis(progress_data):

    if (
        progress_data is None
        or progress_data.empty
    ):

        return {
            "overall_progress": 0,
            "planned_progress": 0,
            "progress_variance": 0,
            "total_activities": 0,
            "completed": 0,
            "in_progress": 0,
            "not_started": 0,
            "delayed": 0,
            "critical": 0,
        }

    data = progress_data.copy()

    # --------------------------------------------------------
    # Standardize numeric fields
    # --------------------------------------------------------

    data["% Complete"] = pd.to_numeric(
        data.get("% Complete", 0),
        errors="coerce"
    ).fillna(0)

    data["Planned %"] = pd.to_numeric(
        data.get("Planned %", 0),
        errors="coerce"
    ).fillna(0)

    data["Schedule Variance"] = pd.to_numeric(
        data.get("Schedule Variance", 0),
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # Standardize Critical flag
    #
    # IMPORTANT:
    # Do NOT use .astype(bool)
    # because "False" is a non-empty string and therefore
    # becomes True in Python/Pandas.
    # --------------------------------------------------------

    if "Critical" in data.columns:

        data["_Critical"] = (
            data["Critical"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin([
                "true",
                "yes",
                "1",
                "critical"
            ])
        )

    else:

        data["_Critical"] = False

    # --------------------------------------------------------
    # Project progress
    #
    # Keep the existing MVP methodology for now.
    # Weighted progress will be addressed separately after
    # Step 5 progress logic is confirmed.
    # --------------------------------------------------------

    overall_progress = (
        data["% Complete"].mean()
        if len(data) > 0
        else 0
    )

    planned_progress = (
        data["Planned %"].mean()
        if len(data) > 0
        else 0
    )

    progress_variance = (
        overall_progress
        - planned_progress
    )

    # --------------------------------------------------------
    # Activity status
    # --------------------------------------------------------

    completed = int(
        (data["% Complete"] >= 100).sum()
    )

    not_started = int(
        (data["% Complete"] <= 0).sum()
    )

    in_progress = int(
        (
            (data["% Complete"] > 0)
            &
            (data["% Complete"] < 100)
        ).sum()
    )

    # --------------------------------------------------------
    # Schedule condition
    #
    # Existing MVP convention:
    # positive Schedule Variance = delayed
    # --------------------------------------------------------

    delayed = int(
        (data["Schedule Variance"] > 0).sum()
    )

    critical = int(
        data["_Critical"].sum()
    )

    # --------------------------------------------------------
    # Return authoritative dashboard KPI set
    # --------------------------------------------------------

    return {
        "overall_progress": float(
            overall_progress
        ),

        "planned_progress": float(
            planned_progress
        ),

        "progress_variance": float(
            progress_variance
        ),

        "total_activities": int(
            len(data)
        ),

        "completed": completed,

        "in_progress": in_progress,

        "not_started": not_started,

        "delayed": delayed,

        "critical": critical,
    }


def render_dashboard(progress_data):
    """
    Render the Step 6 Project Dashboard.
    """

    st.header("Step 6 — Project Dashboard")

    st.info(
        "Project-level overview of current progress, "
        "schedule performance and activity status."
    )

    # --------------------------------------------------
    # VALIDATE DATA
    # --------------------------------------------------

    if progress_data is None or progress_data.empty:

        st.warning(
            "No project progress data is available. "
            "Please update project progress in Step 5 first."
        )

        return

    # --------------------------------------------------
    # CALCULATE KPIs
    # --------------------------------------------------

    kpis = calculate_dashboard_kpis(
        progress_data
    )

    # --------------------------------------------------
    # TOP KPI ROW
    # --------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Overall Progress",
            f"{kpis['overall_progress']:.1f}%"
        )

    with col2:

        st.metric(
            "Planned Progress",
            f"{kpis['planned_progress']:.1f}%"
        )

    with col3:

        st.metric(
            "Progress Variance",
            f"{kpis['progress_variance']:+.1f}%"
        )

    with col4:

        st.metric(
            "Total Activities",
            kpis["total_activities"]
        )

    # --------------------------------------------------
    # ACTIVITY STATUS
    # --------------------------------------------------

    st.subheader("Activity Status")

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Completed",
            kpis["completed"]
        )

    with col2:

        st.metric(
            "In Progress",
            kpis["in_progress"]
        )

    with col3:

        st.metric(
            "Not Started",
            kpis["not_started"]
        )

    with col4:

        st.metric(
            "Delayed",
            kpis["delayed"]
        )

    # --------------------------------------------------
    # SCHEDULE CONDITION
    # --------------------------------------------------

    st.subheader("Schedule Condition")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Delayed Activities",
            kpis["delayed"]
        )

    with col2:

        st.metric(
            "Critical Activities",
            kpis["critical"]
        )

    # --------------------------------------------------
    # PROJECT PROGRESS
    # --------------------------------------------------

    st.divider()

    # ==========================================================
    # DASHBOARD CHARTS
    # ==========================================================

    chart_col1, chart_divider, chart_col2 = st.columns(
        [10, 1, 10]
    )

    # ----------------------------------------------------------
    # PROJECT PROGRESS
    # ----------------------------------------------------------

    with chart_col1:

        st.subheader("Project Progress")

        progress_chart_data = pd.DataFrame(
            {
                "Progress": [
                    kpis["planned_progress"],
                    kpis["overall_progress"],
                ]
            },
            index=[
                "Planned",
                "Actual",
            ]
        )

        fig_progress = go.Figure()

        fig_progress.add_trace(
            go.Bar(
                x=progress_chart_data.index,
                y=progress_chart_data["Progress"],
                marker=dict(
                    color="#7f8c8d"
                ),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Progress: %{y:.1f}%"
                    "<extra></extra>"
                ),
                showlegend=False
            )
        )

        fig_progress.update_layout(
            height=300,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=40
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(
                title="Progress (%)",
                range=[0, 100],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.15)",
                zeroline=False
            ),
            xaxis=dict(
                title="",
                showgrid=False
            )
        )

        st.plotly_chart(
            fig_progress,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True
            }
        )

    # ----------------------------------------------------------
    # VERTICAL DIVIDER
    # ----------------------------------------------------------

    with chart_divider:

        st.markdown(
            """
            <div style="
                height: 300px;
                border-left: 1px solid rgba(128,128,128,0.25);
                margin: 45px auto 0 auto;
            "></div>
            """,
            unsafe_allow_html=True
        )

    # ----------------------------------------------------------
    # ACTIVITY STATUS BREAKDOWN
    # ----------------------------------------------------------

    with chart_col2:

        st.subheader("Activity Status Breakdown")

        status_chart_data = pd.DataFrame(
            {
                "Activities": [
                    kpis["completed"],
                    kpis["in_progress"],
                    kpis["not_started"],
                    kpis["delayed"],
                ]
            },
            index=[
                "Completed",
                "In Progress",
                "Not Started",
                "Delayed",
            ]
        )

        fig_status = go.Figure()

        fig_status.add_trace(
            go.Bar(
                x=status_chart_data.index,
                y=status_chart_data["Activities"],
                marker=dict(
                    color="#7f8c8d"
                ),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    "Activities: %{y}"
                    "<extra></extra>"
                ),
                showlegend=False
            )
        )

        fig_status.update_layout(
            height=300,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=40
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(
                title="Activities",
                showgrid=True,
                gridcolor="rgba(128,128,128,0.15)",
                zeroline=False
            ),
            xaxis=dict(
                title="",
                showgrid=False
            )
        )

        st.plotly_chart(
            fig_status,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True
            }
        )

    # --------------------------------------------------
    # PROGRESS GANTT CHART
    # --------------------------------------------------

    st.divider()

    st.subheader("Progress Gantt Chart")

    render_progress_gantt(
        progress_data
    )

    # --------------------------------------------------
    # ACTIVITIES REQUIRING ATTENTION
    # --------------------------------------------------

    st.divider()

    st.subheader("Activities Requiring Attention")

    attention_data = progress_data.copy()

    attention_data = progress_data.copy()

    # --------------------------------------------------
    # FILTER OPTIONS
    # --------------------------------------------------

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:

        show_delayed_only = st.checkbox(
            "🔴 Delayed Activities Only",
            key="dashboard_delayed_only"
        )

    with filter_col2:

        show_critical_only = st.checkbox(
            "⚠️ Critical Activities Only",
            key="dashboard_critical_only"
        )

    # --------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------

    if show_delayed_only:

        attention_data = attention_data[
            attention_data["Schedule Variance"] > 0
        ]

    if show_critical_only and "Critical" in attention_data.columns:

        critical_values = (
            attention_data["Critical"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        attention_data = attention_data[
            critical_values.isin(
                ["yes", "true", "1"]
            )
        ]

    # --------------------------------------------------
    # DISPLAY COLUMNS
    # --------------------------------------------------

    attention_columns = [
        "ID",
        "WBS",
        "Activity",
        "Planned Start",
        "Planned Finish",
        "Actual Start",
        "% Complete",
        "Planned %",
        "Lag",
        "Schedule Variance",
        "Critical",
        "Progress Status",
    ]

    available_attention_columns = [
        column
        for column in attention_columns
        if column in attention_data.columns
    ]

    attention_display = attention_data[
        available_attention_columns
    ].copy()

    # --------------------------------------------------
    # FORMAT DATES
    # --------------------------------------------------

    date_columns = [
        "Planned Start",
        "Planned Finish",
        "Actual Start",
    ]

    for column in date_columns:

        if column in attention_display.columns:

            attention_display[column] = pd.to_datetime(
                attention_display[column],
                errors="coerce"
            ).dt.strftime(
                "%d %b %Y"
            )

            attention_display[column] = (
                attention_display[column]
                .replace("NaT", "")
            )

    # --------------------------------------------------
    # DISPLAY TABLE
    # --------------------------------------------------

    if attention_display.empty:

        st.success(
            "No activities currently require attention "
            "under the selected filters."
        )

    else:

        st.dataframe(
            attention_display,
            use_container_width=True,
            hide_index=True
        )



# ============================================================
# LOOK-AHEAD PLAN
# ============================================================

# ============================================================
# LOOK-AHEAD PLAN
# ============================================================

def render_lookahead_plan(
    progress_data,
):

    if (
        progress_data is None
        or progress_data.empty
    ):

        st.info(
            "No progress data is available for "
            "Look-Ahead analysis."
        )

        return

    data = progress_data.copy()

    # --------------------------------------------------------
    # Standardize schedule variance
    # --------------------------------------------------------

    data["Schedule Variance"] = pd.to_numeric(
        data.get(
            "Schedule Variance",
            0
        ),
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # Standardize progress
    # --------------------------------------------------------

    data["% Complete"] = pd.to_numeric(
        data.get(
            "% Complete",
            0
        ),
        errors="coerce"
    ).fillna(0)

    # --------------------------------------------------------
    # Standardize dates
    # --------------------------------------------------------

    for column in [
        "Planned Start",
        "Planned Finish",
        "Actual Start",
        "Actual Finish",
    ]:

        if column in data.columns:

            data[column] = pd.to_datetime(
                data[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # Standardize Critical flag
    # --------------------------------------------------------

    if "Critical" in data.columns:

        data["_Critical"] = (
            data["Critical"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin([
                "true",
                "yes",
                "1",
                "critical"
            ])
        )

    else:

        data["_Critical"] = False

    # --------------------------------------------------------
    # Identify activities requiring AI/recovery attention
    #
    # Existing MVP definition:
    #
    #     Delayed OR Critical
    #
    # Positive Schedule Variance means delayed.
    #
    # This filtered dataset is retained as BACKEND CONTEXT
    # for the AI and recovery functions.
    # --------------------------------------------------------

    data["_Delayed"] = (
        data["Schedule Variance"] > 0
    )

    attention_mask = (
        data["_Delayed"]
        |
        data["_Critical"]
    )

    lookahead = data[
        attention_mask
    ].copy()


    # --------------------------------------------------------
    # No activities requiring AI/recovery attention
    # --------------------------------------------------------

    if lookahead.empty:

        st.success(
            "No delayed or critical activities currently "
            "require AI-assisted recovery analysis."
        )

        return

    # --------------------------------------------------------
    # Sort by priority
    #
    # Critical activities first, then largest delay.
    # --------------------------------------------------------

    lookahead["_Priority"] = (
        lookahead["_Critical"]
        .astype(int)
        * 2
        +
        lookahead["_Delayed"]
        .astype(int)
    )

    lookahead = (
        lookahead
        .sort_values(
            by=[
                "_Priority",
                "Schedule Variance"
            ],
            ascending=[
                False,
                False
            ]
        )
        .copy()
    )

    # ========================================================
    # AI SCHEDULE RECOVERY ASSISTANT
    # ========================================================

    render_ai_planning_chat(
        lookahead
    )

    # ========================================================
    # RECOVERY SCENARIO
    # ========================================================

    st.divider()

    render_recovery_scenario(
        lookahead,
        progress_data
    )

    # ========================================================
    # AI RECOVERY RECOMMENDATIONS
    # ========================================================

    st.divider()

    render_ai_recovery_recommendations(
        lookahead
    )


def render_lookahead_gantt(lookahead):
    """
    Render a read-only Look-Ahead Gantt using the
    same visual language as the Step 5 Progress Gantt.
    """

    if lookahead.empty:
        return

    highlight_critical = st.session_state.get(
        "highlight_critical_progress",
        False
    )

    fig = go.Figure()

    for position, (_, activity) in enumerate(
        lookahead.iterrows()
    ):

        start = activity["Planned Start"]

        finish = activity["Planned Finish"]

        if pd.isna(start) or pd.isna(finish):
            continue

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

        activity_name = str(
            activity.get(
                "Activity",
                activity.get("ID", "")
            )
        )

        critical_value = activity.get(
            "Critical",
            False
        )

        is_critical = (
            str(critical_value)
            .strip()
            .lower()
            in ["yes", "true", "1"]
            or critical_value is True
        )

        # --------------------------------------------------
        # BASELINE
        # --------------------------------------------------

        baseline_color = (
            "#c0392b"
            if (
                highlight_critical
                and is_critical
            )
            else "#8f9499"
        )

        fig.add_trace(
            go.Bar(
                x=[duration_ms],
                y=[position],
                base=[start],
                orientation="h",

                marker=dict(
                    color=baseline_color
                ),

                hovertemplate=(
                    "<b>"
                    + activity_name
                    + "</b><br>"
                    "Planned Start: "
                    + start.strftime(
                        "%d %b %Y"
                    )
                    + "<br>"
                    "Planned Finish: "
                    + finish.strftime(
                        "%d %b %Y"
                    )
                    + "<br>"
                    "Schedule Variance: "
                    + str(
                        int(
                            round(
                                activity[
                                    "Schedule Variance"
                                ]
                            )
                        )
                    )
                    + " days"
                    + "<extra></extra>"
                ),

                showlegend=False
            )
        )

        # --------------------------------------------------
        # VARIANCE / RECOVERY EXTENSION
        # --------------------------------------------------

        variance = max(
            0,
            int(
                round(
                    float(
                        activity[
                            "Schedule Variance"
                        ]
                    )
                )
            )
        )

        if variance > 0:

            extension_start = (
                finish
                + pd.Timedelta(days=1)
            )

            extension_duration_ms = (
                variance
                * 24
                * 60
                * 60
                * 1000
            )

            pattern_color = (
                "#c0392b"
                if (
                    highlight_critical
                    and is_critical
                )
                else "#7f8c8d"
            )

            fig.add_trace(
                go.Bar(
                    x=[extension_duration_ms],
                    y=[position],
                    base=[extension_start],
                    orientation="h",

                    marker=dict(
                        color="rgba(0,0,0,0.02)",
                        pattern=dict(
                            shape="/",
                            fgcolor=pattern_color,
                            bgcolor="rgba(0,0,0,0)",
                            size=8,
                            solidity=0.25
                        )
                    ),

                    hovertemplate=(
                        "<b>"
                        + activity_name
                        + "</b><br>"
                        "Schedule Variance: "
                        + str(variance)
                        + " days"
                        + "<extra></extra>"
                    ),

                    showlegend=False
                )
            )

    # --------------------------------------------------
    # TODAY LINE
    # --------------------------------------------------

    today = pd.Timestamp.today().normalize()

    fig.add_vline(
        x=today,
        line_width=4,
        line_color="#f1c40f",
        line_dash="solid",
        layer="above"
    )

    # --------------------------------------------------
    # LAYOUT
    # --------------------------------------------------

    fig.update_layout(

        height=max(
            450,
            len(lookahead) * 45
        ),

        barmode="overlay",

        margin=dict(
            l=240,
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
            dtick=(
                24
                * 60
                * 60
                * 1000
            ),
            tickformat="%d %b",
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
                    len(lookahead)
                )
            ),

            ticktext=[
                str(activity)
                for activity in lookahead[
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

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": True,
            "responsive": True
        }
    )



def render_ai_planning_chat(lookahead_data):

    st.subheader("🤖 AI Schedule Recovery Assistant")

    st.caption(
        "Discuss schedule recovery options with AI. "
        "AI recommendations do not automatically change your baseline."
    )

    if lookahead_data is None or lookahead_data.empty:
        st.info(
            "Select Delayed and/or Critical activities above "
            "to start an AI planning discussion."
        )
        return

    # ---------------------------------------------------------
    # Model selection
    # ---------------------------------------------------------

    model_options = {
        "gpt-oss-20b": {
            "provider": "Groq",
            "model": "openai/gpt-oss-20b",
        },
        "gpt-oss-120b": {
            "provider": "Groq",
            "model": "openai/gpt-oss-120b",
        },
    }

    selected_model_name = st.selectbox(
        "Select AI Model",
        list(model_options.keys()),
        key="lookahead_selected_model",
    )

    selected_model = model_options[selected_model_name]

    st.caption(
        f"Provider: **{selected_model['provider']}**"
    )

    # ---------------------------------------------------------
    # Reset connection if model has changed
    # ---------------------------------------------------------

    connected_model = st.session_state.get(
        "lookahead_connected_model"
    )

    if (
        st.session_state.get("lookahead_ai_connected", False)
        and connected_model != selected_model_name
    ):
        st.session_state.lookahead_ai_connected = False
        st.session_state.lookahead_connected_api_key = None

    # ---------------------------------------------------------
    # API key
    # ---------------------------------------------------------

    api_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="Enter Groq API key",
        key="lookahead_api_key",
        help="Your API key is used only for the current AI session.",
    )

    # ---------------------------------------------------------
    # Connect
    # ---------------------------------------------------------

    if st.button(
        "🔌 Connect to AI",
        type="primary",
        use_container_width=True,
        key="lookahead_connect_ai",
    ):

        if not api_key.strip():

            st.error(
                "Please enter your Groq API key before connecting."
            )

        else:

            try:

                client = OpenAI(
                    api_key=api_key.strip(),
                    base_url="https://api.groq.com/openai/v1",
                )

                test_response = client.responses.create(
                    model=selected_model["model"],
                    input="Reply with the single word: Connected.",
                )

                if test_response.output_text:

                    st.session_state.lookahead_ai_connected = True

                    st.session_state.lookahead_connected_model = (
                        selected_model_name
                    )

                    st.session_state.lookahead_connected_api_key = (
                        api_key.strip()
                    )

                    st.success(
                        f"✓ Connection successful — "
                        f"{selected_model_name}"
                    )

                else:

                    st.error(
                        "The model responded, but no text was returned."
                    )

            except Exception as e:

                st.session_state.lookahead_ai_connected = False

                st.error(
                    "❌ Connection failed."
                )

                st.caption(
                    f"Details: {str(e)}"
                )

    # ---------------------------------------------------------
    # Connection status
    # ---------------------------------------------------------

    if not st.session_state.get(
        "lookahead_ai_connected",
        False
    ):
        return

    connected_model = st.session_state.get(
        "lookahead_connected_model"
    )

    connected_api_key = st.session_state.get(
        "lookahead_connected_api_key"
    )

    st.success(
        f"✓ AI connected — {connected_model}"
    )

    st.divider()

    # ---------------------------------------------------------
    # Conversation state
    # ---------------------------------------------------------

    if "lookahead_chat_history" not in st.session_state:
        st.session_state.lookahead_chat_history = []

    # ---------------------------------------------------------
    # Display previous conversation
    # ---------------------------------------------------------

    for message in st.session_state.lookahead_chat_history:

        if message["role"] == "user":

            st.markdown(
                f"**You:** {message['content']}"
            )

        else:

            st.markdown(
                f"**🤖 AI:** {message['content']}"
            )

    # ---------------------------------------------------------
    # User question
    # ---------------------------------------------------------

    st.subheader("💬 Recovery Planning Discussion")

    user_question = st.text_input(
        "Ask the AI",
        placeholder=(
            "e.g. How can I recover these delayed activities?"
        ),
        key="lookahead_user_question",
    )

    col1, col2 = st.columns(2)

    with col1:

        send_message = st.button(
            "➤ Send",
            type="primary",
            use_container_width=True,
            key="lookahead_send_message",
        )

    with col2:

        clear_chat = st.button(
            "🗑 Clear Discussion",
            use_container_width=True,
            key="lookahead_clear_chat",
        )

    # ---------------------------------------------------------
    # Clear conversation
    # ---------------------------------------------------------

    if clear_chat:

        st.session_state.lookahead_chat_history = []

        st.rerun()

    # ---------------------------------------------------------
    # Send message
    # ---------------------------------------------------------

    if send_message:

        if not user_question.strip():

            st.warning(
                "Please enter a question before sending."
            )

        else:

            # -------------------------------------------------
            # Build authoritative schedule context
            # -------------------------------------------------

            # Activities currently shown in Look-Ahead
            recovery_data = lookahead_data.copy()

            # -------------------------------------------------
            # Get authoritative project data sources
            # -------------------------------------------------

            # Recovery Scenario:
            # Application-calculated hypothetical schedule
            scenario_context_data = st.session_state.get(
                "recovery_scenario"
            )

            if (
                scenario_context_data is None
                or scenario_context_data.empty
            ):

                scenario_context_data = pd.DataFrame()

            else:

                scenario_context_data = (
                    scenario_context_data.copy()
                )

            # Step 5:
            # Current progress and schedule performance
            progress_context_data = st.session_state.get(
                "progress_data"
            )

            if (
                progress_context_data is None
                or progress_context_data.empty
            ):

                progress_context_data = recovery_data.copy()

            else:

                progress_context_data = (
                    progress_context_data.copy()
                )


            # Step 5A:
            # Application-calculated recovery scenario
            scenario_context_data = st.session_state.get(
                "recovery_scenario"
            )

            if (
                scenario_context_data is None
                or scenario_context_data.empty
            ):

                scenario_context_data = pd.DataFrame()

            else:

                scenario_context_data = (
                    scenario_context_data.copy()
                )


            # Step 4:
            # Approved baseline schedule and schedule logic
            baseline_context_data = st.session_state.get(
                "baseline_schedule"
            )


            if (
                baseline_context_data is None
                or baseline_context_data.empty
            ):

                baseline_context_data = pd.DataFrame()

            else:

                baseline_context_data = (
                    baseline_context_data.copy()
                )

            # -------------------------------------------------
            # Fields available to AI
            # -------------------------------------------------

            preferred_ai_columns = [
                "ID",
                "WBS",
                "Activity",
                "Planned Start",
                "Planned Finish",
                "Actual Start",
                "Actual Finish",
                "Duration",
                "% Complete",
                "Status",
                "Schedule Variance",
                "Lag",
                "Total Float",
                "Critical",
            ]

            # -------------------------------------------------
            # Recovery activity context
            # -------------------------------------------------

            recovery_columns = [
                column
                for column in preferred_ai_columns
                if column in recovery_data.columns
            ]

            recovery_context_data = (
                recovery_data[
                    recovery_columns
                ].copy()
            )

            recovery_context = (
                recovery_context_data.to_dict(
                    orient="records"
                )
            )

            # -------------------------------------------------
            # Current progress context
            # -------------------------------------------------

            progress_columns = [
                column
                for column in preferred_ai_columns
                if column in progress_context_data.columns
            ]

            progress_context_data = (
                progress_context_data[
                    progress_columns
                ].copy()
            )

            # -------------------------------------------------
            # Compact Current Progress Context
            # -------------------------------------------------

            progress_columns = [
                "ID",
                "Activity",
                "Planned Start",
                "Planned Finish",
                "Actual Start",
                "Actual Finish",
                "% Complete",
                "Status",
                "Schedule Variance",
                "Lag",
            ]

            progress_columns = [
                column
                for column in progress_columns
                if column in progress_context_data.columns
            ]

            compact_progress_data = (
                progress_context_data[
                    progress_columns
                ].copy()
            )


            # Keep the AI context focused on activities
            # currently relevant to project control.
            if len(compact_progress_data) > 40:

                compact_progress_data = (
                    compact_progress_data
                    .head(40)
                    .copy()
                )

            current_progress_context = (
                compact_progress_data
                .to_dict(
                    orient="records"
                )
            )

            # -------------------------------------------------
            # Recovery Scenario context
            # -------------------------------------------------

            # -------------------------------------------------
            # Compact Recovery Scenario Context
            # -------------------------------------------------

            scenario_columns = [
                "ID",
                "Activity",
                "Planned Finish",
                "Scenario Start",
                "Scenario Finish",
                "Scenario Change",
                "Scenario Status",
                "Affected by Recovery",
                "Critical",
            ]

            scenario_columns = [
                column
                for column in scenario_columns
                if column in scenario_context_data.columns
            ]

            scenario_context_data = (
                scenario_context_data[
                    scenario_columns
                ].copy()
            )

            recovery_scenario_context = (
                scenario_context_data
                .to_dict(
                    orient="records"
                )
            )


            # -------------------------------------------------
            # Approved baseline schedule context
            # -------------------------------------------------

            baseline_columns = [
                column
                for column in preferred_ai_columns
                if column in baseline_context_data.columns
            ]

            baseline_schedule_context_data = (
                baseline_context_data[
                    baseline_columns
                ].copy()
            )


            # -------------------------------------------------
            # Step 5B:
            # Prepare calculated recovery scenario for AI
            # -------------------------------------------------

            scenario_columns = [
                "ID",
                "Activity",
                "Planned Finish",
                "Scenario Start",
                "Scenario Finish",
                "Scenario Change",
                "Scenario Status",
                "Affected by Recovery",
                "Critical",
                "Baseline Project Finish",
                "Scenario Project Finish",
                "Project Finish Change",
                "Recovery Achieved",
            ]


            scenario_columns = [
                column
                for column in preferred_ai_columns
                if column in scenario_context_data.columns
            ]

            scenario_extra_columns = [
                "Scenario Start",
                "Scenario Finish",
                "Scenario Start Change",
                "Scenario Change",
                "Scenario Delay",
                "Scenario Improved",
                "Scenario Status",
                "Affected by Recovery",
                "Baseline Project Finish",
                "Scenario Project Finish",
                "Project Finish Change",
                "Recovery Achieved",
                "Recovery Scenario",
                "Recovery Target Activity",
            ]

            scenario_columns += [
                column
                for column in scenario_extra_columns
                if (
                    column in scenario_context_data.columns
                    and column not in scenario_columns
                )
            ]

            scenario_context_data = (
                scenario_context_data[
                    scenario_columns
                ].copy()
            )

            recovery_scenario_context = (
                scenario_context_data.to_dict(
                    orient="records"
                )
            )

            # -------------------------------------------------
            # Compact Approved Baseline Context
            # -------------------------------------------------

            baseline_columns = [
                "ID",
                "Activity",
                "Planned Start",
                "Planned Finish",
                "Duration",
                "Relationship",
                "Predecessor",
                "Total Float",
                "Critical",
            ]

            baseline_columns = [
                column
                for column in baseline_columns
                if column in baseline_context_data.columns
            ]

            compact_baseline_data = (
                baseline_context_data[
                    baseline_columns
                ].copy()
            )


            if len(compact_baseline_data) > 40:

                compact_baseline_data = (
                    compact_baseline_data
                    .head(40)
                    .copy()
                )

            baseline_schedule_context = (
                compact_baseline_data
                .to_dict(
                    orient="records"
                )
            )

            # -------------------------------------------------
            # Identify unavailable fields
            # -------------------------------------------------

            missing_ai_fields = [
                column
                for column in preferred_ai_columns
                if (
                    column not in progress_context_data.columns
                    and column not in baseline_context_data.columns
                    and column not in recovery_data.columns
                )
            ]

            missing_context_note = ""

            if missing_ai_fields:

                missing_context_note = (
                    "\n\nFIELDS NOT AVAILABLE IN THE "
                    "APPLICATION DATA:\n"
                    + ", ".join(
                        missing_ai_fields
                    )
                    + "\n"
                    "Do not infer or invent these fields."
                )

            # -------------------------------------------------
            # System instructions
            # -------------------------------------------------

            system_prompt = """
You are an AI construction planning and schedule recovery assistant.

You are assisting a construction project planner.

The Recovery Activities section contains activities currently
selected in the Look-Ahead view because they are delayed,
critical, or both.

The Complete Project Schedule Context contains the available
project schedule and progress data for verifying schedule logic.

IMPORTANT RULES:

1. Use only facts explicitly provided in the application data.

2. Treat application-calculated values such as dates, progress,
   schedule variance, critical status, float, lag, and
   relationships as authoritative.

3. Use the APPROVED BASELINE SCHEDULE AND SCHEDULE LOGIC
   to verify predecessors, successors, relationships, float,
   dates, durations and schedule logic.

4. Never invent relationships, predecessors, successors,
   float, durations, resources, causes, constraints,
   or other project facts.

5. Never assume that activities are sequential unless the
   supplied relationship data confirms it.

6. A schedule relationship does not automatically prove
   actual delay causation. Distinguish schedule logic from
   proven delay causation.

7. Never invent a recovery duration, production rate,
   number of crews, number of shifts, saved days, or
   other quantitative recovery result unless that value
   is explicitly provided or calculated by the application.

8. Do not treat a calculated current-performance field such
   as Lag or Schedule Variance as a baseline relationship
   parameter that can be changed.

9. Do not perform or claim downstream schedule movement from a
    hypothetical recovery action unless the application has
    actually calculated that recovery scenario.

10. Do not treat Lag in Current Project Progress Data as a
    baseline relationship lag.

11. Do not describe a hypothetical future schedule date as a
verified project date.

12. When discussing a hypothetical recovery action, label its
    downstream effects as "potential" unless calculated by the
    application.

13. Do not recommend changing a baseline predecessor,
   relationship, lag, duration, or other baseline parameter
   unless the planner explicitly asks to evaluate a baseline
   change. If such a change is discussed, clearly identify it
   as a proposed baseline change requiring formal review.

14. A verified predecessor relationship describes schedule
    logic. It does not prove actual delay causation.

15. If a required field is not available in the application
   data, say so briefly rather than guessing.

16. Clearly distinguish between:

   FACT:
   Directly supported by application data.

   RECOMMENDATION:
   A proposed recovery option for planner consideration.

   ASSUMPTION:
   Something that requires confirmation.

17. Never claim that a recovery action has been implemented.

18. Never modify, replace, or assume modification of the
    approved baseline.

19. Recovery recommendations are options for the planner
    to review and decide.

20. If a RECOVERY SCENARIO is provided, it is an
    application-calculated hypothetical schedule.

21. Treat Scenario Start, Scenario Finish, Scenario Change,
    Scenario Delay and Scenario Improved as authoritative
    application-calculated values.

22. The RECOVERY SCENARIO must be used to interpret the
    calculated schedule impact. Do not recalculate its dates
    yourself.

23. Clearly distinguish between:
    - Approved Baseline
    - Current Project Progress
    - Calculated Recovery Scenario

24. A recovery scenario is hypothetical and has NOT been
    implemented unless the planner explicitly confirms
    implementation outside this AI discussion.

25. Never claim that the approved baseline has changed because
    a recovery scenario was calculated.

26. If no Recovery Scenario is available, discuss recovery
    options normally and state that a calculated scenario is
    not currently available when relevant.

RESPONSE STYLE:

RESPONSE STYLE:

1. Be concise and decision-oriented by default.

2. Normally respond in 3–6 short points or a compact table.

3. Do not repeat the complete Look-Ahead activity table
   unless specifically requested.

4. Do not repeat information already clearly visible in
   the Look-Ahead screen unless necessary.

5. Give the most useful recommendation first when appropriate.

6. For recovery options, briefly state:

   - Option
   - Potential benefit
   - Main risk
   - Decision or information required

7. Do not provide lengthy explanations unless requested.

8. If the planner asks why, explain, compare, calculate,
   or otherwise requests detail, provide more detail.

9. When several reasonable recovery options exist, present
   them briefly and allow the planner to choose which one
   to explore.

10. Keep the discussion focused on practical construction
    planning and schedule recovery.

The approved baseline remains controlled by the planner.
"""

            # -------------------------------------------------
            # Previous conversation
            # -------------------------------------------------

            chat_history = st.session_state.get(
                "lookahead_chat_history",
                []
            )

            # Keep only the most recent messages so the AI
            # context does not grow indefinitely.

            MAX_CHAT_MESSAGES = 12

            if len(chat_history) > MAX_CHAT_MESSAGES:

                chat_history = chat_history[
                    -MAX_CHAT_MESSAGES:
                ]

                st.session_state[
                    "lookahead_chat_history"
                ] = chat_history

            conversation_context = ""

            for message in chat_history:

                conversation_context += (
                    f"{message['role'].upper()}: "
                    f"{message['content']}\n\n"
                )

            # -------------------------------------------------
            # Build complete AI context
            # -------------------------------------------------

            context_prompt = f"""
RECOVERY ACTIVITIES CURRENTLY REQUIRING ATTENTION:

{recovery_context}


CURRENT PROJECT PROGRESS DATA:

{current_progress_context}

The three schedule views have different purposes:

APPROVED BASELINE:
The approved contractual/planned schedule and its schedule logic.

CURRENT PROJECT PROGRESS:
What is actually happening on the project now.

CALCULATED RECOVERY SCENARIO:
A hypothetical schedule calculated by the application after
the planner proposes a recovery finish date.

The Recovery Scenario must never be treated as the approved
baseline or as an implemented project change.


APPROVED BASELINE SCHEDULE AND SCHEDULE LOGIC:

{baseline_schedule_context}


CALCULATED RECOVERY SCENARIO:

{recovery_scenario_context}


IMPORTANT DATA RULES:

1. CURRENT PROJECT PROGRESS DATA is authoritative for
   current actual progress, actual dates, percentage complete,
   schedule variance, lag, status and current performance.

2. APPROVED BASELINE SCHEDULE AND SCHEDULE LOGIC is authoritative
   for planned dates, duration, predecessor, relationship,
   float and critical-path information.

3. Use the APPROVED BASELINE SCHEDULE AND SCHEDULE LOGIC to
   verify predecessor and successor relationships.

4. A predecessor relationship establishes schedule logic,
   but does not by itself prove that one activity is the
   actual cause of another activity's delay.

5. Do not claim actual delay causation unless the available
   application data supports that conclusion.

6. Do not invent recovery durations or claim that a recovery
   action will recover a specific number of days unless the
   application has calculated that result.

7. If a CALCULATED RECOVERY SCENARIO is provided, treat the
   following values as authoritative application-calculated
   results:

   - Scenario Start
   - Scenario Finish
   - Scenario Start Change
   - Scenario Change
   - Scenario Status
   - Affected by Recovery
   - Baseline Project Finish
   - Scenario Project Finish
   - Project Finish Change
   - Recovery Achieved

8. Do not recalculate, override or independently derive the
   application-calculated Recovery Scenario dates or impacts.

9. Use the Recovery Scenario to explain:
   - which activities were affected
   - which activities moved earlier
   - which activities moved later
   - which activities remained unchanged
   - the calculated project finish impact
   - the calculated recovery achieved

10. Treat the Recovery Scenario as hypothetical only.
    It does not modify or replace the approved baseline.

11. Never claim that a recovery action has been implemented
    merely because a scenario was calculated.

12. Do not invent the method, resources, productivity,
    additional crews, working hours or other means by which
    the proposed recovery would actually be achieved.

13. Clearly distinguish between:
    FACT — information directly supported by application data.
    CALCULATED RESULT — a result produced by the application.
    RECOMMENDATION — an AI-proposed action.
    ASSUMPTION — an explicitly stated assumption.

14. If no CALCULATED RECOVERY SCENARIO is available, do not
    invent scenario results. State that no calculated scenario
    is currently available when relevant.

15. If information is unavailable, state that it is unavailable.

16. Keep responses concise and decision-oriented.

17. Prefer tables for activity-level comparisons.

18. When discussing multiple activities, use a compact table
    rather than a long paragraph.

19. Do not repeat information already visible in the application.

20. For calculated recovery scenarios, prefer this structure:

    | Activity | Baseline Finish | Scenario Finish | Change | Status |

    Then provide only the key project-level impact below the table.

21. Avoid lengthy summaries unless the user explicitly asks
    for detailed explanation.

22. Do not repeat the same conclusion in multiple sections.

{missing_context_note}


PREVIOUS CONVERSATION:

{conversation_context}


CURRENT USER QUESTION:

{user_question}
"""

            # -------------------------------------------------
            # Send to Groq
            # -------------------------------------------------

            try:

                client = OpenAI(
                    api_key=connected_api_key,
                    base_url="https://api.groq.com/openai/v1",
                )

                response = client.responses.create(
                    model=model_options[
                        connected_model
                    ]["model"],
                    instructions=system_prompt,
                    input=context_prompt,
                )

                ai_response = response.output_text

                if not ai_response:

                    st.error(
                        "The AI responded, but no text was returned."
                    )

                else:

                    st.session_state.lookahead_chat_history.append(
                        {
                            "role": "user",
                            "content": user_question,
                        }
                    )

                    st.session_state.lookahead_chat_history.append(
                        {
                            "role": "assistant",
                            "content": ai_response,
                        }
                    )

                    st.rerun()

            except Exception as e:

                st.error(
                    "❌ AI request failed."
                )

                st.caption(
                    f"Details: {str(e)}"
                )


# ============================================================
# AI RECOVERY RECOMMENDATIONS
# ============================================================

def render_ai_recovery_recommendations(
    lookahead_data
):

    st.subheader(
        "Recovery Recommendations"
    )

    st.write(
        "Generate AI-assisted recovery options for the "
        "activities currently requiring attention. "
        "Recommendations are advisory only and do not "
        "modify the approved baseline."
    )

    # --------------------------------------------------------
    # Required project data
    # --------------------------------------------------------

    progress_data = st.session_state.get(
        "progress_data"
    )

    baseline = st.session_state.get(
        "baseline_schedule"
    )

    if (
        progress_data is None
        or progress_data.empty
    ):

        st.info(
            "Current project progress data is unavailable."
        )

        return

    if (
        baseline is None
        or baseline.empty
    ):

        st.info(
            "Approved baseline schedule is unavailable."
        )

        return

    # --------------------------------------------------------
    # AI connection check
    # --------------------------------------------------------

    ai_connected = st.session_state.get(
        "lookahead_ai_connected",
        False
    )

    if not ai_connected:

        st.info(
            "Connect the AI Planning Assistant above "
            "before generating recovery recommendations."
        )

        return

    # --------------------------------------------------------
    # Restrict candidates to current Look-Ahead activities
    # --------------------------------------------------------

    lookahead_ids = set(
        lookahead_data["ID"]
        .astype(str)
        .str.strip()
    )

    recovery_progress = progress_data[
        progress_data["ID"]
        .astype(str)
        .str.strip()
        .isin(lookahead_ids)
    ].copy()

    if recovery_progress.empty:

        st.info(
            "No current delayed or critical activities "
            "are available for recovery recommendations."
        )

        return

    # --------------------------------------------------------
    # Build compact progress context
    # --------------------------------------------------------

    preferred_progress_columns = [
        "ID",
        "WBS",
        "Activity",
        "Planned Start",
        "Planned Finish",
        "Actual Start",
        "Actual Finish",
        "Duration",
        "% Complete",
        "Planned %",
        "Progress Status",
        "Schedule Variance",
        "Lag",
        "Critical",
    ]

    progress_columns = [
        column
        for column in preferred_progress_columns
        if column in recovery_progress.columns
    ]

    progress_context = (
        recovery_progress[
            progress_columns
        ]
        .to_dict(
            orient="records"
        )
    )

    # --------------------------------------------------------
    # Build baseline context
    # --------------------------------------------------------

    baseline_columns = [
        "ID",
        "WBS",
        "Activity",
        "Planned Start",
        "Planned Finish",
        "Duration",
        "Relationship",
        "Predecessor",
        "Total Float",
        "Critical",
    ]

    available_baseline_columns = [
        column
        for column in baseline_columns
        if column in baseline.columns
    ]

    baseline_context = (
        baseline[
            available_baseline_columns
        ]
        .to_dict(
            orient="records"
        )
    )

    # --------------------------------------------------------
    # Generate button
    #
    # IMPORTANT:
    # AI is called ONLY when the user explicitly clicks
    # this button.
    # --------------------------------------------------------

    if st.button(
        "Generate Recovery Recommendations",
        type="primary",
        use_container_width=True,
        key="generate_recovery_recommendations",
    ):

        with st.spinner(
            "Generating recovery recommendations..."
        ):

            try:

                client = OpenAI(
                    api_key=st.session_state.get(
                        "lookahead_connected_api_key"
                    ),
                    base_url="https://api.groq.com/openai/v1"
                )

                model = st.session_state.get(
                    "lookahead_connected_model"
                )

                # --------------------------------------------------------
                # Normalize Groq model identifier
                # --------------------------------------------------------

                if model == "gpt-oss-20b":

                    model = "openai/gpt-oss-20b"

                elif model == "gpt-oss-120b":

                    model = "openai/gpt-oss-120b"

                if not st.session_state.get(
                    "lookahead_connected_api_key"
                ):

                    st.error(
                        "AI connection is unavailable. "
                        "Please reconnect the AI Planning Assistant."
                    )

                    return

                if not model:

                    st.error(
                        "AI model is not configured."
                    )

                    return

                prompt = f"""
You are a construction planning and project-control
assistant supporting a professional construction planner.

Your role is to ANALYZE the supplied project data and
identify practical recovery strategies for the activities
currently requiring attention.

The supplied data is authoritative.

STRICT DATA AND SAFETY RULES:

1. Use ONLY facts contained in the supplied project data.

2. NEVER invent or assume:
   - manpower quantities
   - crew sizes
   - shift arrangements
   - working hours
   - equipment
   - plant
   - material specifications
   - productivity rates
   - quantities
   - costs
   - resources
   - construction methods
   - site conditions
   - weather conditions
   - permits
   - approvals
   - contractual constraints
   - dates
   - durations
   - relationships
   - predecessors

3. Do NOT recommend a specific resource, equipment,
   material, productivity rate, shift pattern or
   construction method unless that information is
   explicitly present in the supplied data.

4. You MAY identify a recovery STRATEGY CATEGORY,
   such as:
   - additional resources
   - increased productivity
   - resequencing
   - parallel working
   - earlier start
   - reduced activity duration
   - predecessor acceleration

   However, if the required supporting information is
   not available, clearly state:

   "Requires planner validation."

5. Do NOT calculate a recovery finish date unless it can
   be directly supported by the supplied project data.

6. Do NOT calculate project finish impact.

7. Do NOT modify, replace or reinterpret the approved
   baseline.

8. Do NOT create new activities.

9. Do NOT create or change relationships.

10. Do NOT claim that a recovery strategy will recover
    a specific number of days unless that result has
    been calculated by the deterministic recovery
    scenario engine.

11. Clearly distinguish:
    - FACT = directly supported by supplied data
    - POTENTIAL STRATEGY = planning option requiring
      planner validation
    - UNKNOWN = information not available in the data

12. If the data is insufficient to recommend a specific
    intervention, say so explicitly rather than filling
    the gap with assumptions.

13. Focus ONLY on the activities supplied in the current
    Look-Ahead data.

14. Recommendations are advisory. They must never
    automatically change the baseline or project schedule.

                Return the recovery recommendations as STRICT JSON.

                Do NOT return Markdown.
                Do NOT return headings.
                Do NOT return bullet points.
                Do NOT return code fences.
                Do NOT include any text before or after the JSON.

                Keep every response concise.
                Do not repeat detailed schedule data already supplied
                in the project context.

                Use exactly this structure:

                {{
                  "recommendations": [
                    {{
                      "option": 1,
                      "recovery_strategy": "2-4 words",
                      "target_activity": "Activity ID and short activity name",
                      "current_situation": "Maximum 3-4 words",
                      "potential_recovery_strategy": "One concise sentence",
                      "required_planner_validation": "One concise sentence",
                      "proposed_finish": "Date only if directly supportable; otherwise Not calculated — requires deterministic scenario analysis.",
                      "expected_benefit": "One concise sentence",
                      "constraints_risks": "One concise sentence or Not available."
                    }}
                  ]
                }}

                IMPORTANT OUTPUT RULES:
                - "option" must be a sequential integer.
                - "target_activity" must use only an activity supplied in the project data.
                - "current_situation" MUST contain no more than 3-4 words.
                - Prefer concise factual phrases such as:
                  "5 days behind"
                  "4 days behind"
                  "Not started"
                  "Critical and delayed"
                  "3 days behind"
                - Do NOT repeat planned dates, duration, predecessor,
                  actual dates, float, or other detailed schedule data
                  in "current_situation".
                - "recovery_strategy" must be a short category such as:
                  "Earlier start", "Resequencing", "Additional resources",
                  or "Parallel working".
                - "potential_recovery_strategy" must be planning-level only.
                - "required_planner_validation" must state what the planner
                  needs to confirm before implementation.
                - Do not invent a proposed finish date.
                - Use a proposed finish date only when it is directly
                  supported by deterministic scenario analysis already
                  supplied in the context.
                - "expected_benefit" must be qualitative and concise unless
                  a deterministic numerical benefit is already supplied.
                - Do not invent constraints or risks.
                - If information is unavailable, explicitly state
                  "Not available."
                - Return only valid JSON.

IMPORTANT:

The deterministic recovery scenario engine is the only
component permitted to calculate scenario dates,
downstream effects, affected activities or project finish
impact.

Do not perform those calculations yourself.

CURRENT LOOK-AHEAD PROGRESS DATA:

{progress_context}

APPROVED BASELINE DATA:

{baseline_context}
"""

                response = client.responses.create(
                    model=model,
                    input=prompt,
                )

                recommendation_text = (
                    response.output_text
                    if hasattr(
                        response,
                        "output_text"
                    )
                    else str(response)
                )

                # --------------------------------------------------------
                # Parse strict JSON returned by the AI
                # --------------------------------------------------------

                import json

                cleaned_response = (
                    recommendation_text
                    .strip()
                )

                # Remove accidental Markdown code fences
                if cleaned_response.startswith(
                    "```json"
                ):

                    cleaned_response = (
                        cleaned_response[7:]
                        .strip()
                    )

                elif cleaned_response.startswith(
                    "```"
                ):

                    cleaned_response = (
                        cleaned_response[3:]
                        .strip()
                    )

                if cleaned_response.endswith(
                    "```"
                ):

                    cleaned_response = (
                        cleaned_response[:-3]
                        .strip()
                    )

                recommendations_json = json.loads(
                    cleaned_response
                )

                recommendations = (
                    recommendations_json.get(
                        "recommendations",
                        []
                    )
                )

                if not isinstance(
                    recommendations,
                    list
                ):

                    raise ValueError(
                        "AI returned an invalid "
                        "recommendations structure."
                    )

                st.session_state[
                    "recovery_recommendations"
                ] = recommendations

                st.session_state[
                    "recovery_recommendations_generated_for"
                ] = sorted(
                    lookahead_ids
                )

            except Exception as e:

                st.error(
                    f"Unable to generate recovery "
                    f"recommendations: {e}"
                )

    # --------------------------------------------------------
    # Display persisted recommendations
    # --------------------------------------------------------

    recommendations = (
        st.session_state.get(
            "recovery_recommendations"
        )
    )

    # --------------------------------------------------------
    # Ensure recommendations use the new structured format
    # --------------------------------------------------------

    if isinstance(
        recommendations,
        str
    ):

        # Old-format recommendations may still exist
        # in Streamlit session state from a previous run.
        recommendations = None

        st.session_state.pop(
            "recovery_recommendations",
            None
        )

    if recommendations:

        st.divider()

        st.markdown(
            "### AI-Generated Recovery Recommendations"
        )

        st.caption(
            "Advisory planning options based only on the "
            "current Look-Ahead data. The approved baseline "
            "is not modified."
        )

        # --------------------------------------------------------
        # SUMMARY TABLE
        # --------------------------------------------------------

        recommendation_rows = []

        for recommendation in recommendations:

            recommendation_rows.append(
                {
                    "Option": recommendation.get(
                        "option",
                        ""
                    ),
                    "Target Activity": recommendation.get(
                        "target_activity",
                        ""
                    ),
                    "Current Situation": recommendation.get(
                        "current_situation",
                        ""
                    ),
                    "Recovery Strategy": recommendation.get(
                        "recovery_strategy",
                        ""
                    ),
                    "Planner Validation": recommendation.get(
                        "required_planner_validation",
                        ""
                    ),
                    "Expected Benefit": recommendation.get(
                        "expected_benefit",
                        ""
                    )
                }
            )

        recommendation_table = pd.DataFrame(
            recommendation_rows
        )

        st.dataframe(
            recommendation_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Option": st.column_config.NumberColumn(
                    "Option",
                    width="small"
                ),
                "Target Activity": st.column_config.TextColumn(
                    "Target Activity",
                    width="medium"
                ),
                "Current Situation": st.column_config.TextColumn(
                    "Current Situation",
                    width="small"
                ),
                "Recovery Strategy": st.column_config.TextColumn(
                    "Recovery Strategy",
                    width="medium"
                ),
                "Planner Validation": st.column_config.TextColumn(
                    "Planner Validation",
                    width="large"
                ),
                "Expected Benefit": st.column_config.TextColumn(
                    "Expected Benefit",
                    width="large"
                ),
            }
        )

        # --------------------------------------------------------
        # DETAILED RECOMMENDATIONS
        # --------------------------------------------------------

        st.markdown(
            "#### Recommendation Details"
        )

        for recommendation in recommendations:

            option = recommendation.get(
                "option",
                ""
            )

            strategy = recommendation.get(
                "recovery_strategy",
                "Recovery Option"
            )

            target_activity = recommendation.get(
                "target_activity",
                ""
            )

            with st.expander(
                f"Recovery Option {option} — "
                f"{strategy}"
            ):

                st.markdown(
                    f"**Target Activity**  \n"
                    f"{target_activity}"
                )

                st.markdown(
                    "**Current Situation**"
                )

                st.write(
                    recommendation.get(
                        "current_situation",
                        ""
                    )
                )

                st.markdown(
                    "**Potential Recovery Strategy**"
                )

                st.write(
                    recommendation.get(
                        "potential_recovery_strategy",
                        ""
                    )
                )

                st.markdown(
                    "**Required Planner Validation**"
                )

                st.write(
                    recommendation.get(
                        "required_planner_validation",
                        ""
                    )
                )

                st.markdown(
                    "**Proposed Finish**"
                )

                st.write(
                    recommendation.get(
                        "proposed_finish",
                        ""
                    )
                )

                st.markdown(
                    "**Expected Benefit**"
                )

                st.write(
                    recommendation.get(
                        "expected_benefit",
                        ""
                    )
                )

                st.markdown(
                    "**Constraints / Risks**"
                )

                st.write(
                    recommendation.get(
                        "constraints_risks",
                        ""
                    )
                )

        st.caption(
            "AI recommendations are advisory only. "
            "They do not modify the approved baseline."
        )



def calculate_recovery_scenario(
    baseline_schedule,
    progress_data,
    activity_id,
    target_finish_date,
):
    """
    Create a read-only recovery scenario.

    The approved baseline is never modified.

    The planner proposes a new finish date for one activity.
    The application calculates the hypothetical downstream
    effect through Finish-to-Start relationships.
    """

    if baseline_schedule is None or baseline_schedule.empty:
        return None, "Approved baseline schedule is unavailable."

    if progress_data is None or progress_data.empty:
        return None, "Current project progress data is unavailable."

    baseline = baseline_schedule.copy()
    progress = progress_data.copy()

    required_columns = [
        "ID",
        "Activity",
        "Planned Start",
        "Planned Finish",
        "Duration",
        "Relationship",
        "Predecessor",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in baseline.columns
    ]

    if missing_columns:
        return (
            None,
            "Baseline is missing required fields: "
            + ", ".join(missing_columns),
        )

    # -------------------------------------------------
    # Normalize dates
    # -------------------------------------------------

    baseline["Planned Start"] = pd.to_datetime(
        baseline["Planned Start"],
        errors="coerce",
    )

    baseline["Planned Finish"] = pd.to_datetime(
        baseline["Planned Finish"],
        errors="coerce",
    )

    target_finish_date = pd.to_datetime(
        target_finish_date,
        errors="coerce",
    )

    if pd.isna(target_finish_date):
        return None, "Invalid recovery target date."

    if activity_id not in baseline["ID"].astype(str).values:
        return (
            None,
            f"Activity {activity_id} was not found in the approved baseline.",
        )

    # -------------------------------------------------
    # Create scenario from baseline
    # -------------------------------------------------

    scenario = baseline.copy()

    scenario["Scenario Start"] = scenario["Planned Start"]
    scenario["Scenario Finish"] = scenario["Planned Finish"]

    scenario["Scenario Change"] = 0
    scenario["Scenario Status"] = "Unchanged"

    # -------------------------------------------------
    # Identify selected activity
    # -------------------------------------------------

    selected_index = scenario[
        scenario["ID"].astype(str) == str(activity_id)
    ].index[0]

    original_start = scenario.loc[
        selected_index,
        "Planned Start",
    ]

    original_finish = scenario.loc[
        selected_index,
        "Planned Finish",
    ]

    duration = scenario.loc[
        selected_index,
        "Duration",
    ]

    if pd.isna(duration):
        return (
            None,
            "Selected activity does not have a valid duration.",
        )

    duration = int(duration)

    # -------------------------------------------------
    # Apply planner's proposed recovery finish
    # -------------------------------------------------

    scenario.loc[
        selected_index,
        "Scenario Finish"
    ] = target_finish_date

    scenario.loc[
        selected_index,
        "Scenario Start"
    ] = (
        target_finish_date
        - timedelta(days=duration - 1)
    )

    # -------------------------------------------------
    # Build predecessor / successor maps
    # -------------------------------------------------

    predecessor_map = {}

    for _, row in scenario.iterrows():

        activity = str(row["ID"])

        predecessor_value = row.get(
            "Predecessor",
            "",
        )

        if pd.isna(predecessor_value):
            predecessor_value = ""

        predecessor_map[activity] = (
            str(predecessor_value).strip()
        )

    successor_map = {
        str(row["ID"]): []
        for _, row in scenario.iterrows()
    }

    for activity, predecessor_value in predecessor_map.items():

        if not predecessor_value:
            continue

        predecessor_ids = [
            item.strip()
            for item in predecessor_value.split(",")
            if item.strip()
        ]

        for predecessor_id in predecessor_ids:

            if predecessor_id in successor_map:

                successor_map[
                    predecessor_id
                ].append(activity)

    # -------------------------------------------------
    # Track activities affected by the recovery
    # -------------------------------------------------

    affected_activities = {
        str(activity_id)
    }

    # -------------------------------------------------
    # Validate predecessor references
    # -------------------------------------------------

    known_activity_ids = set(
        scenario["ID"]
        .astype(str)
        .str.strip()
    )

    invalid_predecessors = []

    for activity, predecessor_value in predecessor_map.items():

        if not predecessor_value:
            continue

        predecessor_ids = [
            item.strip()
            for item in predecessor_value.split(",")
            if item.strip()
        ]

        for predecessor_id in predecessor_ids:

            if predecessor_id not in known_activity_ids:

                invalid_predecessors.append(
                    f"{activity} → {predecessor_id}"
                )

    if invalid_predecessors:

        return (
            None,
            "Recovery scenario contains invalid "
            "predecessor references: "
            + ", ".join(invalid_predecessors),
        )

    # -------------------------------------------------
    # Propagate recovery through FS relationships
    #
    # IMPORTANT:
    #
    # For activities with multiple FS predecessors,
    # the successor must respect the LATEST required
    # start date from ALL applicable predecessors.
    #
    # This prevents one recovered predecessor from
    # incorrectly pulling an activity earlier while
    # another predecessor still controls its start.
    # -------------------------------------------------

    queue = [
        str(activity_id)
    ]

    processed = set()

    iteration = 0
    max_iterations = len(scenario) * 3 + 10

    while queue and iteration < max_iterations:

        iteration += 1

        current_activity = queue.pop(0)

        if current_activity in processed:
            continue

        processed.add(current_activity)

        # -------------------------------------------------
        # Find all successors of the current activity
        # -------------------------------------------------

        successor_ids = successor_map.get(
            current_activity,
            [],
        )

        if not successor_ids:
            continue

        for successor_id in successor_ids:

            successor_rows = scenario[
                scenario["ID"].astype(str)
                == str(successor_id)
            ]

            if successor_rows.empty:
                continue

            successor_index = successor_rows.index[0]

            relationship = str(
                scenario.loc[
                    successor_index,
                    "Relationship",
                ]
            ).strip()

            # -------------------------------------------------
            # Only FS is supported by the recovery engine
            # in this increment.
            # -------------------------------------------------

            if "Finish-to-Start" not in relationship:
                continue

            successor_duration = scenario.loc[
                successor_index,
                "Duration",
            ]

            if pd.isna(successor_duration):

                return (
                    None,
                    f"Activity {successor_id} does not "
                    "have a valid duration.",
                )

            successor_duration = int(
                successor_duration
            )

            # -------------------------------------------------
            # Determine the controlling start date.
            #
            # We must evaluate ALL FS predecessors of this
            # successor, not just the predecessor currently
            # being propagated.
            # -------------------------------------------------

            successor_predecessors = []

            predecessor_value = predecessor_map.get(
                str(successor_id),
                "",
            )

            if predecessor_value:

                successor_predecessors = [
                    item.strip()
                    for item in predecessor_value.split(",")
                    if item.strip()
                ]

            required_starts = []

            for predecessor_id in successor_predecessors:

                predecessor_rows = scenario[
                    scenario["ID"].astype(str)
                    == str(predecessor_id)
                ]

                if predecessor_rows.empty:
                    continue

                predecessor_index = (
                    predecessor_rows.index[0]
                )

                predecessor_relationship = str(
                    scenario.loc[
                        predecessor_index,
                        "Relationship",
                    ]
                ).strip()

                if (
                    "Finish-to-Start"
                    not in predecessor_relationship
                ):
                    continue

                predecessor_finish = (
                    scenario.loc[
                        predecessor_index,
                        "Scenario Finish",
                    ]
                )

                if pd.notna(predecessor_finish):

                    required_starts.append(
                        predecessor_finish
                        + timedelta(days=1)
                    )

            # -------------------------------------------------
            # If no valid FS predecessor is currently
            # controlling the successor, leave it unchanged.
            # -------------------------------------------------

            if not required_starts:
                continue

            # -------------------------------------------------
            # The latest predecessor requirement controls.
            # -------------------------------------------------

            required_start = max(
                required_starts
            )

            required_finish = (
                required_start
                + timedelta(
                    days=successor_duration - 1
                )
            )

            current_scenario_start = scenario.loc[
                successor_index,
                "Scenario Start",
            ]

            current_scenario_finish = scenario.loc[
                successor_index,
                "Scenario Finish",
            ]

            # -------------------------------------------------
            # Update only when the calculated FS constraint
            # actually changes the successor schedule.
            # -------------------------------------------------

            if (
                pd.isna(current_scenario_start)
                or required_start
                != current_scenario_start
            ):

                scenario.loc[
                    successor_index,
                    "Scenario Start"
                ] = required_start

                scenario.loc[
                    successor_index,
                    "Scenario Finish"
                ] = required_finish

                successor_id_string = str(
                    successor_id
                )

                affected_activities.add(
                    successor_id_string
                )

                # Re-evaluate this successor so that
                # any downstream activities are recalculated.
                queue.append(
                    successor_id_string
                )

    # -------------------------------------------------
    # Detect excessive propagation
    # -------------------------------------------------

    if iteration >= max_iterations:

        return (
            None,
            "Recovery scenario propagation could not "
            "converge. Please check the baseline "
            "predecessor relationships for circular "
            "or conflicting dependencies.",
        )

    # -------------------------------------------------
    # Calculate scenario changes
    # -------------------------------------------------

    scenario["Scenario Change"] = (
        scenario["Scenario Finish"]
        - scenario["Planned Finish"]
    ).dt.days

    scenario["Scenario Start Change"] = (
        scenario["Scenario Start"]
        - scenario["Planned Start"]
    ).dt.days

    scenario["Scenario Delay"] = (
        scenario["Scenario Change"]
        .clip(lower=0)
    )

    scenario["Scenario Improved"] = (
        scenario["Scenario Change"] < 0
    )

    # -------------------------------------------------
    # Classify scenario status
    # -------------------------------------------------

    def classify_scenario_status(row):

        activity = str(row["ID"])

        if activity == str(activity_id):
            return "Recovery Target"

        change = row["Scenario Change"]

        if pd.isna(change):
            return "Unknown"

        if change < 0:
            return "Moved Earlier"

        if change > 0:
            return "Moved Later"

        return "Unchanged"

    scenario["Scenario Status"] = scenario.apply(
        classify_scenario_status,
        axis=1,
    )

    # -------------------------------------------------
    # Project-level impact
    # -------------------------------------------------

    baseline_project_finish = (
        baseline["Planned Finish"].max()
    )

    scenario_project_finish = (
        scenario["Scenario Finish"].max()
    )

    if (
        pd.notna(baseline_project_finish)
        and pd.notna(scenario_project_finish)
    ):

        project_finish_change = (
            scenario_project_finish
            - baseline_project_finish
        ).days

    else:

        project_finish_change = 0

    # Positive recovery means the hypothetical
    # project finish is earlier than baseline.
    recovery_achieved = max(
        0,
        -project_finish_change,
    )

    # -------------------------------------------------
    # Project-level scenario fields
    # -------------------------------------------------

    scenario["Baseline Project Finish"] = (
        baseline_project_finish
    )

    scenario["Scenario Project Finish"] = (
        scenario_project_finish
    )

    scenario["Project Finish Change"] = (
        project_finish_change
    )

    scenario["Recovery Achieved"] = (
        recovery_achieved
    )

    # -------------------------------------------------
    # Current project progress
    # -------------------------------------------------

    progress_columns = [
        "ID",
        "Actual Start",
        "Actual Finish",
        "% Complete",
        "Schedule Variance",
        "Progress Status",
    ]

    available_progress_columns = [
        column
        for column in progress_columns
        if column in progress.columns
    ]

    progress_subset = progress[
        available_progress_columns
    ].copy()

    scenario = scenario.merge(
        progress_subset,
        on="ID",
        how="left",
        suffixes=("", "_Current"),
    )

    # -------------------------------------------------
    # Final scenario metadata
    # -------------------------------------------------

    scenario["Recovery Scenario"] = True

    scenario["Recovery Target Activity"] = str(
        activity_id
    )

    scenario["Affected by Recovery"] = (
        scenario["ID"]
        .astype(str)
        .isin(affected_activities)
    )

    return scenario, None



def render_recovery_scenario_gantt(
    scenario,
    activity_id,
):
    """
    Display the recovery scenario using the same visual
    formatting and timeline language as the project Gantt.
    """

    if scenario is None or scenario.empty:
        return

    gantt_scale = st.selectbox(
        "Time Scale",
        [
            "Days",
            "Weeks",
            "Months",
            "Quarters"
        ],
        key="recovery_scenario_gantt_scale"
    )

    highlight_critical = st.checkbox(
        "Highlight critical activities",
        value=True,
        key="recovery_scenario_critical",
    )

    gantt_data = scenario.copy()

    gantt_data["Scenario Start"] = pd.to_datetime(
        gantt_data["Scenario Start"],
        errors="coerce"
    )

    gantt_data["Scenario Finish"] = pd.to_datetime(
        gantt_data["Scenario Finish"],
        errors="coerce"
    )

    gantt_data["Critical"] = (
        gantt_data["Critical"]
        .fillna(False)
        .astype(bool)
    )

    gantt_data = gantt_data[
        gantt_data["Scenario Start"].notna()
        & gantt_data["Scenario Finish"].notna()
    ].copy()

    if gantt_data.empty:
        st.warning(
            "No calculated scenario dates are available "
            "for the Gantt chart."
        )
        return

    gantt_data = gantt_data.reset_index(drop=True)

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
    # CREATE GANTT
    # --------------------------------------------------

    fig = go.Figure()

    for position, activity in gantt_data.iterrows():

        start = activity["Scenario Start"]

        finish = activity["Scenario Finish"]

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

        activity_id_value = str(
            activity.get(
                "ID",
                ""
            )
        )

        activity_name = str(
            activity.get(
                "Activity",
                activity_id_value
            )
        )

        is_selected = (
            activity_id_value
            == str(activity_id)
        )

        is_critical = bool(
            activity["Critical"]
        )

        # Selected recovery activity = blue
        if is_selected:

            bar_color = "#2980b9"

        # Critical activities = red
        elif (
            highlight_critical
            and is_critical
        ):

            bar_color = "#c0392b"

        # All other activities = neutral
        else:

            bar_color = "#9aa0a6"

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
                    + activity_id_value
                    + "<br>"
                    "Scenario Start: "
                    + start.strftime(
                        "%d %b %Y"
                    )
                    + "<br>"
                    "Scenario Finish: "
                    + finish.strftime(
                        "%d %b %Y"
                    )
                    + "<br>"
                    "Baseline Finish: "
                    + pd.to_datetime(
                        activity["Planned Finish"]
                    ).strftime(
                        "%d %b %Y"
                    )
                    + "<br>"
                    "Duration: "
                    + str(duration_days)
                    + " days"
                    + "<br>"
                    "Scenario Change: "
                    + str(
                        int(
                            activity[
                                "Scenario Change"
                            ]
                        )
                    )
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
    # TODAY LINE
    # --------------------------------------------------

    today = pd.Timestamp.today().normalize()

    fig.add_vline(
        x=today,
        line_width=3,
        line_dash="solid",
        line_color="#f1c40f",
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
        "Selected recovery activity is shown in blue. "
        "Critical activities are shown in red when "
        "Highlight Critical Activities is enabled. "
        "All other activities remain neutral. "
        "Yellow line = today."
    )



def render_recovery_scenario(
    lookahead_data,
    progress_data,
):
    """
    Planner-facing recovery scenario interface.

    This is read-only and never modifies the approved baseline.
    """

    st.subheader(
        "Recovery Scenario"
    )

    st.write(
        "Create a hypothetical recovery scenario and "
        "evaluate its calculated schedule impact. "
        "The approved baseline remains unchanged."
    )

    baseline = st.session_state.get(
        "baseline_schedule"
    )

    if (
        baseline is None
        or baseline.empty
    ):

        st.warning(
            "Approved baseline schedule is unavailable."
        )

        return

    scenario_candidates = baseline[
        baseline["ID"]
        .astype(str)
        .isin(
            lookahead_data["ID"]
            .astype(str)
        )
    ].copy()

    if scenario_candidates.empty:

        st.info(
            "No delayed or critical activities are "
            "currently available for recovery analysis."
        )

        return

    scenario_candidates = (
        scenario_candidates.sort_values(
            by="ID"
        )
    )

    activity_options = (
        scenario_candidates[
            "ID"
        ]
        .astype(str)
        .tolist()
    )

    selected_activity_id = st.selectbox(
        "Recovery Activity",
        activity_options,
        key="recovery_scenario_activity_selector",
    )

    selected_row = scenario_candidates[
        scenario_candidates["ID"]
        .astype(str)
        == selected_activity_id
    ].iloc[0]

    st.caption(
        f"Selected Activity: "
        f"{selected_row['Activity']}"
    )

    baseline_finish = pd.to_datetime(
        selected_row["Planned Finish"],
        errors="coerce",
    )

    if pd.isna(baseline_finish):

        st.error(
            "The selected activity does not have "
            "a valid baseline finish date."
        )

        return

    target_finish = st.date_input(
        "Proposed Recovery Finish Date",
        value=baseline_finish.date(),
        key="recovery_scenario_target_finish",
    )

    if target_finish > baseline_finish.date():

        st.warning(
            "The proposed finish is later than the "
            "approved baseline finish. This is a "
            "recovery scenario only and may represent "
            "additional delay rather than recovery."
        )

    if st.button(
        "Calculate Recovery Scenario",
        type="primary",
        use_container_width=True,
        key="calculate_recovery_scenario",
    ):

        scenario, error = (
            calculate_recovery_scenario(
                baseline,
                progress_data,
                selected_activity_id,
                target_finish,
            )
        )

        if error:

            st.error(error)

        else:

            st.session_state.recovery_scenario = (
                scenario
            )

            st.session_state.recovery_scenario_selected_activity = (
                selected_activity_id
            )

            st.success(
                "Recovery scenario calculated. "
                "The approved baseline has not been changed."
            )

    scenario = st.session_state.get(
        "recovery_scenario"
    )

    scenario_activity = st.session_state.get(
        "recovery_scenario_selected_activity"
    )

    if (
        scenario is None
        or scenario.empty
        or scenario_activity is None
    ):
        return

    st.divider()

    st.subheader(
        "Scenario Result"
    )

    selected_scenario = scenario[
        scenario["ID"]
        .astype(str)
        == str(scenario_activity)
    ]

    if not selected_scenario.empty:

        selected_scenario = (
            selected_scenario.iloc[0]
        )

        baseline_finish = pd.to_datetime(
            selected_scenario[
                "Planned Finish"
            ],
            errors="coerce",
        )

        scenario_finish = pd.to_datetime(
            selected_scenario[
                "Scenario Finish"
            ],
            errors="coerce",
        )

        scenario_change = int(
            selected_scenario[
                "Scenario Change"
            ]
        )

        baseline_project_finish = pd.to_datetime(
            selected_scenario[
                "Baseline Project Finish"
            ],
            errors="coerce",
        )

        scenario_project_finish = pd.to_datetime(
            selected_scenario[
                "Scenario Project Finish"
            ],
            errors="coerce",
        )

        project_finish_change = int(
            selected_scenario[
                "Project Finish Change"
            ]
        )

        recovery_achieved = int(
            selected_scenario[
                "Recovery Achieved"
            ]
        )

        affected_count = int(
            scenario[
                "Affected by Recovery"
            ].sum()
        )

        moved_earlier_count = int(
            (
                scenario[
                    "Scenario Status"
                ]
                == "Moved Earlier"
            ).sum()
        )

        moved_later_count = int(
            (
                scenario[
                    "Scenario Status"
                ]
                == "Moved Later"
            ).sum()
        )

        unchanged_count = int(
            (
                scenario[
                    "Scenario Status"
                ]
                == "Unchanged"
            ).sum()
        )

        metric1, metric2, metric3, metric4 = (
            st.columns(4)
        )

        with metric1:

            st.metric(
                "Baseline Project Finish",
                (
                    baseline_project_finish.strftime(
                        "%d %b %y"
                    )
                    if pd.notna(
                        baseline_project_finish
                    )
                    else "—"
                ),
            )

        with metric2:

            st.metric(
                "Scenario Project Finish",
                (
                    scenario_project_finish.strftime(
                        "%d %b %y"
                    )
                    if pd.notna(
                        scenario_project_finish
                    )
                    else "—"
                ),
            )

        with metric3:

            if project_finish_change < 0:

                st.metric(
                    "Project Recovery",
                    f"{recovery_achieved} days",
                    delta=f"{project_finish_change} days",
                )

            elif project_finish_change > 0:

                st.metric(
                    "Project Impact",
                    f"+{project_finish_change} days",
                    delta=f"+{project_finish_change} days",
                )

            else:

                st.metric(
                    "Project Impact",
                    "No change",
                )

        with metric4:

            st.metric(
                "Affected Activities",
                affected_count,
            )

        st.caption(
            f"{moved_earlier_count} moved earlier • "
            f"{moved_later_count} moved later • "
            f"{unchanged_count} unchanged"
        )

    st.caption(
        "Blue = selected recovery activity | "
        "Red = critical | Grey = other baseline activities | "
        "Yellow line = today"
    )

    render_recovery_scenario_gantt(
        scenario,
        scenario_activity,
    )

    st.subheader(
        "Scenario Schedule Impact"
    )

    # -------------------------------------------------
    # Recovery Scenario Impact Table
    # -------------------------------------------------

    impact_columns = [
        "ID",
        "Activity",
        "Planned Start",
        "Scenario Start",
        "Planned Finish",
        "Scenario Finish",
        "Scenario Start Change",
        "Scenario Change",
        "Scenario Status",
        "Affected by Recovery",
    ]

    available_impact_columns = [
        column
        for column in impact_columns
        if column in scenario.columns
    ]

    impact_table = scenario[
        available_impact_columns
    ].copy()

    # ---------------------------------------------
    # Format dates
    # ---------------------------------------------

    for column in [
        "Planned Start",
        "Scenario Start",
        "Planned Finish",
        "Scenario Finish",
    ]:

        if column in impact_table.columns:

            impact_table[column] = (
                pd.to_datetime(
                    impact_table[column],
                    errors="coerce",
                ).dt.strftime(
                    "%d %b %y"
                )
            )

    # ---------------------------------------------
    # Make affected status readable
    # ---------------------------------------------

    if "Affected by Recovery" in impact_table.columns:

        impact_table[
            "Affected by Recovery"
        ] = impact_table[
            "Affected by Recovery"
        ].map(
            {
                True: "Yes",
                False: "No",
            }
        )

    # ---------------------------------------------
    # Rename columns for user-facing table
    # ---------------------------------------------

    impact_table = impact_table.rename(
        columns={
            "Scenario Start Change":
                "Start Change (days)",

            "Scenario Change":
                "Finish Change (days)",

            "Affected by Recovery":
                "Affected",
        }
    )

    st.dataframe(
        impact_table,
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "This is a hypothetical scenario only. "
        "It does not modify or replace the approved baseline. "
        "Positive change means later than baseline; "
        "negative change means earlier."
    )

    # -------------------------------------------------
    # Reset Recovery Scenario
    # -------------------------------------------------

    st.divider()

    if st.button(
        "Reset Recovery Scenario",
        use_container_width=True,
        key="reset_recovery_scenario",
    ):

        st.session_state.pop(
            "recovery_scenario",
            None,
        )

        st.session_state.pop(
            "recovery_scenario_selected_activity",
            None,
        )

        st.session_state.pop(
            "recovery_scenario_target_finish",
            None,
        )

        st.rerun()


#cc
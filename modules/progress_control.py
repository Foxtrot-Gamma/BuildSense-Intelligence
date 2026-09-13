import pandas as pd
import streamlit as st
import plotly.graph_objects as go


def initialize_progress_data(baseline_schedule):
    """
    Create a working progress dataset from the approved baseline.

    The approved baseline is copied and never modified.
    """

    if baseline_schedule is None:
        return None

    if baseline_schedule.empty:
        return None

    progress = baseline_schedule.copy()

    # Add progress-control columns if they do not already exist
    if "Actual Start" not in progress.columns:
        progress["Actual Start"] = pd.NaT

    if "Actual Finish" not in progress.columns:
        progress["Actual Finish"] = pd.NaT

    if "Progress Update Date" not in progress.columns:
        progress["Progress Update Date"] = pd.NaT

    if "% Complete" not in progress.columns:
        progress["% Complete"] = 0.0

    if "Planned %" not in progress.columns:
        progress["Planned %"] = 0.0

    if "Status" not in progress.columns:
        progress["Status"] = "Not Started"

    if "Schedule Variance" not in progress.columns:
        progress["Schedule Variance"] = 0

    if "Schedule Impact" not in progress.columns:
        progress["Schedule Impact"] = "On Track"

    if "Lag" not in progress.columns:
        progress["Lag"] = None

    if "Progress Status" not in progress.columns:
        progress["Progress Status"] = "Not Started"

    # Standardize all date columns as Pandas timestamps
    progress["Planned Start"] = pd.to_datetime(
        progress["Planned Start"],
        errors="coerce"
    )

    progress["Planned Finish"] = pd.to_datetime(
        progress["Planned Finish"],
        errors="coerce"
    )

    progress["Actual Start"] = pd.to_datetime(
        progress["Actual Start"],
        errors="coerce"
    )

    progress["Actual Finish"] = pd.to_datetime(
        progress["Actual Finish"],
        errors="coerce"
    )

    progress["Progress Update Date"] = pd.to_datetime(
        progress["Progress Update Date"],
        errors="coerce"
    )

    # Ensure percentage is numeric and within 0–100
    progress["% Complete"] = pd.to_numeric(
        progress["% Complete"],
        errors="coerce"
    ).fillna(0.0)

    progress["% Complete"] = progress["% Complete"].clip(
        lower=0,
        upper=100
    )

    # Calculate planned progress as of today
    progress["Planned %"] = progress.apply(
        _calculate_planned_progress,
        axis=1
    )

    # Calculate status
    progress["Status"] = progress.apply(
        _calculate_status,
        axis=1
    )

    # Calculate lag
    progress["Lag"] = progress.apply(
    _calculate_lag,
    axis=1
    )

    # Calculate schedule variance
    progress["Schedule Variance"] = progress.apply(
        _calculate_schedule_variance,
        axis=1
    )

    progress["Schedule Impact"] = progress.apply(
        _calculate_schedule_impact,
        axis=1
    )

    # Calculate overall progress status
    progress["Progress Status"] = progress.apply(
        _calculate_progress_status,
        axis=1
    )

    return progress


def _calculate_status(row):
    """
    Determine basic activity execution status.
    """

    percent_complete = row["% Complete"]
    actual_start = row["Actual Start"]
    actual_finish = row["Actual Finish"]

    if percent_complete >= 100:
        return "Completed"

    if pd.notna(actual_finish):
        return "Completed"

    if percent_complete > 0:
        return "In Progress"

    if pd.notna(actual_start):
        return "In Progress"

    return "Not Started"


def _calculate_lag(row):
    """
    Calculate start-date lag in calendar days.

    Positive value = started late
    Negative value = started early
    Zero = started on planned date
    Blank = activity has not started
    """

    planned_start = row["Planned Start"]
    actual_start = row["Actual Start"]

    if pd.isna(planned_start) or pd.isna(actual_start):
        return None

    return (
        actual_start - planned_start
    ).days


def _calculate_schedule_variance(row):
    """
    Calculate schedule variance in calendar days.

    Positive value = late
    Negative value = early
    Zero = on time / not yet due
    """

    planned_finish = pd.to_datetime(
        row["Planned Finish"],
        errors="coerce"
    )


    actual_finish = pd.to_datetime(
        row["Actual Finish"],
        errors="coerce"
    )

    if pd.isna(planned_finish):
        return 0

    # Completed activity:
    # compare actual finish against planned finish.
    if pd.notna(actual_finish):

        return (
            actual_finish.normalize()
            - planned_finish.normalize()
        ).days

    # Activity not yet completed:
    # compare today's date against planned finish.
    today = pd.Timestamp.today().normalize()

    if today > planned_finish.normalize():

        return (
            today
            - planned_finish.normalize()
        ).days

    return 0

def _calculate_schedule_impact(row):
    """
    Determine whether schedule variance has consumed
    or exceeded the available CPM total float.
    """

    schedule_variance = row["Schedule Variance"]
    total_float = row.get("Total Float", 0)

    if pd.isna(schedule_variance):
        return "No Schedule"

    if pd.isna(total_float):
        total_float = 0

    schedule_variance = float(schedule_variance)
    total_float = float(total_float)

    if schedule_variance <= 0:
        return "On Track"

    if schedule_variance <= total_float:
        return "No Impact"

    return "Project Delay"


def _calculate_progress_status(row):
    """
    Compare activity progress against its planned schedule.
    """

    percent_complete = row["% Complete"]
    planned_start = row["Planned Start"]
    planned_finish = row["Planned Finish"]

    today = pd.Timestamp.today().normalize()

    if percent_complete >= 100:
        return "Completed"

    if pd.isna(planned_start) or pd.isna(planned_finish):
        return "No Schedule"

    if today < planned_start:
        return "Not Due"

    # Use the same Pandas Timestamp type as the schedule dates.
    today = pd.Timestamp.today().normalize()

    total_days = (
        planned_finish - planned_start
    ).days + 1

    if total_days <= 0:
        return "No Schedule"

    elapsed_days = (
        today - planned_start
    ).days + 1

    elapsed_days = max(
        0,
        min(elapsed_days, total_days)
    )

    planned_progress = (
        elapsed_days / total_days
    ) * 100

    # Allow a 5 percentage-point tolerance.
    if percent_complete >= planned_progress + 5:
        return "Ahead"

    if percent_complete <= planned_progress - 5:
        return "Behind"

    return "On Track"

def _calculate_planned_progress(row):
    """
    Calculate planned activity progress as of today.
    """

    planned_start = row["Planned Start"]
    planned_finish = row["Planned Finish"]

    if pd.isna(planned_start) or pd.isna(planned_finish):
        return 0.0

    today = pd.Timestamp.today().normalize()

    total_days = (
        planned_finish - planned_start
    ).days + 1

    if total_days <= 0:
        return 0.0

    if today < planned_start:
        return 0.0

    if today >= planned_finish:
        return 100.0

    elapsed_days = (
        today - planned_start
    ).days + 1

    planned_progress = (
        elapsed_days / total_days
    ) * 100

    return round(
        planned_progress,
        1
    )

def _update_progress_data():
    """
    Apply edits made in the progress data editor
    directly to the stored progress dataset.
    """

    editor_key = (
        f"progress_editor_"
        f"{st.session_state.get('progress_editor_version', 0)}"
    )

    editor_state = st.session_state.get(editor_key)

    if not editor_state:
        return

    progress_data = st.session_state.get("progress_data")

    if progress_data is None:
        return

    edited_rows = editor_state.get("edited_rows", {})

    if not edited_rows:
        return

    # Apply each edited row to the main progress dataset
    for row_index, changes in edited_rows.items():

        if row_index not in progress_data.index:
            continue

        for column, value in changes.items():

            if column == "% Complete":

                value = pd.to_numeric(
                    value,
                    errors="coerce"
                )

                if pd.isna(value):
                    value = 0.0

                value = max(
                    0,
                    min(100, float(value))
                )

                progress_data.loc[
                    row_index,
                    "% Complete"
                ] = value

            elif column == "Actual Start":

                progress_data.loc[
                    row_index,
                    "Actual Start"
                ] = pd.to_datetime(
                    value,
                    errors="coerce"
                )

            elif column == "Actual Finish":

                progress_data.loc[
                    row_index,
                    "Actual Finish"
                ] = pd.to_datetime(
                    value,
                    errors="coerce"
                )

            elif column == "Progress Update Date":

                progress_data.loc[
                    row_index,
                    "Progress Update Date"
                ] = pd.to_datetime(
                    value,
                    errors="coerce"
                )
                

    # Recalculate all dependent fields
    progress_data["Lag"] = progress_data.apply(
        _calculate_lag,
        axis=1
    )
    
    
    progress_data["Status"] = progress_data.apply(
        _calculate_status,
        axis=1
    )

    progress_data["Schedule Variance"] = progress_data.apply(
        _calculate_schedule_variance,
        axis=1
    )

    progress_data["Schedule Impact"] = progress_data.apply(
        _calculate_schedule_impact,
        axis=1
    )

    progress_data["Progress Status"] = progress_data.apply(
        _calculate_progress_status,
        axis=1
    )

    st.session_state.progress_data = progress_data


def render_progress_gantt(progress_data):
    """
    Display the project progress Gantt chart in a dialog.

    Planned duration is shown as the baseline.
    Actual progress is shown as a percentage of
    the planned activity duration.

    Start lag is shown by beginning the progress bar
    from the actual start date.

    Schedule overrun is shown as a patterned extension
    beyond the planned finish.
    """

    if progress_data is None or progress_data.empty:

        st.warning(
            "No project progress data is available "
            "for the Gantt chart."
        )

        return

    gantt_data = progress_data.copy()

    # --------------------------------------------------
    # STANDARDIZE DATA
    # --------------------------------------------------

    gantt_data["Planned Start"] = pd.to_datetime(
        gantt_data["Planned Start"],
        errors="coerce"
    )

    gantt_data["Planned Finish"] = pd.to_datetime(
        gantt_data["Planned Finish"],
        errors="coerce"
    )

    gantt_data["Actual Start"] = pd.to_datetime(
        gantt_data.get(
            "Actual Start",
            pd.NaT
        ),
        errors="coerce"
    )

    gantt_data["Actual Finish"] = pd.to_datetime(
        gantt_data.get(
            "Actual Finish",
            pd.NaT
        ),
        errors="coerce"
    )

    gantt_data["% Complete"] = pd.to_numeric(
        gantt_data["% Complete"],
        errors="coerce"
    ).fillna(0).clip(
        lower=0,
        upper=100
    )

    gantt_data["Schedule Variance"] = pd.to_numeric(
        gantt_data.get(
            "Schedule Variance",
            0
        ),
        errors="coerce"
    ).fillna(0)

    gantt_data = gantt_data[
        gantt_data["Planned Start"].notna()
        & gantt_data["Planned Finish"].notna()
    ].copy()

    if gantt_data.empty:

        st.warning(
            "No valid planned dates are available "
            "for the Progress Gantt."
        )

        return

    gantt_data = gantt_data.reset_index(
        drop=False
    )

    # --------------------------------------------------
    # CRITICAL HIGHLIGHT SETTING
    # --------------------------------------------------

    highlight_critical = st.session_state.get(
        "highlight_critical_progress",
        False
    )

    # --------------------------------------------------
    # TIME SCALE
    # --------------------------------------------------

    gantt_scale = st.selectbox(
        "Time Scale",
        [
            "Days",
            "Weeks",
            "Months",
            "Quarters"
        ],
        key="progress_gantt_scale"
    )

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
    # CREATE FIGURE
    # --------------------------------------------------

    fig = go.Figure()

    for position, activity in gantt_data.iterrows():

        start = activity["Planned Start"]

        finish = activity["Planned Finish"]

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

        percent_complete = float(
            activity["% Complete"]
        )

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
        # CRITICAL STATUS
        # --------------------------------------------------

        critical_value = activity.get(
            "Critical",
            False
        )

        is_critical = (
            str(critical_value).strip().lower()
            in [
                "yes",
                "true",
                "1"
            ]
            or critical_value is True
        )

        # --------------------------------------------------
        # PLANNED BASELINE BAR
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
                    "ID: "
                    + activity_id
                    + "<br>"
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
                    "Planned Duration: "
                    + str(duration_days)
                    + " days"
                    + "<br>"
                    "Progress: "
                    + f"{percent_complete:.0f}%"
                    + "<extra></extra>"
                ),

                showlegend=False
            )
        )

        # --------------------------------------------------
        # ACTUAL PROGRESS
        # --------------------------------------------------

        if percent_complete > 0:

            actual_start = activity[
                "Actual Start"
            ]

            if pd.isna(actual_start):

                progress_start = start

            else:

                progress_start = actual_start

            progress_duration_ms = (
                duration_ms
                * percent_complete
                / 100
            )

            fig.add_trace(
                go.Bar(
                    x=[progress_duration_ms],
                    y=[position],
                    base=[progress_start],
                    orientation="h",

                    marker=dict(
                        color="#27ae60"
                    ),

                    hovertemplate=(
                        "<b>"
                        + activity_name
                        + "</b><br>"
                        "Actual Start: "
                        + (
                            progress_start.strftime(
                                "%d %b %Y"
                            )
                        )
                        + "<br>"
                        "Actual Progress: "
                        + f"{percent_complete:.0f}%"
                        + "<extra></extra>"
                    ),

                    showlegend=False
                )
            )

        # --------------------------------------------------
        # SCHEDULE OVERRUN
        # --------------------------------------------------

        schedule_variance = max(
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

        if schedule_variance > 0:

            overrun_start = (
                finish
                + pd.Timedelta(days=1)
            )

            overrun_duration_ms = (
                schedule_variance
                * 24
                * 60
                * 60
                * 1000
            )

            if (
                highlight_critical
                and is_critical
            ):

                pattern_color = "#c0392b"

            else:

                pattern_color = "#7f8c8d"

            fig.add_trace(
                go.Bar(
                    x=[overrun_duration_ms],
                    y=[position],
                    base=[overrun_start],
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
                        + str(schedule_variance)
                        + " days"
                        + "<extra></extra>"
                    ),

                    showlegend=False
                )
            )

    # --------------------------------------------------
    # LAYOUT
    # --------------------------------------------------

        # --------------------------------------------------
    # TODAY INDICATOR
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
            500,
            len(gantt_data) * 42
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
        "Grey bars represent the approved baseline. "
        "Green bars represent recorded progress. "
        "Patterned extensions represent schedule overrun."
    )


#cc
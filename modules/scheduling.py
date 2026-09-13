
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import format_date
from modules.ai_assistant import render_ai_relationship_analysis


# ==========================================================
# RELATIONSHIP OPTIONS
# ==========================================================

RELATIONSHIP_OPTIONS = [
    "No Predecessor",
    "Finish-to-Start (FS)",
    "Start-to-Start (SS)",
    "Finish-to-Finish (FF)",
    "Start-to-Finish (SF)"
]


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def activity_lookup(activities):
    """
    Create a dictionary using Activity ID as the key.
    """

    lookup = {}

    for _, row in activities.iterrows():

        activity_id = str(row["ID"]).strip()

        lookup[activity_id] = row

    return lookup


def detect_cycles(activities):
    """
    Detect circular predecessor relationships.
    """

    graph = {}

    for _, row in activities.iterrows():

        activity_id = str(row["ID"]).strip()
        predecessor = str(row["Predecessor"]).strip()

        if predecessor:
            graph[activity_id] = predecessor
        else:
            graph[activity_id] = None

    visited = set()
    recursion_stack = set()
    cycles = []

    def visit(node, path):

        if node in recursion_stack:

            cycle_start = path.index(node)

            cycles.append(
                path[cycle_start:] + [node]
            )

            return True

        if node in visited:
            return False

        visited.add(node)
        recursion_stack.add(node)

        predecessor = graph.get(node)

        if predecessor and predecessor in graph:

            visit(
                predecessor,
                path + [predecessor]
            )

        recursion_stack.remove(node)

        return False

    for node in graph:

        if node not in visited:
            visit(node, [node])

    return cycles


def calculate_activity_dates(
    relationship,
    predecessor_start,
    predecessor_finish,
    duration,
    project_start
):
    """
    Calculate activity start and finish dates
    according to the relationship.
    """

    duration = max(int(duration), 1)

    if relationship == "Finish-to-Start (FS)":

        start_date = (
            predecessor_finish + timedelta(days=1)
        )

        finish_date = (
            start_date
            + timedelta(days=duration - 1)
        )

    elif relationship == "Start-to-Start (SS)":

        start_date = predecessor_start

        finish_date = (
            start_date
            + timedelta(days=duration - 1)
        )

    elif relationship == "Finish-to-Finish (FF)":

        finish_date = predecessor_finish

        start_date = (
            finish_date
            - timedelta(days=duration - 1)
        )

    elif relationship == "Start-to-Finish (SF)":

        finish_date = predecessor_start

        start_date = (
            finish_date
            - timedelta(days=duration - 1)
        )

    else:

        start_date = project_start

        finish_date = (
            start_date
            + timedelta(days=duration - 1)
        )

    return start_date, finish_date


def calculate_schedule(activities, project_start):
    """
    Calculate the complete project schedule and CPM metrics.

    Calculates:
        - Planned Start
        - Planned Finish
        - Early Start
        - Early Finish
        - Late Start
        - Late Finish
        - Total Float
        - Critical

    Activity IDs are used internally for relationships.
    """

    activities = activities.copy()

    lookup = activity_lookup(activities)

    calculated = {}

    unresolved = set(
        activities["ID"]
        .astype(str)
        .tolist()
    )

    warnings = []

    # ======================================================
    # FORWARD PASS
    # ======================================================

    max_iterations = max(
        len(unresolved) * 3,
        10
    )

    iteration = 0

    while unresolved and iteration < max_iterations:

        iteration += 1

        progress_made = False

        for activity_id in list(unresolved):

            row = lookup[activity_id]

            predecessor = str(
                row["Predecessor"]
            ).strip()

            relationship = str(
                row["Relationship"]
            ).strip()

            duration = row["Duration"]

            # --------------------------------------------------
            # VALIDATE DURATION
            # --------------------------------------------------

            try:

                duration = int(
                    float(duration)
                )

            except Exception:

                duration = 1

                warnings.append(
                    f"{activity_id}: Invalid duration. "
                    "Temporary 1-day duration used."
                )

            if duration <= 0:

                duration = 1

                warnings.append(
                    f"{activity_id}: Duration must be greater than zero."
                )

            # --------------------------------------------------
            # NO PREDECESSOR
            # --------------------------------------------------

            if (
                not predecessor
                or predecessor.lower()
                in ["none", "none 🔍"]
            ):

                start_date = project_start

                finish_date = (
                    start_date
                    + timedelta(days=duration - 1)
                )

                calculated[activity_id] = {
                    "Start": start_date,
                    "Finish": finish_date,
                    "Duration": duration
                }

                unresolved.remove(activity_id)

                progress_made = True

                continue

            # --------------------------------------------------
            # INVALID PREDECESSOR
            # --------------------------------------------------

            if predecessor not in lookup:

                warnings.append(
                    f"{activity_id}: Predecessor "
                    f"'{predecessor}' does not exist."
                )

                continue

            # --------------------------------------------------
            # PREDECESSOR NOT YET CALCULATED
            # --------------------------------------------------

            if predecessor not in calculated:

                continue

            predecessor_start = calculated[
                predecessor
            ]["Start"]

            predecessor_finish = calculated[
                predecessor
            ]["Finish"]

            # --------------------------------------------------
            # CALCULATE ACTIVITY DATES
            # --------------------------------------------------

            start_date, finish_date = (
                calculate_activity_dates(
                    relationship,
                    predecessor_start,
                    predecessor_finish,
                    duration,
                    project_start
                )
            )

            calculated[activity_id] = {
                "Start": start_date,
                "Finish": finish_date,
                "Duration": duration
            }

            unresolved.remove(activity_id)

            progress_made = True

        if not progress_made:
            break

    # ======================================================
    # UNRESOLVED ACTIVITIES
    # ======================================================

    if unresolved:

        for activity_id in unresolved:

            warnings.append(
                f"{activity_id}: Schedule could not be calculated. "
                "Check predecessor relationships or circular dependencies."
            )

    # ======================================================
    # BUILD INITIAL RESULT
    # ======================================================

    result = activities.copy()

    result["Planned Start"] = None
    result["Planned Finish"] = None

    result["Early Start"] = None
    result["Early Finish"] = None
    result["Late Start"] = None
    result["Late Finish"] = None

    result["Total Float"] = None
    result["Critical"] = False

    for index, row in result.iterrows():

        activity_id = str(
            row["ID"]
        ).strip()

        if activity_id in calculated:

            start_date = calculated[
                activity_id
            ]["Start"]

            finish_date = calculated[
                activity_id
            ]["Finish"]

            result.at[
                index,
                "Planned Start"
            ] = start_date

            result.at[
                index,
                "Planned Finish"
            ] = finish_date

            result.at[
                index,
                "Early Start"
            ] = start_date

            result.at[
                index,
                "Early Finish"
            ] = finish_date

    # ======================================================
    # CPM BACKWARD PASS
    # ======================================================

    valid_activities = [
        activity_id
        for activity_id in calculated
        if calculated[activity_id]["Start"] is not None
        and calculated[activity_id]["Finish"] is not None
    ]

    if valid_activities:

        # --------------------------------------------------
        # PROJECT FINISH
        # --------------------------------------------------

        project_finish = max(
            calculated[activity_id]["Finish"]
            for activity_id in valid_activities
        )

        # --------------------------------------------------
        # CREATE SUCCESSOR MAP
        # --------------------------------------------------

        successors = {
            activity_id: []
            for activity_id in valid_activities
        }

        for activity_id in valid_activities:

            row = lookup[activity_id]

            predecessor = str(
                row["Predecessor"]
            ).strip()

            relationship = str(
                row["Relationship"]
            ).strip()

            if (
                predecessor
                and predecessor.lower()
                not in ["none", "none 🔍"]
                and predecessor in successors
            ):

                successors[
                    predecessor
                ].append(
                    {
                        "id": activity_id,
                        "relationship": relationship
                    }
                )

        # --------------------------------------------------
        # INITIAL LATE DATES
        # --------------------------------------------------

        cpm = {}

        for activity_id in valid_activities:

            duration = calculated[
                activity_id
            ]["Duration"]

            late_finish = project_finish

            late_start = (
                late_finish
                - timedelta(days=duration - 1)
            )

            cpm[activity_id] = {
                "Late Start": late_start,
                "Late Finish": late_finish
            }

        # --------------------------------------------------
        # BACKWARD PASS
        #
        # Repeated relaxation is used rather than relying
        # on row order. This keeps the engine robust when
        # activities are entered in a non-sequential order.
        # --------------------------------------------------

        reverse_iterations = max(
            len(valid_activities) * 3,
            10
        )

        for _ in range(reverse_iterations):

            changed = False

            for activity_id in reversed(
                valid_activities
            ):

                activity_duration = calculated[
                    activity_id
                ]["Duration"]

                current_late_start = cpm[
                    activity_id
                ]["Late Start"]

                current_late_finish = cpm[
                    activity_id
                ]["Late Finish"]

                new_late_start = current_late_start
                new_late_finish = current_late_finish

                activity_successors = successors.get(
                    activity_id,
                    []
                )

                # --------------------------------------------------
                # ACTIVITIES WITHOUT SUCCESSORS
                # --------------------------------------------------

                if not activity_successors:

                    new_late_finish = project_finish

                    new_late_start = (
                        new_late_finish
                        - timedelta(
                            days=activity_duration - 1
                        )
                    )

                else:

                    # --------------------------------------------------
                    # APPLY SUCCESSOR CONSTRAINTS
                    # --------------------------------------------------

                    for successor in activity_successors:

                        successor_id = successor["id"]
                        relationship = successor["relationship"]

                        successor_late_start = cpm[
                            successor_id
                        ]["Late Start"]

                        successor_late_finish = cpm[
                            successor_id
                        ]["Late Finish"]

                        successor_duration = calculated[
                            successor_id
                        ]["Duration"]

                        # ----------------------------------------------
                        # FINISH-TO-START
                        #
                        # Pred Finish <= Succ Start - 1
                        # ----------------------------------------------

                        if relationship == (
                            "Finish-to-Start (FS)"
                        ):

                            candidate_late_finish = (
                                successor_late_start
                                - timedelta(days=1)
                            )

                            candidate_late_start = (
                                candidate_late_finish
                                - timedelta(
                                    days=activity_duration - 1
                                )
                            )

                        # ----------------------------------------------
                        # START-TO-START
                        #
                        # Pred Start <= Succ Start
                        # ----------------------------------------------

                        elif relationship == (
                            "Start-to-Start (SS)"
                        ):

                            candidate_late_start = (
                                successor_late_start
                            )

                            candidate_late_finish = (
                                candidate_late_start
                                + timedelta(
                                    days=activity_duration - 1
                                )
                            )

                        # ----------------------------------------------
                        # FINISH-TO-FINISH
                        #
                        # Pred Finish <= Succ Finish
                        # ----------------------------------------------

                        elif relationship == (
                            "Finish-to-Finish (FF)"
                        ):

                            candidate_late_finish = (
                                successor_late_finish
                            )

                            candidate_late_start = (
                                candidate_late_finish
                                - timedelta(
                                    days=activity_duration - 1
                                )
                            )

                        # ----------------------------------------------
                        # START-TO-FINISH
                        #
                        # Pred Start <= Succ Finish
                        # ----------------------------------------------

                        elif relationship == (
                            "Start-to-Finish (SF)"
                        ):

                            candidate_late_start = (
                                successor_late_finish
                            )

                            candidate_late_finish = (
                                candidate_late_start
                                + timedelta(
                                    days=activity_duration - 1
                                )
                            )

                        else:

                            continue

                        # ----------------------------------------------
                        # TAKE THE MOST RESTRICTIVE VALUE
                        # ----------------------------------------------

                        if (
                            candidate_late_start
                            < new_late_start
                        ):

                            new_late_start = (
                                candidate_late_start
                            )

                        if (
                            candidate_late_finish
                            < new_late_finish
                        ):

                            new_late_finish = (
                                candidate_late_finish
                            )

                # --------------------------------------------------
                # SAVE IF CHANGED
                # --------------------------------------------------

                if (
                    new_late_start
                    != current_late_start
                    or
                    new_late_finish
                    != current_late_finish
                ):

                    cpm[activity_id][
                        "Late Start"
                    ] = new_late_start

                    cpm[activity_id][
                        "Late Finish"
                    ] = new_late_finish

                    changed = True

            if not changed:
                break

        # ==================================================
        # CALCULATE FLOAT + CRITICAL STATUS
        # ==================================================

        for index, row in result.iterrows():

            activity_id = str(
                row["ID"]
            ).strip()

            if activity_id not in cpm:
                continue

            early_start = calculated[
                activity_id
            ]["Start"]

            early_finish = calculated[
                activity_id
            ]["Finish"]

            late_start = cpm[
                activity_id
            ]["Late Start"]

            late_finish = cpm[
                activity_id
            ]["Late Finish"]

            # --------------------------------------------------
            # TOTAL FLOAT
            # --------------------------------------------------

            total_float = (
                late_start
                - early_start
            ).days

            # Protect against numerical/date inconsistencies.
            total_float = max(
                int(total_float),
                0
            )

            critical = (
                total_float == 0
            )

            result.at[
                index,
                "Late Start"
            ] = late_start

            result.at[
                index,
                "Late Finish"
            ] = late_finish

            result.at[
                index,
                "Total Float"
            ] = total_float

            result.at[
                index,
                "Critical"
            ] = critical

    return result, warnings

# ==========================================================
# INTERACTIVE GANTT CHART
# ==========================================================

@st.dialog("📊 Project Gantt Chart", width="large")
def render_gantt_chart(proposed_schedule, project_start):

    st.write(
        "Interactive view of the proposed project schedule."
    )

    # ------------------------------------------------------
    # TIMELINE SCALE
    # ------------------------------------------------------

    zoom_level = st.radio(
        "Timeline Scale",
        [
            "Days",
            "Weeks",
            "Months",
            "Quarters"
        ],
        horizontal=True,
        key="gantt_zoom_level"
    )

    # ------------------------------------------------------
    # PREPARE DATA
    # ------------------------------------------------------

    gantt_data = proposed_schedule.copy()

    gantt_data["Planned Start"] = pd.to_datetime(
        gantt_data["Planned Start"],
        errors="coerce"
    )

    gantt_data["Planned Finish"] = pd.to_datetime(
        gantt_data["Planned Finish"],
        errors="coerce"
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
        return

    gantt_data = gantt_data.reset_index(drop=True)

    # ------------------------------------------------------
    # DISPLAY DATA
    # ------------------------------------------------------

    display_data = pd.DataFrame({
        "ID": gantt_data["ID"].astype(str),
        "Activity Name": gantt_data["Activity"].astype(str),
        "Duration": (
            gantt_data["Duration"]
            .astype(str)
            + " days"
        )
    })

    # ------------------------------------------------------
    # TIMELINE SCALE
    # ------------------------------------------------------

    if zoom_level == "Days":

        dtick = 24 * 60 * 60 * 1000
        tickformat = "%d %b"

    elif zoom_level == "Weeks":

        dtick = 7 * 24 * 60 * 60 * 1000
        tickformat = "%d %b"

    elif zoom_level == "Months":

        dtick = "M1"
        tickformat = "%b %Y"

    else:

        dtick = "M3"
        tickformat = "%b %Y"

    # ------------------------------------------------------
    # CREATE GANTT TIMELINE
    # ------------------------------------------------------

    fig = go.Figure()

    for position, row in gantt_data.iterrows():

        start = row["Planned Start"]
        finish = row["Planned Finish"]

        # Inclusive date logic:
        # A 1-day activity should still display as one day.
        duration_ms = (
            finish - start
        ).total_seconds() * 1000

        if duration_ms <= 0:
            duration_ms = (
                24 * 60 * 60 * 1000
            )

        fig.add_trace(
            go.Bar(
                x=[duration_ms],
                y=[position],
                base=[start],
                orientation="h",
                hovertemplate=(
                    "<b>"
                    + str(row["Activity"])
                    + "</b><br>"
                    "ID: "
                    + str(row["ID"])
                    + "<br>"
                    "Start: "
                    + start.strftime("%d %b %Y")
                    + "<br>"
                    "Finish: "
                    + finish.strftime("%d %b %Y")
                    + "<br>"
                    "Duration: "
                    + str(row["Duration"])
                    + " days"
                    + "<extra></extra>"
                ),
                showlegend=False
            )
        )

    # ------------------------------------------------------
    # TIMELINE LAYOUT
    # ------------------------------------------------------

    fig.update_layout(
        height=max(
            500,
            len(gantt_data) * 42
        ),
        barmode="overlay",

        xaxis=dict(
            title="Project Timeline",
            type="date",
            dtick=dtick,
            tickformat=tickformat,
            showgrid=True,
            rangeslider=dict(
                visible=True
            )
        ),

        yaxis=dict(
            title="",
            tickmode="array",
            tickvals=list(
                range(len(gantt_data))
            ),
            ticktext=[
                ""
                for _ in range(len(gantt_data))
            ],
            autorange="reversed",
            showgrid=True,
            zeroline=False
        ),

        margin=dict(
            l=10,
            r=20,
            t=30,
            b=20
        ),

        hovermode="closest"
    )

    # ------------------------------------------------------
    # TABLE + GANTT LAYOUT
    # ------------------------------------------------------

    left_column, right_column = st.columns(
        [1.25, 3.75],
        gap="small"
    )

    # ------------------------------------------------------
    # LEFT: ACTIVITY INFORMATION TABLE
    # ------------------------------------------------------

    with left_column:

        st.markdown(
            """
            <div style="
                height: 38px;
                display: flex;
                align-items: center;
                font-weight: 700;
                border-bottom: 1px solid #888;
                padding-left: 6px;
            ">
                Activity Information
            </div>
            """,
            unsafe_allow_html=True
        )

        st.dataframe(
            display_data,
            hide_index=True,
            use_container_width=True,
            height=max(
                430,
                len(display_data) * 35 + 45
            ),
            column_config={
                "ID": st.column_config.TextColumn(
                    "ID",
                    width="small"
                ),
                "Activity Name": st.column_config.TextColumn(
                    "Activity Name",
                    width="large"
                ),
                "Duration": st.column_config.TextColumn(
                    "Duration",
                    width="small"
                )
            }
        )

    # ------------------------------------------------------
    # RIGHT: GANTT TIMELINE
    # ------------------------------------------------------

    with right_column:

        st.markdown(
            """
            <div style="
                height: 38px;
                display: flex;
                align-items: center;
                font-weight: 700;
                border-bottom: 1px solid #888;
                padding-left: 6px;
            ">
                Project Timeline
            </div>
            """,
            unsafe_allow_html=True
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
        "Use Days, Weeks, Months or Quarters to change "
        "the timeline scale. You can also zoom and pan "
        "directly on the chart."
    )

# ==========================================================
# RENDER STEP 3
# ==========================================================

def render_scheduling():

    st.header("Step 3 — Planning & Scheduling")

    st.write(
        "Review activity durations and relationships, "
        "calculate the proposed project schedule, and "
        "confirm the schedule before locking it."
    )

    activities = st.session_state.activities.copy()

    project = st.session_state.project

    project_start = project.get("start_date")

    # ======================================================
    # BASIC VALIDATION
    # ======================================================

    if activities.empty:

        st.warning(
            "No activities are available. "
            "Return to Step 2 and add or import activities."
        )

        if st.button(
            "← Back to Activity Data",
            use_container_width=True
        ):

            st.session_state.current_step = 2
            st.rerun()

        return

    if project_start is None:

        st.error(
            "Project start date is missing. "
            "Return to Step 1 and provide the planned start date."
        )

        if st.button(
            "← Back to Project Setup",
            use_container_width=True
        ):

            st.session_state.current_step = 1
            st.rerun()

        return

    # ======================================================
    # PROJECT SUMMARY
    # ======================================================

    st.subheader("Project Scheduling Information")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Project",
            project.get("name", "Unnamed Project")
        )

    with col2:

        st.metric(
            "Planned Start",
            format_date(project_start)
        )

    with col3:

        st.metric(
            "Activities",
            len(activities)
        )

    st.divider()

    # ======================================================
    # DURATION STATUS
    # ======================================================

    tentative_mask = (
        activities["Duration Source"]
        .astype(str)
        .eq("Tentative")
    )

    tentative_count = int(
        tentative_mask.sum()
    )

    if tentative_count > 0:

        st.warning(
            f"{tentative_count} activity/activities have "
            "tentative durations. Review them before locking "
            "the schedule."
        )

    else:

        st.success(
            "All activity durations are currently specified."
        )

    # ======================================================
    # AI RELATIONSHIP ANALYSIS
    # ======================================================

    st.subheader("AI Planning Assistant")

    render_ai_relationship_analysis(
        st.session_state.activities.copy()
    )

    st.divider()

    # ======================================================
    # CALCULATE SCHEDULE
    # ======================================================

    st.subheader("2. Calculate Proposed Schedule")

    st.write(
        "Once the AI-reviewed relationships have been "
        "validated successfully, the scheduling engine "
        "will calculate the proposed project dates."
    )

    ai_saved = st.session_state.get(
        "ai_relationship_saved",
        False
    )

    ai_validated = st.session_state.get(
        "ai_validation_passed",
        False
    )

    # ------------------------------------------------------
    # AI REVIEW STATUS
    # ------------------------------------------------------

    if not ai_saved:

        st.info(
            "Complete and save the AI relationship review "
            "before calculating the schedule."
        )

    elif not ai_validated:

        st.warning(
            "Relationship validation has not passed yet. "
            "Validate the saved relationships before "
            "calculating the schedule."
        )

    else:

        st.success(
            "✅ Relationship validation passed. "
            "The schedule is ready to be calculated."
        )

        if st.button(
            "🧮 Calculate Proposed Schedule",
            type="primary",
            use_container_width=True
        ):

            saved_relationships = (
                st.session_state.get(
                    "ai_saved_relationships"
                )
            )

            if saved_relationships is None:

                st.error(
                    "No saved relationship data is available. "
                    "Please save the AI relationship review again."
                )

            else:

                proposed_schedule, schedule_warnings = (
                    calculate_schedule(
                        saved_relationships,
                        project_start
                    )
                )

                st.session_state.proposed_schedule = (
                    proposed_schedule
                )

                st.session_state.schedule_warnings = (
                    schedule_warnings
                )

                st.success(
                    "Proposed schedule calculated successfully."
                )

                st.rerun()

    # ======================================================
    # PROPOSED SCHEDULE
    # ======================================================

    if (
        "proposed_schedule"
        in st.session_state
    ):

        st.divider()

        st.subheader(
            "3. Proposed Project Schedule"
        )

        proposed = (
            st.session_state.proposed_schedule
            .copy()
        )

        # --------------------------------------------------
        # GANTT CHART
        # --------------------------------------------------

        if st.button(
            "📊 View Gantt Chart",
            type="primary",
            use_container_width=True
        ):

            render_gantt_chart(
                proposed,
                project_start
            )

        schedule_warnings = st.session_state.get(
            "schedule_warnings",
            []
        )

        if schedule_warnings:

            st.warning(
                "The scheduler generated the following warnings:"
            )

            for warning in schedule_warnings:

                st.write(
                    f"• {warning}"
                )

        # --------------------------------------------------
        # PROJECT DURATION
        # --------------------------------------------------

        valid_finish_dates = []

        for value in proposed[
            "Planned Finish"
        ]:

            if pd.notna(value):

                valid_finish_dates.append(
                    value
                )

        if valid_finish_dates:

            project_finish = max(
                valid_finish_dates
            )

            project_duration = (
                project_finish
                - project_start
            ).days + 1

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Calculated Project Finish",
                    format_date(project_finish)
                )

            with col2:

                st.metric(
                    "Calculated Project Duration",
                    f"{project_duration} days"
                )

        # --------------------------------------------------
        # DISPLAY SCHEDULE
        # --------------------------------------------------

        schedule_display = proposed.copy()

        # --------------------------------------------------
        # ADD WBS NAME
        # --------------------------------------------------

        approved_wbs = st.session_state.get(
            "wbs",
            pd.DataFrame()
        )

        if (
            isinstance(approved_wbs, pd.DataFrame)
            and not approved_wbs.empty
            and "WBS ID" in approved_wbs.columns
            and "WBS Name" in approved_wbs.columns
        ):

            wbs_name_lookup = (
                approved_wbs[
                    [
                        "WBS ID",
                        "WBS Name"
                    ]
                ]
                .drop_duplicates(
                    subset=["WBS ID"]
                )
                .set_index("WBS ID")["WBS Name"]
                .to_dict()
            )

            schedule_display["WBS Name"] = (
                schedule_display["WBS"]
                .astype(str)
                .str.strip()
                .map(wbs_name_lookup)
                .fillna("")
            )

        else:

            schedule_display["WBS Name"] = ""

        # --------------------------------------------------
        # FORMAT DATES
        # --------------------------------------------------

        schedule_display["Planned Start"] = (
            pd.to_datetime(
                schedule_display["Planned Start"],
                errors="coerce"
            )
            .dt.strftime("%d %b %Y")
        )

        schedule_display["Planned Finish"] = (
            pd.to_datetime(
                schedule_display["Planned Finish"],
                errors="coerce"
            )
            .dt.strftime("%d %b %Y")
        )

        # --------------------------------------------------
        # DISPLAY SCHEDULE TABLE
        # --------------------------------------------------

        st.dataframe(
            schedule_display[
                [
                    "ID",
                    "WBS",
                    "WBS Name",
                    "Activity",
                    "Duration",
                    "Duration Source",
                    "Relationship",
                    "Predecessor",
                    "Planned Start",
                    "Planned Finish"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # --------------------------------------------------
        # FINAL REVIEW
        # --------------------------------------------------

        st.subheader(
            "4. Final Review Before Locking"
        )

        st.info(
            "The schedule is still a proposal. "
            "Review the activities, durations, relationships "
            "and calculated dates carefully. Nothing is locked "
            "until you explicitly confirm it."
        )

        confirm_review = st.checkbox(
            "I have reviewed the proposed schedule and "
            "confirm that the activities, durations, "
            "relationships and dates are acceptable.",
            key="schedule_review_confirmation"
        )

        if confirm_review:

            if st.button(
                "Finalize Proposed Schedule →",
                type="primary",
                use_container_width=True
            ):

                st.session_state.finalized_schedule = (
                    proposed.copy()
                )

                st.session_state.schedule_finalized = True

                st.session_state.current_step = 4

                st.success(
                    "Proposed schedule finalized. "
                    "Proceeding to Baseline Review."
                )

                st.rerun()

    st.divider()

    # ======================================================
    # NAVIGATION
    # ======================================================

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "← Back to Activity Data",
            use_container_width=True
        ):

            st.session_state.current_step = 2
            st.rerun()

    with col2:

        st.empty()

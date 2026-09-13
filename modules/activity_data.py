
import io
import re

import pandas as pd
import streamlit as st

from modules.ai_wbs_builder import (
    get_ai_wbs_suggestions,
    get_ai_activity_wbs_mapping
)

from utils import (
    add_activity,
    create_activity_id,
    delete_activity,
    format_date,
    guess_column,
    normalize_columns,
    parse_duration,
    parse_number
)


RELATIONSHIP_OPTIONS = [
    "No Predecessor",
    "Finish-to-Start (FS)",
    "Start-to-Start (SS)",
    "Finish-to-Finish (FF)",
    "Start-to-Finish (SF)"
]

def detect_structured_wbs(df, wbs_column):
    """
    Determine whether the selected column contains
    a recognizable hierarchical WBS structure.
    """

    if (
        wbs_column is None
        or wbs_column == "— Do not import —"
        or wbs_column not in df.columns
    ):
        return False

    values = (
        df[wbs_column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    if values.empty:
        return False

    # Recognize hierarchical numeric WBS IDs:
    # 1.0
    # 1.1
    # 1.1.1
    # 2.0
    wbs_pattern = re.compile(
        r"^\d+(?:\.\d+)+$"
    )

    matches = values.apply(
        lambda value: bool(
            wbs_pattern.match(value)
        )
    )

    # Require the majority of populated values
    # to look like hierarchical WBS IDs.
    return (
        matches.mean() >= 0.70
    )


def render_boq_format_preview():

    st.markdown("### 📋 Recommended BOQ / WBS Format")

    st.caption(
        "Your BOQ does not need to match this format exactly. "
        "The example shows the recommended structure for importing data."
    )

    sample_data = pd.DataFrame({
        "Ser No": [1, 2, 3, 4, 5, 6],
        "Description": [
            "Site clearance & layout marking",
            "Excavation for foundation",
            "Backfilling with soil",
            "PCC below footing",
            "RCC in footings",
            "Centering & shuttering"
        ],
        "Unit": [
            "L.S",
            "Cu.m",
            "Cu.m",
            "Cu.m",
            "Cu.m",
            "Sq.m"
        ],
        "Quantity": [
            1,
            20,
            12,
            3.5,
            4.2,
            120
        ],
        "Rate": [
            12000,
            450,
            300,
            6500,
            8500,
            950
        ],
        "Amount": [
            12000,
            9000,
            3600,
            22750,
            35700,
            114000
        ]
    })

    st.dataframe(
        sample_data,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "**Recommended fields:** "
        "Description = Activity, "
        "Unit = Unit, "
        "Quantity = BOQ Qty, "
        "Rate = Rate, "
        "Amount = Amount. "
        "WBS and Duration are optional."
    )


def validate_approved_wbs(wbs_df):
    """
    Validate the approved WBS structure before it becomes
    the authoritative project WBS.
    """

    errors = []

    if wbs_df is None or wbs_df.empty:
        errors.append("No WBS data is available.")
        return False, errors

    required_columns = [
        "WBS ID",
        "WBS Name",
        "Parent WBS",
        "Level",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in wbs_df.columns
    ]

    if missing_columns:
        errors.append(
            "Missing WBS columns: "
            + ", ".join(missing_columns)
        )
        return False, errors

    # ------------------------------------------------------
    # DUPLICATE IDS
    # ------------------------------------------------------

    duplicate_ids = (
        wbs_df["WBS ID"]
        .astype(str)
        .str.strip()
        .duplicated()
    )

    if duplicate_ids.any():

        duplicates = (
            wbs_df.loc[
                duplicate_ids,
                "WBS ID"
            ]
            .astype(str)
            .tolist()
        )

        errors.append(
            "Duplicate WBS IDs: "
            + ", ".join(duplicates)
        )

    # ------------------------------------------------------
    # BUILD LOOKUP
    # ------------------------------------------------------

    valid_ids = set(
        wbs_df["WBS ID"]
        .astype(str)
        .str.strip()
    )

    level_lookup = {}

    for _, row in wbs_df.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        try:
            level = int(
                row["Level"]
            )
        except (TypeError, ValueError):
            errors.append(
                f"{wbs_id}: invalid WBS level."
            )
            continue

        level_lookup[wbs_id] = level

    # ------------------------------------------------------
    # PARENT VALIDATION
    # ------------------------------------------------------

    for _, row in wbs_df.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        parent_wbs = str(
            row["Parent WBS"]
        ).strip()

        try:
            level = int(
                row["Level"]
            )
        except (TypeError, ValueError):
            continue

        if level == 1:

            if parent_wbs:
                errors.append(
                    f"{wbs_id}: Level 1 WBS cannot "
                    "have a parent."
                )

        else:

            if not parent_wbs:

                errors.append(
                    f"{wbs_id}: parent WBS is required."
                )

            elif parent_wbs not in valid_ids:

                errors.append(
                    f"{wbs_id}: parent WBS "
                    f"'{parent_wbs}' does not exist."
                )

            elif (
                parent_wbs in level_lookup
                and level_lookup[parent_wbs] != level - 1
            ):

                errors.append(
                    f"{wbs_id}: parent WBS level is "
                    "incorrect."
                )

    return len(errors) == 0, errors


def build_activity_wbs_mapping_view(
    imported_activities,
    mapping_df,
    approved_wbs
):
    """
    Build the human-reviewable Activity → WBS mapping table.

    Activity text and WBS names are calculated by the application.
    AI only supplies the proposed WBS, confidence, and reason.
    """

    if (
        imported_activities is None
        or imported_activities.empty
    ):
        return pd.DataFrame()

    if (
        mapping_df is None
        or mapping_df.empty
    ):
        return pd.DataFrame()

    if (
        approved_wbs is None
        or approved_wbs.empty
    ):
        return pd.DataFrame()

    # --------------------------------------------------
    # BUILD WBS LOOKUP
    # --------------------------------------------------

    wbs_name_lookup = {}

    for _, row in approved_wbs.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        wbs_name = str(
            row["WBS Name"]
        ).strip()

        if wbs_id:
            wbs_name_lookup[wbs_id] = wbs_name

    # --------------------------------------------------
    # BUILD ACTIVITY LOOKUP
    # --------------------------------------------------

    activity_lookup = {}

    for index, row in imported_activities.iterrows():

        activity_index = index + 1

        activity_text = str(
            row.get(
                "Activity",
                ""
            )
        ).strip()

        activity_lookup[
            activity_index
        ] = activity_text

    # --------------------------------------------------
    # BUILD REVIEW TABLE
    # --------------------------------------------------

    records = []

    for _, mapping in mapping_df.iterrows():

        activity_index = int(
            mapping["Activity Index"]
        )

        suggested_wbs = str(
            mapping["Suggested WBS"]
        ).strip()

        records.append(
            {
                "Activity": activity_lookup.get(
                    activity_index,
                    ""
                ),

                "Proposed WBS": suggested_wbs,

                "WBS Name": wbs_name_lookup.get(
                    suggested_wbs,
                    ""
                ),

                "Confidence": mapping.get(
                    "Confidence",
                    "Low"
                ),

                "Reason": mapping.get(
                    "Reason",
                    ""
                ),

                "Approve": bool(
                    mapping.get(
                        "Approve",
                        False
                    )
                ),

                "Status": mapping.get(
                    "Status",
                    "⏳ Pending"
                ),
            }
        )

    return pd.DataFrame(
        records,
        columns=[
            "Activity",
            "Proposed WBS",
            "WBS Name",
            "Confidence",
            "Reason",
            "Approve",
            "Status",
        ]
    )


def render_ai_wbs_builder():

    st.subheader("🤖 AI WBS Builder")

    st.caption(
        "Generate a proposed construction Work Breakdown Structure "
        "from the project scope. The AI creates WBS structure only — "
        "activities are developed separately."
    )

    project = st.session_state.project

    # ------------------------------------------------------
    # PROJECT INFORMATION
    # ------------------------------------------------------

    project_name = project.get(
        "name",
        ""
    )

    st.write(
        f"**Project:** {project_name}"
    )

    project_description = st.text_area(
        "Project Scope / Description",
        placeholder=(
            "Describe the project, major construction works, "
            "building type, infrastructure scope, etc."
        ),
        height=140,
        key="ai_wbs_project_description"
    )

    # ------------------------------------------------------
    # API CONNECTION
    # ------------------------------------------------------

    api_key = st.text_input(
        "Groq API Key",
        type="password",
        key="step2_ai_wbs_api_key",
        help=(
            "Your API key is used only for this AI request."
        )
    )

    model_options = {
        "gpt-oss-20b": "openai/gpt-oss-20b",
        "gpt-oss-120b": "openai/gpt-oss-120b",
    }

    selected_model_name = st.selectbox(
        "AI Model",
        list(model_options.keys()),
        key="step2_ai_wbs_model"
    )

    selected_model = model_options[
        selected_model_name
    ]

    # ------------------------------------------------------
    # GENERATE WBS
    # ------------------------------------------------------

    if st.button(
        "🤖 Generate AI WBS",
        type="primary",
        use_container_width=True
    ):

        if not project_name.strip():

            st.error(
                "Project name is required."
            )

        elif not project_description.strip():

            st.error(
                "Please provide a project description."
            )

        elif not api_key.strip():

            st.error(
                "Please enter your Groq API key."
            )

        else:

            with st.spinner(
                "AI is developing the project WBS..."
            ):

                try:

                    wbs_suggestions = (
                        get_ai_wbs_suggestions(
                            project_name,
                            project_description,
                            api_key.strip(),
                            selected_model
                        )
                    )

                    st.session_state.ai_wbs_data = (
                        wbs_suggestions.copy()
                    )

                    st.session_state.ai_wbs_original = (
                        wbs_suggestions.copy()
                    )

                    st.session_state.ai_wbs_approved = False

                    # The newly generated WBS is not yet authoritative.
                    st.session_state.wbs_approved = False

                    # Remove the previous authoritative WBS.
                    st.session_state.pop(
                        "wbs",
                        None
                    )

                    # Any previous Activity → WBS mapping is now invalid
                    # because a new WBS has been generated.
                    st.session_state.pop(
                        "ai_activity_wbs_mapping",
                        None
                    )

                    st.session_state.pop(
                        "approved_activity_wbs_mapping",
                        None
                    )

                    st.session_state.pop(
                        "boq_wbs_mapping_approved",
                        None
                    )

                    st.success(
                        "AI WBS generated successfully."
                    )

                    st.success(
                        "AI WBS generated successfully."
                    )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        "AI WBS generation failed."
                    )

                    st.exception(exc)

    # ------------------------------------------------------
    # WBS REVIEW
    # ------------------------------------------------------

    if "ai_wbs_data" not in st.session_state:

        st.info(
            "Generate an AI WBS to begin the WBS review."
        )

        return

    wbs_data = (
        st.session_state.ai_wbs_data.copy()
    )

    st.divider()

    st.subheader("Review Proposed WBS")

    st.info(
        "Review and modify the proposed WBS before approving it. "
        "Activities will be created separately."
    )

    edited_wbs = st.data_editor(

        wbs_data,

        use_container_width=True,

        hide_index=True,

        disabled=[
            "Status"
        ],

        column_config={

            "WBS ID": st.column_config.TextColumn(
                "WBS ID",
                required=True
            ),

            "WBS Name": st.column_config.TextColumn(
                "WBS Name",
                required=True
            ),

            "Parent WBS": st.column_config.TextColumn(
                "Parent WBS"
            ),

            "Level": st.column_config.NumberColumn(
                "Level",
                min_value=1,
                step=1
            ),

            "Description": st.column_config.TextColumn(
                "Description"
            ),

            "Approve": st.column_config.CheckboxColumn(
                "Approve"
            ),

            "Status": st.column_config.TextColumn(
                "Status",
                disabled=True
            )
        },

        key="ai_wbs_editor"
    )

    # ------------------------------------------------------
    # SAVE WBS CHANGES
    # ------------------------------------------------------

    if st.button(
        "💾 Save WBS Changes",
        use_container_width=True
    ):

        saved_wbs = edited_wbs.copy()

        original_wbs = (
            st.session_state.ai_wbs_original
        )

        for index in saved_wbs.index:

            if index >= len(original_wbs):

                saved_wbs.loc[
                    index,
                    "Status"
                ] = "✏️ Modified"

                continue

            current_row = (
                saved_wbs.loc[index]
            )

            original_row = (
                original_wbs.loc[index]
            )

            changed = False

            for column in [
                "WBS ID",
                "WBS Name",
                "Parent WBS",
                "Level",
                "Description"
            ]:

                if str(
                    current_row[column]
                ) != str(
                    original_row[column]
                ):

                    changed = True
                    break

            if changed:

                saved_wbs.loc[
                    index,
                    "Status"
                ] = "✏️ Modified"

            elif bool(
                saved_wbs.loc[
                    index,
                    "Approve"
                ]
            ):

                saved_wbs.loc[
                    index,
                    "Status"
                ] = "✅ Approved"

            else:

                saved_wbs.loc[
                    index,
                    "Status"
                ] = "⏳ Pending"

        st.session_state.ai_wbs_data = (
            saved_wbs.copy()
        )

        # Any existing Activity → WBS mapping may now be invalid
        # because the WBS structure was edited.
        st.session_state.pop(
            "ai_activity_wbs_mapping",
            None
        )

        st.session_state.pop(
            "approved_activity_wbs_mapping",
            None
        )

        st.session_state.pop(
            "boq_wbs_mapping_approved",
            None
        )

        st.success(
            "WBS changes saved."
        )

        st.success(
            "WBS changes saved."
        )

        st.rerun()

    # ------------------------------------------------------
    # APPROVE WBS
    # ------------------------------------------------------

    st.divider()

    if st.button(
        "✅ Approve WBS",
        type="primary",
        use_container_width=True
    ):

        current_wbs = (
            st.session_state.ai_wbs_data.copy()
        )

        # ----------------------------------------------
        # Check all rows approved
        # ----------------------------------------------

        pending_rows = current_wbs[
            current_wbs["Approve"] != True
        ]

        if not pending_rows.empty:

            st.error(
                "All WBS elements must be approved "
                "before the WBS can be locked."
            )

        else:

            valid, errors = (
                validate_approved_wbs(
                    current_wbs
                )
            )

            if not valid:

                st.error(
                    "WBS validation failed."
                )

                for error in errors:

                    st.markdown(
                        f"• {error}"
                    )

            else:

                # --------------------------------------
                # AUTHORITATIVE APPROVED WBS
                # --------------------------------------

                st.session_state.wbs = (
                    current_wbs.copy()
                )

                st.session_state.wbs_approved = True

                st.success(
                    "✅ WBS approved and saved "
                    "as the project WBS."
                )

                st.rerun()

    # ------------------------------------------------------
    # APPROVED STATUS
    # ------------------------------------------------------

    if st.session_state.get(
        "wbs_approved",
        False
    ):

        st.success(
            "✅ Project WBS is approved."
        )

        st.caption(
            "The approved WBS can now be used when "
            "creating or editing project activities."
        )


def stage_pending_boq_activities(imported_rows):
    """
    Store imported BOQ activities temporarily.

    These activities are NOT authoritative until the
    Activity -> WBS mapping has been reviewed and approved.

    ABSOLUTE RULE:
        Pending activities must never exist in the
        authoritative Activity Register.
    """

    pending_rows = []

    for index, row in enumerate(
        imported_rows,
        start=1
    ):

        pending_rows.append({

            "Activity Index":
                index,

            "Activity":
                str(
                    row.get(
                        "Activity",
                        ""
                    )
                ),

            "WBS":
                str(
                    row.get(
                        "WBS",
                        ""
                    )
                ).strip(),

            "Description":
                str(
                    row.get(
                        "Description",
                        ""
                    )
                ),

            "Duration":
                int(
                    row.get(
                        "Duration",
                        1
                    )
                ),

            "Duration Source":
                str(
                    row.get(
                        "Duration Source",
                        "Tentative"
                    )
                ),

            "Relationship":
                str(
                    row.get(
                        "Relationship",
                        "No Predecessor"
                    )
                ),

            "Predecessor":
                str(
                    row.get(
                        "Predecessor",
                        ""
                    )
                ),

            "BOQ Qty":
                row.get(
                    "BOQ Qty",
                    0.0
                ),

            "Unit":
                str(
                    row.get(
                        "Unit",
                        ""
                    )
                ),

            "Rate":
                row.get(
                    "Rate",
                    0.0
                ),

            "Amount":
                row.get(
                    "Amount",
                    0.0
                )
        })

    st.session_state.pending_boq_activities = (
        pd.DataFrame(pending_rows)
    )

    # ==========================================================
    # ABSOLUTE REGISTER SAFETY
    # ==========================================================
    #
    # Any activity with no WBS is not authoritative.
    # Remove such legacy rows immediately.

    if (
        "activities" in st.session_state
        and not st.session_state.activities.empty
    ):

        activities = (
            st.session_state.activities.copy()
        )

        activities["WBS"] = (
            activities["WBS"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        activities = activities[
            activities["WBS"] != ""
        ].copy()

        st.session_state.activities = (
            activities
        )

    # ==========================================================
    # INVALIDATE OLD MAPPING
    # ==========================================================

    st.session_state.pop(
        "ai_activity_wbs_mapping",
        None
    )

    st.session_state.pop(
        "approved_activity_wbs_mapping",
        None
    )

    st.session_state.pop(
        "boq_wbs_mapping_approved",
        None
    )


def get_pending_activity_context():
    """
    Convert pending BOQ activities into the compact format
    required by the AI mapping function.
    """

    pending = st.session_state.get(
        "pending_boq_activities"
    )

    if pending is None or pending.empty:
        return []

    return [
        {
            "Activity Index": int(row["Activity Index"]),
            "Activity": str(row["Activity"])
        }
        for _, row in pending.iterrows()
    ]


def build_activity_wbs_mapping_view(
    pending_activities,
    mapping_df,
    approved_wbs
):
    """
    Build the human-review table for Activity -> WBS mapping.
    """

    if pending_activities is None or pending_activities.empty:
        return pd.DataFrame()

    if mapping_df is None or mapping_df.empty:
        return pd.DataFrame()

    wbs_lookup = {}

    for _, row in approved_wbs.iterrows():

        wbs_id = str(
            row.get("WBS ID", "")
        ).strip()

        wbs_name = str(
            row.get("WBS Name", "")
        ).strip()

        if wbs_id:
            wbs_lookup[wbs_id] = wbs_name

    activity_lookup = {}

    for _, row in pending_activities.iterrows():

        activity_index = int(
            row["Activity Index"]
        )

        activity_lookup[activity_index] = str(
            row["Activity"]
        )

    review_rows = []

    for _, mapping in mapping_df.iterrows():

        activity_index = int(
            mapping["Activity Index"]
        )

        proposed_wbs = str(
            mapping["Suggested WBS"]
        ).strip()

        review_rows.append({
            "Activity Index": activity_index,
            "Activity": activity_lookup.get(
                activity_index,
                ""
            ),
            "Proposed WBS": proposed_wbs,
            "WBS Name": wbs_lookup.get(
                proposed_wbs,
                ""
            ),
            "Confidence": str(
                mapping.get("Confidence", "Low")
            ),
            "Reason": str(
                mapping.get("Reason", "")
            ),
            "Approve": bool(
                mapping.get("Approve", False)
            ),
            "Status": str(
                mapping.get("Status", "⏳ Pending")
            )
        })

    return pd.DataFrame(review_rows)


def render_activity_wbs_mapping():
    """
    Complete human review and approval workflow for:

        Imported BOQ
             ↓
        Approved AI WBS
             ↓
        AI Activity → WBS Proposal
             ↓
        Human Review/Edit
             ↓
        Human Approval
             ↓
        Authoritative Activity Register
    """

    pending = st.session_state.get(
        "pending_boq_activities"
    )

    if pending is None or pending.empty:
        return

    st.divider()

    st.subheader(
        "4. BOQ Activity → Approved WBS Mapping"
    )

    st.caption(
        f"{len(pending)} BOQ activities are currently "
        "pending WBS assignment."
    )

    st.write(
        "The imported BOQ activities are currently staged. "
        "AI will propose a WBS assignment for each activity "
        "using only the approved project WBS. "
        "You must review and approve every assignment before "
        "the activities enter the authoritative Activity Register."
    )

    # ----------------------------------------------------------
    # REQUIRE APPROVED WBS
    # ----------------------------------------------------------

    approved_wbs = st.session_state.get("wbs")

    wbs_approved = st.session_state.get(
        "wbs_approved",
        False
    )

    if (
        not wbs_approved
        or approved_wbs is None
        or approved_wbs.empty
    ):

        st.warning(
            "Approve the AI-generated WBS first. "
            "Activity-to-WBS mapping cannot begin until "
            "the WBS is approved."
        )

        return

    # ----------------------------------------------------------
    # WBS SUMMARY
    # ----------------------------------------------------------

    st.success(
        f"Approved WBS available: "
        f"{len(approved_wbs)} WBS elements."
    )

    # ----------------------------------------------------------
    # AI MAPPING GENERATION
    # ----------------------------------------------------------

    mapping_df = st.session_state.get(
        "ai_activity_wbs_mapping"
    )

    if mapping_df is None or mapping_df.empty:

        st.markdown(
            "### AI Activity Mapping"
        )

        st.info(
            "AI will propose one WBS assignment for every "
            "imported BOQ activity. AI does not modify the "
            "approved WBS."
        )

        api_key = st.text_input(
            "Groq API Key",
            type="password",
            key="activity_wbs_mapping_api_key"
        )

        model_options = {
            "gpt-oss-20b":
                "openai/gpt-oss-20b",

            "gpt-oss-120b":
                "openai/gpt-oss-120b"
        }

        selected_model_label = st.selectbox(
            "AI Model",
            list(model_options.keys()),
            key="activity_wbs_mapping_model"
        )

        selected_model = model_options[
            selected_model_label
        ]

        if st.button(
            "🤖 Propose Activity → WBS Mapping",
            type="primary",
            use_container_width=True
        ):

            if not api_key.strip():

                st.error(
                    "Please provide the Groq API key."
                )

            else:

                try:

                    activity_context = (
                        get_pending_activity_context()
                    )

                    proposed_mapping = (
                        get_ai_activity_wbs_mapping(
                            activity_context,
                            approved_wbs,
                            api_key.strip(),
                            selected_model
                        )
                    )

                    st.session_state.ai_activity_wbs_mapping = (
                        proposed_mapping
                    )

                    st.success(
                        "AI activity-to-WBS mapping generated. "
                        "Review every proposed assignment below."
                    )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        f"AI mapping failed: {exc}"
                    )

        return

    # ----------------------------------------------------------
    # BUILD REVIEW TABLE
    # ----------------------------------------------------------

    review_df = build_activity_wbs_mapping_view(
        pending,
        mapping_df,
        approved_wbs
    )

    if review_df.empty:

        st.error(
            "No activity-to-WBS mapping data is available."
        )

        return

    # ----------------------------------------------------------
    # APPROVED WBS OPTIONS
    # ----------------------------------------------------------

    wbs_options = []

    for _, row in approved_wbs.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        wbs_name = str(
            row["WBS Name"]
        ).strip()

        wbs_options.append(
            f"{wbs_id} — {wbs_name}"
        )

    # ----------------------------------------------------------
    # DATA EDITOR
    # ----------------------------------------------------------

    edited_df = st.data_editor(
        review_df,
        hide_index=True,
        use_container_width=True,
        disabled=[
            "Activity Index",
            "Activity",
            "WBS Name",
            "Confidence",
            "Reason",
            "Status"
        ],
        column_config={

            "Activity Index":
                st.column_config.NumberColumn(
                    "Activity #",
                    disabled=True
                ),

            "Activity":
                st.column_config.TextColumn(
                    "BOQ Activity",
                    disabled=True,
                    width="large"
                ),

            "Proposed WBS":
                st.column_config.SelectboxColumn(
                    "Proposed WBS",
                    options=[
                        option.split(
                            " — ",
                            1
                        )[0]
                        for option in wbs_options
                    ],
                    required=True
                ),

            "WBS Name":
                st.column_config.TextColumn(
                    "WBS Name",
                    disabled=True
                ),

            "Confidence":
                st.column_config.TextColumn(
                    "AI Confidence",
                    disabled=True
                ),

            "Reason":
                st.column_config.TextColumn(
                    "AI Reason",
                    disabled=True,
                    width="large"
                ),

            "Approve":
                st.column_config.CheckboxColumn(
                    "Approve",
                    help=(
                        "Approve this activity's "
                        "WBS assignment."
                    )
                ),

            "Status":
                st.column_config.TextColumn(
                    "Status",
                    disabled=True
                )
        },
        key="activity_wbs_mapping_editor"
    )

    # ----------------------------------------------------------
    # SAVE MAPPING CHANGES
    # ----------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "💾 Save Mapping Changes",
            use_container_width=True
        ):

            valid_wbs_ids = set(
                approved_wbs["WBS ID"]
                .astype(str)
                .str.strip()
            )

            invalid = []

            for _, row in edited_df.iterrows():

                selected_wbs = str(
                    row["Proposed WBS"]
                ).strip()

                if selected_wbs not in valid_wbs_ids:

                    invalid.append(
                        (
                            int(row["Activity Index"]),
                            selected_wbs
                        )
                    )

            if invalid:

                st.error(
                    "One or more activities have an "
                    "invalid WBS assignment."
                )

            else:

                original_mapping = (
                    st.session_state
                    .ai_activity_wbs_mapping
                    .copy()
                )

                updated_mapping = []

                for _, row in edited_df.iterrows():

                    activity_index = int(
                        row["Activity Index"]
                    )

                    proposed_wbs = str(
                        row["Proposed WBS"]
                    ).strip()

                    original_row = (
                        original_mapping[
                            original_mapping[
                                "Activity Index"
                            ] == activity_index
                        ]
                    )

                    original_wbs = ""

                    if not original_row.empty:

                        original_wbs = str(
                            original_row.iloc[0][
                                "Suggested WBS"
                            ]
                        ).strip()

                    if proposed_wbs != original_wbs:

                        status = "✏️ Modified"

                    elif bool(row["Approve"]):

                        status = "✅ Approved"

                    else:

                        status = "⏳ Pending"

                    updated_mapping.append({
                        "Activity Index":
                            activity_index,

                        "Suggested WBS":
                            proposed_wbs,

                        "Confidence":
                            str(row["Confidence"]),

                        "Reason":
                            str(row["Reason"]),

                        "Approve":
                            bool(row["Approve"]),

                        "Status":
                            status
                    })

                st.session_state.ai_activity_wbs_mapping = (
                    pd.DataFrame(updated_mapping)
                )

                st.success(
                    "Mapping changes saved."
                )

                st.rerun()

    # ----------------------------------------------------------
    # APPROVE MAPPING
    # ----------------------------------------------------------

    with col2:

        if st.button(
            "✅ Approve Activity → WBS Mapping",
            type="primary",
            use_container_width=True
        ):

            current_mapping = (
                st.session_state
                .ai_activity_wbs_mapping
            )

            # ----------------------------------------------
            # CHECK EVERY ACTIVITY
            # ----------------------------------------------

            if not all(
                current_mapping["Approve"].astype(bool)
            ):

                st.error(
                    "Every activity must be approved "
                    "before the mapping can be finalized."
                )

                return

            # ----------------------------------------------
            # VALIDATE WBS IDS
            # ----------------------------------------------

            valid_wbs_ids = set(
                approved_wbs["WBS ID"]
                .astype(str)
                .str.strip()
            )

            invalid_wbs = []

            for _, row in current_mapping.iterrows():

                wbs_id = str(
                    row["Suggested WBS"]
                ).strip()

                if wbs_id not in valid_wbs_ids:

                    invalid_wbs.append(
                        wbs_id
                    )

            if invalid_wbs:

                st.error(
                    "Invalid WBS assignment detected: "
                    + ", ".join(
                        sorted(
                            set(invalid_wbs)
                        )
                    )
                )

                return

            # ----------------------------------------------
            # CREATE AUTHORITATIVE ACTIVITIES
            # ----------------------------------------------

            existing_count = len(
                st.session_state.activities
            )

            new_activity_rows = []

            for _, pending_row in pending.iterrows():

                activity_index = int(
                    pending_row["Activity Index"]
                )

                mapping_row = (
                    current_mapping[
                        current_mapping[
                            "Activity Index"
                        ] == activity_index
                    ]
                )

                if mapping_row.empty:

                    st.error(
                        f"No WBS mapping exists for "
                        f"Activity #{activity_index}."
                    )

                    return

                mapped_wbs = str(
                    mapping_row.iloc[0][
                        "Suggested WBS"
                    ]
                ).strip()

                activity_id = (
                    f"A{existing_count + len(new_activity_rows) + 1:03d}"
                )

                # IMPORTANT:
                # Activity wording is copied exactly.
                new_activity_rows.append({

                    "ID":
                        activity_id,

                    "WBS":
                        mapped_wbs,

                    "Activity":
                        str(
                            pending_row["Activity"]
                        ),

                    "Description":
                        str(
                            pending_row.get(
                                "Description",
                                ""
                            )
                        ),

                    "Duration":
                        int(
                            pending_row.get(
                                "Duration",
                                1
                            )
                        ),

                    "Duration Source":
                        str(
                            pending_row.get(
                                "Duration Source",
                                "Tentative"
                            )
                        ),

                    "Relationship":
                        "No Predecessor",

                    "Predecessor":
                        "",

                    "BOQ Qty":
                        pending_row.get(
                            "BOQ Qty",
                            0.0
                        ),

                    "Unit":
                        str(
                            pending_row.get(
                                "Unit",
                                ""
                            )
                        ),

                    "Rate":
                        pending_row.get(
                            "Rate",
                            0.0
                        ),

                    "Amount":
                        pending_row.get(
                            "Amount",
                            0.0
                        )
                })


                            # ----------------------------------------------
            # COMMIT ACTIVITIES TO AUTHORITATIVE REGISTER
            # ----------------------------------------------

            if new_activity_rows:

                new_activities_df = pd.DataFrame(
                    new_activity_rows
                )

                st.session_state.activities = pd.concat(
                    [
                        st.session_state.activities,
                        new_activities_df
                    ],
                    ignore_index=True
                )

            # ----------------------------------------------
            # SAVE APPROVED MAPPING
            # ----------------------------------------------

            st.session_state.approved_activity_wbs_mapping = (
                current_mapping.copy()
            )

            st.session_state.boq_wbs_mapping_approved = True

            # ----------------------------------------------
            # REMOVE PENDING ACTIVITIES
            # ----------------------------------------------

            st.session_state.pop(
                "pending_boq_activities",
                None
            )

            # ----------------------------------------------
            # CONFIRMATION
            # ----------------------------------------------

            st.success(
                f"{len(new_activity_rows)} activities "
                "successfully added to the Activity Register."
            )

            # ----------------------------------------------
            # REFRESH PAGE
            # ----------------------------------------------

            st.rerun()

            # ----------------------------------------------
            # FINAL APPEND
            # ----------------------------------------------

            if not new_activity_rows:

                st.error(
                    "No activities were available to approve."
                )

                return

            new_df = pd.DataFrame(
                new_activity_rows
            )

            st.session_state.activities = pd.concat(
                [
                    st.session_state.activities,
                    new_df
                ],
                ignore_index=True
            )

            # ----------------------------------------------
            # FINAL APPROVAL STATE
            # ----------------------------------------------

            st.session_state.approved_activity_wbs_mapping = (
                current_mapping.copy()
            )

            st.session_state.boq_wbs_mapping_approved = True

            # Pending data has now become authoritative.
            st.session_state.pop(
                "pending_boq_activities",
                None
            )

            st.success(
                f"✅ {len(new_df)} BOQ activities have been "
                "mapped to the approved WBS and added to the "
                "authoritative Activity Register."
            )

            st.rerun()


def render_activity_data():

    st.header("Step 2 — BOQ/WBS & Activity Data")

    st.write(
        "Create, import and manage the activities that will form the project schedule."
    )

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 AI WBS Builder",
        "➕ Add Activity",
        "📥 Import BOQ / WBS",
        "✏️ Edit Existing Data"
    ])

    # ==========================================================
    # TAB 1 — AI WBS BUILDER
    # ==========================================================

    with tab1:

        render_ai_wbs_builder()


    # ==========================================================
    # TAB 2 — ADD ACTIVITY
    # ==========================================================

    with tab2:

        st.subheader("Add Activity")

        col1, col2 = st.columns(2)

        with col1:

            # WBS selection
            if (
                st.session_state.get("wbs_approved", False)
                and "wbs" in st.session_state
                and not st.session_state.wbs.empty
            ):
                wbs_options = ["— Select WBS —"]
                wbs_display_map = {}

                for _, wbs_row in st.session_state.wbs.iterrows():
                    wbs_id = str(wbs_row["WBS ID"]).strip()
                    wbs_name = str(wbs_row["WBS Name"]).strip()

                    display = f"{wbs_id} — {wbs_name}"

                    wbs_options.append(display)
                    wbs_display_map[display] = wbs_id

                selected_wbs_display = st.selectbox(
                    "WBS / BOQ Code",
                    wbs_options,
                    key="add_activity_wbs"
                )

                wbs = (
                    wbs_display_map.get(selected_wbs_display, "")
                    if selected_wbs_display != "— Select WBS —"
                    else ""
                )

            else:
                wbs = st.text_input(
                    "WBS / BOQ Code",
                    placeholder="Example: 1.1"
                )

            activity_name = st.text_input(
                "Activity Name *",
                placeholder="Example: Excavation for foundation"
            )

            description = st.text_area(
                "Description",
                placeholder="Optional detailed description"
            )

        with col2:

            duration_source = st.radio(
                "Duration Source",
                [
                    "Specified in BOQ/WBS",
                    "Tentative Duration"
                ],
                horizontal=True
            )

            duration = st.number_input(
                "Duration (days)",
                min_value=1,
                value=1,
                step=1
            )

            relationship = st.selectbox(
                "Relationship",
                RELATIONSHIP_OPTIONS
            )

            predecessor_options = ["None"]

            if not st.session_state.activities.empty:
                predecessor_options += (
                    st.session_state.activities["ID"]
                    .astype(str)
                    .tolist()
                )

            predecessor = st.selectbox(
                "Predecessor",
                predecessor_options
            )

        col3, col4, col5 = st.columns(3)

        with col3:
            boq_qty = st.number_input(
                "BOQ Quantity",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        with col4:
            unit = st.text_input(
                "Unit",
                placeholder="m³, m², kg, No, L.S"
            )

        with col5:
            rate = st.number_input(
                "Rate",
                min_value=0.0,
                value=0.0,
                step=1.0
            )

        amount = boq_qty * rate

        st.caption(
            f"Calculated Amount: **{amount:,.2f}**"
        )

        if st.button(
            "Add Activity",
            type="primary",
            use_container_width=True
        ):

            if not wbs.strip():

                st.error(
                    "An activity cannot be added without an assigned WBS."
                )

            elif not activity_name.strip():
                st.error("Activity Name is required.")

            else:

                activity_id = create_activity_id()

                if predecessor == "None":
                    predecessor_value = ""
                else:
                    predecessor_value = predecessor

                activity_data = {
                    "ID": activity_id,
                    "WBS": wbs.strip(),
                    "Activity": activity_name.strip(),
                    "Description": description.strip(),
                    "Duration": int(duration),
                    "Duration Source": (
                        "BOQ/WBS"
                        if duration_source == "Specified in BOQ/WBS"
                        else "Tentative"
                    ),
                    "Relationship": relationship,
                    "Predecessor": predecessor_value,
                    "BOQ Qty": boq_qty,
                    "Unit": unit.strip(),
                    "Rate": rate,
                    "Amount": amount
                }

                add_activity(activity_data)

                st.success(
                    f"Activity {activity_id} added successfully."
                )

                st.rerun()

    # ==========================================================
    # TAB 3 — IMPORT BOQ / WBS
    # ==========================================================

    with tab3:

        st.subheader("Import Existing BOQ / WBS")

        if st.button(
            "📋 View Recommended BOQ / WBS Format",
            use_container_width=True
        ):
            st.session_state.show_boq_preview = True

        if st.session_state.get("show_boq_preview", False):
            render_boq_format_preview()

        st.write(
            "Upload your existing BOQ or WBS. "
            "The application will suggest how your columns should be mapped."
        )

        uploaded_file = st.file_uploader(
            "Upload Excel or CSV",
            type=["xlsx", "xls", "csv"],
            help=(
                "Your existing BOQ does not need to exactly match "
                "the recommended format."
            )
        )

        # ==========================================================
        # LOAD NEW OR PREVIOUSLY IMPORTED BOQ
        # ==========================================================

        df = None
        current_file_name = None

        # ----------------------------------------------------------
        # NEW FILE UPLOAD
        # ----------------------------------------------------------

        if uploaded_file is not None:

            try:

                file_name = uploaded_file.name.lower()

                if file_name.endswith(".csv"):

                    df = pd.read_csv(uploaded_file)

                else:

                    df = pd.read_excel(uploaded_file)

                df = normalize_columns(df)

                st.session_state.imported_boq_df = (
                    df.copy()
                )

                st.session_state.imported_boq_filename = (
                    uploaded_file.name
                )

                current_file_name = uploaded_file.name

            except Exception as e:

                st.error(
                    f"Unable to read or process the uploaded file: {e}"
                )

                return

        # ----------------------------------------------------------
        # RESTORE PREVIOUSLY IMPORTED BOQ
        # ----------------------------------------------------------

        elif (
            "imported_boq_df" in st.session_state
            and st.session_state.imported_boq_df is not None
            and not st.session_state.imported_boq_df.empty
        ):

            df = st.session_state.imported_boq_df.copy()

            current_file_name = (
                st.session_state.get(
                    "imported_boq_filename",
                    "Previously imported BOQ"
                )
            )

        # ----------------------------------------------------------
        # PROCESS BOQ
        # ----------------------------------------------------------

        if df is not None:

            try:

                st.success(
                    f"File loaded successfully: {current_file_name}"
                )

                if df.empty:

                    st.warning(
                        "The uploaded file contains no data."
                    )

                else:

                    st.write("### Preview of Original BOQ")

                    st.dataframe(
                        df.head(10),
                        use_container_width=True,
                        hide_index=True
                    )

                    columns = list(df.columns)

                    st.write("### 🔗 Map Your BOQ Columns")

                    st.caption(
                        "The application suggests mappings, but you can "
                        "change them manually."
                    )

                    # --------------------------------------------------
                    # COLUMN SUGGESTIONS
                    # --------------------------------------------------

                    wbs_guess = guess_column(
                        columns,
                        [
                            "wbs",
                            "boq code",
                            "item code",
                            "item no",
                            "code"
                        ]
                    )

                    activity_guess = guess_column(
                        columns,
                        [
                            "description",
                            "description of work",
                            "item description",
                            "work description",
                            "particulars",
                            "activity",
                            "activity name",
                            "work item",
                            "scope of work"
                        ]
                    )

                    unit_guess = guess_column(
                        columns,
                        [
                            "unit",
                            "uom",
                            "measurement unit"
                        ]
                    )

                    quantity_guess = guess_column(
                        columns,
                        [
                            "quantity",
                            "qty",
                            "estimated quantity",
                            "boq quantity"
                        ]
                    )

                    rate_guess = guess_column(
                        columns,
                        [
                            "rate",
                            "unit rate",
                            "price"
                        ]
                    )

                    amount_guess = guess_column(
                        columns,
                        [
                            "amount",
                            "total amount",
                            "total cost",
                            "value"
                        ]
                    )

                    duration_guess = guess_column(
                        columns,
                        [
                            "duration",
                            "days",
                            "duration days",
                            "time"
                        ]
                    )

                    # --------------------------------------------------
                    # MAPPING
                    # --------------------------------------------------

                    none_option = "— Do not import —"

                    def mapping_options():

                        return [none_option] + columns

                    map_col1, map_col2 = st.columns(2)

                    with map_col1:

                        activity_col = st.selectbox(
                            "Activity / Description *",
                            mapping_options(),
                            index=(
                                columns.index(activity_guess) + 1
                                if activity_guess in columns
                                else 0
                            )
                        )

                        unit_col = st.selectbox(
                            "Unit",
                            mapping_options(),
                            index=(
                                columns.index(unit_guess) + 1
                                if unit_guess in columns
                                else 0
                            )
                        )

                        quantity_col = st.selectbox(
                            "Quantity",
                            mapping_options(),
                            index=(
                                columns.index(quantity_guess) + 1
                                if quantity_guess in columns
                                else 0
                            )
                        )

                        wbs_col = st.selectbox(
                            "WBS / BOQ Code",
                            mapping_options(),
                            index=(
                                columns.index(wbs_guess) + 1
                                if wbs_guess in columns
                                else 0
                            )
                        )

                    with map_col2:

                        duration_col = st.selectbox(
                            "Duration",
                            mapping_options(),
                            index=(
                                columns.index(duration_guess) + 1
                                if duration_guess in columns
                                else 0
                            )
                        )

                        rate_col = st.selectbox(
                            "Rate",
                            mapping_options(),
                            index=(
                                columns.index(rate_guess) + 1
                                if rate_guess in columns
                                else 0
                            )
                        )

                        amount_col = st.selectbox(
                            "Amount",
                            mapping_options(),
                            index=(
                                columns.index(amount_guess) + 1
                                if amount_guess in columns
                                else 0
                            )
                        )

                    st.divider()

                    # --------------------------------------------------
                    # WBS INTELLIGENCE
                    # --------------------------------------------------

                    has_structured_wbs = detect_structured_wbs(
                        df,
                        wbs_col
                    )

                    if wbs_col != none_option:

                        if has_structured_wbs:

                            st.success(
                                "✅ A structured WBS was detected in the imported file. "
                                "The existing WBS will be preserved."
                            )

                        else:

                            st.info(
                                "ℹ️ A WBS/code column was selected, but it does not "
                                "appear to contain a structured hierarchical WBS. "
                                "AI can propose a WBS from the imported activities."
                            )

                    else:

                        st.info(
                            "ℹ️ No WBS column was selected. "
                            "AI can propose a WBS from the imported activities."
                        )

                    # --------------------------------------------------
                    # VALIDATE ACTIVITY COLUMN
                    # --------------------------------------------------

                    if activity_col == none_option:

                        st.error(
                            "Please select a column containing the "
                            "BOQ activity / description."
                        )

                    else:

                        st.write("### Import Preview")

                        preview_rows = []

                        for _, row in df.head(10).iterrows():

                            raw_activity = row[activity_col]

                            if pd.isna(raw_activity):
                                activity_text = ""
                            else:
                                # Preserve original BOQ wording
                                activity_text = str(raw_activity)

                            if wbs_col != none_option:
                                raw_wbs = row[wbs_col]

                                if pd.isna(raw_wbs):
                                    wbs_value = ""
                                else:
                                    wbs_value = str(raw_wbs)
                            else:
                                wbs_value = ""

                            if unit_col != none_option:
                                raw_unit = row[unit_col]

                                if pd.isna(raw_unit):
                                    unit_value = ""
                                else:
                                    unit_value = str(raw_unit)
                            else:
                                unit_value = ""

                            if quantity_col != none_option:
                                quantity_value = parse_number(
                                    row[quantity_col]
                                )
                            else:
                                quantity_value = None

                            if rate_col != none_option:
                                rate_value = parse_number(
                                    row[rate_col]
                                )
                            else:
                                rate_value = None

                            if amount_col != none_option:
                                amount_value = parse_number(
                                    row[amount_col]
                                )
                            else:
                                amount_value = None

                            if duration_col != none_option:
                                duration_value = parse_duration(
                                    row[duration_col]
                                )
                            else:
                                duration_value = None

                            duration_source = (
                                "BOQ/WBS"
                                if duration_value is not None
                                else "Tentative"
                            )

                            if duration_value is None:
                                duration_value = 1

                            preview_rows.append({
                                "Activity": activity_text,
                                "WBS": wbs_value,
                                "Unit": unit_value,
                                "BOQ Qty": quantity_value,
                                "Duration": duration_value,
                                "Duration Source": duration_source,
                                "Rate": rate_value,
                                "Amount": amount_value
                            })

                        preview_df = pd.DataFrame(preview_rows)

                        st.dataframe(
                            preview_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        st.info(
                            "The Activity text shown above is imported "
                            "**exactly as it appears in your BOQ**. "
                            "The application does not rewrite or shorten it."
                        )

                        # --------------------------------------------------
                        # AI WBS GENERATION FROM BOQ
                        # --------------------------------------------------

                        if not has_structured_wbs:

                            st.divider()

                            st.subheader("🤖 Generate WBS from BOQ")

                            st.caption(
                                "No structured WBS was detected. AI can propose a "
                                "construction WBS from the imported activity descriptions. "
                                "You will review and approve it before it becomes the project WBS."
                            )

                            import_wbs_api_key = st.text_input(
                                "Groq API Key",
                                type="password",
                                key="import_boq_wbs_api_key"
                            )

                            import_model_options = {
                                "gpt-oss-20b": "openai/gpt-oss-20b",
                                "gpt-oss-120b": "openai/gpt-oss-120b",
                            }

                            import_model_name = st.selectbox(
                                "AI Model",
                                list(
                                    import_model_options.keys()
                                ),
                                key="import_boq_wbs_model"
                            )

                            import_model = import_model_options[
                                import_model_name
                            ]

                            if st.button(
                                "🤖 Generate WBS from BOQ",
                                use_container_width=True
                            ):

                                if activity_col == none_option:

                                    st.error(
                                        "Select the Activity / Description column first."
                                    )

                                elif not import_wbs_api_key.strip():

                                    st.error(
                                        "Please enter your Groq API key."
                                    )

                                else:

                                    boq_activities = []

                                    activity_index = 1

                                    for _, boq_row in df.iterrows():

                                        raw_activity = boq_row[
                                            activity_col
                                        ]

                                        if pd.isna(raw_activity):
                                            continue

                                        activity_text = str(
                                            raw_activity
                                        ).strip()

                                        if not activity_text:
                                            continue

                                        boq_activities.append(
                                            {
                                                "Activity Index": activity_index,
                                                "Activity": activity_text,
                                            }
                                        )

                                        activity_index += 1

                                    # --------------------------------------------------
                                    # PRESERVE BOQ ACTIVITY CONTEXT
                                    # --------------------------------------------------

                                    st.session_state.imported_boq_activities = (
                                        boq_activities.copy()
                                    )

                                    # --------------------------------------------------
                                    # IF THE USER HAS NOT YET CLICKED
                                    # "IMPORT ACTIVITIES", STAGE THE FULL
                                    # BOQ NOW.
                                    #
                                    # This allows:
                                    #
                                    # BOQ
                                    # ↓
                                    # Generate WBS
                                    # ↓
                                    # Approve WBS
                                    # ↓
                                    # Activity → WBS Mapping
                                    #
                                    # without requiring the BOQ to be
                                    # uploaded again.
                                    # --------------------------------------------------

                                    # ==================================================
                                    # ALWAYS STAGE THE CURRENT BOQ
                                    # ==================================================
                                    #
                                    # The currently displayed/imported BOQ is the
                                    # authoritative source for this WBS-generation
                                    # operation.
                                    #
                                    # Do not reuse an older pending BOQ.

                                    imported_rows = []

                                    existing_count = len(
                                        st.session_state.activities
                                    )

                                    for _, boq_row in df.iterrows():

                                        raw_activity = boq_row[
                                            activity_col
                                        ]

                                        if pd.isna(raw_activity):
                                            continue

                                        activity_text = str(
                                            raw_activity
                                        )

                                        if not activity_text.strip():
                                            continue

                                        # ------------------------------
                                        # WBS
                                        # ------------------------------

                                        if wbs_col != none_option:

                                            raw_wbs = boq_row[wbs_col]

                                            if pd.isna(raw_wbs):
                                                wbs_value = ""
                                            else:
                                                wbs_value = str(raw_wbs)

                                        else:

                                            wbs_value = ""

                                        # ------------------------------
                                        # UNIT
                                        # ------------------------------

                                        if unit_col != none_option:

                                            raw_unit = boq_row[unit_col]

                                            if pd.isna(raw_unit):
                                                unit_value = ""
                                            else:
                                                unit_value = str(raw_unit)

                                        else:

                                            unit_value = ""

                                        # ------------------------------
                                        # QUANTITY
                                        # ------------------------------

                                        if quantity_col != none_option:

                                            quantity_value = parse_number(
                                                boq_row[quantity_col]
                                            )

                                        else:

                                            quantity_value = None

                                        # ------------------------------
                                        # RATE
                                        # ------------------------------

                                        if rate_col != none_option:

                                            rate_value = parse_number(
                                                boq_row[rate_col]
                                            )

                                        else:

                                            rate_value = None

                                        # ------------------------------
                                        # AMOUNT
                                        # ------------------------------

                                        if amount_col != none_option:

                                            amount_value = parse_number(
                                                boq_row[amount_col]
                                            )

                                        else:

                                            amount_value = None

                                        # ------------------------------
                                        # DURATION
                                        # ------------------------------

                                        if duration_col != none_option:

                                            duration_value = parse_duration(
                                                boq_row[duration_col]
                                            )

                                        else:

                                            duration_value = None

                                        if duration_value is None:

                                            duration_value = 1
                                            duration_source = "Tentative"

                                        else:

                                            duration_source = "BOQ/WBS"

                                        activity_id = (
                                            f"A{existing_count + len(imported_rows) + 1:03d}"
                                        )

                                        imported_rows.append({

                                            "ID":
                                                activity_id,

                                            "WBS":
                                                wbs_value,

                                            "Activity":
                                                activity_text,

                                            "Description":
                                                "",

                                            "Duration":
                                                duration_value,

                                            "Duration Source":
                                                duration_source,

                                            "Relationship":
                                                "No Predecessor",

                                            "Predecessor":
                                                "",

                                            "BOQ Qty":
                                                quantity_value,

                                            "Unit":
                                                unit_value,

                                            "Rate":
                                                rate_value,

                                            "Amount":
                                                amount_value
                                        })

                                    if imported_rows:

                                        stage_pending_boq_activities(
                                            imported_rows
                                        )

                                    if not boq_activities:

                                        st.error(
                                            "No usable activity descriptions were found "
                                            "to generate a WBS."
                                        )

                                    else:

                                        project_name = (
                                            st.session_state.project
                                            .get("name", "")
                                        )

                                        boq_scope = "\n".join(
                                            f"- {item['Activity']}"
                                            for item in boq_activities
                                        )

                                        ai_scope = f"""
                        Create a construction WBS based on the following
                        imported BOQ/activity descriptions.

                        PROJECT:
                        {project_name}

                        IMPORTED BOQ ACTIVITIES:
                        {boq_scope}
                        """

                                        with st.spinner(
                                            "AI is analyzing the BOQ and proposing a WBS..."
                                        ):

                                            try:

                                                wbs_suggestions = (
                                                    get_ai_wbs_suggestions(
                                                        project_name,
                                                        ai_scope,
                                                        import_wbs_api_key.strip(),
                                                        import_model
                                                    )
                                                )

                                                st.session_state.ai_wbs_data = (
                                                    wbs_suggestions.copy()
                                                )

                                                st.session_state.ai_wbs_original = (
                                                    wbs_suggestions.copy()
                                                )

                                                # --------------------------------------------------
                                                # NEW WBS IS NOT YET AUTHORITATIVE
                                                # --------------------------------------------------

                                                st.session_state.ai_wbs_approved = False

                                                st.session_state.wbs_approved = False

                                                # Remove any previous authoritative WBS.

                                                st.session_state.pop(
                                                    "wbs",
                                                    None
                                                )

                                                # Remove any previous Activity → WBS mapping.

                                                st.session_state.pop(
                                                    "ai_activity_wbs_mapping",
                                                    None
                                                )

                                                st.session_state.pop(
                                                    "approved_activity_wbs_mapping",
                                                    None
                                                )

                                                st.session_state.pop(
                                                    "boq_wbs_mapping_approved",
                                                    None
                                                )

                                                st.success(
                                                    "AI WBS generated from the BOQ. "
                                                    "Open the AI WBS Builder tab to review it."
                                                )

                                                st.rerun()

                                            except Exception as exc:

                                                st.error(
                                                    "AI WBS generation failed."
                                                )

                                                st.exception(exc)






                        # --------------------------------------------------
                        # MISSING DURATION WARNING
                        # --------------------------------------------------

                        if duration_col == none_option:

                            st.warning(
                                "No duration column was selected. "
                                "Imported activities will receive a "
                                "temporary 1-day duration and be marked "
                                "'Tentative'. You will provide the "
                                "appropriate duration before scheduling."
                            )

                        elif (
                            "Duration Source" in preview_df.columns
                            and (
                                preview_df["Duration Source"]
                                == "Tentative"
                            ).any()
                        ):

                            st.warning(
                                "Some activities do not contain a "
                                "usable duration. Those activities will "
                                "be marked 'Tentative'."
                            )

                        # --------------------------------------------------
                        # IMPORT BUTTON
                        # --------------------------------------------------

                        if st.button(
                            "⬇️ Import Activities",
                            type="primary",
                            use_container_width=True
                        ):

                            imported_rows = []

                            existing_count = len(
                                st.session_state.activities
                            )

                            for _, row in df.iterrows():

                                # --------------------------------------------------
                                # Activity
                                # --------------------------------------------------

                                raw_activity = row[activity_col]

                                if pd.isna(raw_activity):
                                    activity_text = ""
                                else:
                                    # IMPORTANT:
                                    # Preserve original BOQ wording exactly.
                                    activity_text = str(raw_activity)

                                if not activity_text.strip():
                                    continue

                                # --------------------------------------------------
                                # WBS
                                # --------------------------------------------------

                                if wbs_col != none_option:

                                    raw_wbs = row[wbs_col]

                                    if pd.isna(raw_wbs):
                                        wbs_value = ""
                                    else:
                                        wbs_value = str(raw_wbs)

                                else:

                                    wbs_value = ""

                                # --------------------------------------------------
                                # Unit
                                # --------------------------------------------------

                                if unit_col != none_option:

                                    raw_unit = row[unit_col]

                                    if pd.isna(raw_unit):
                                        unit_value = ""
                                    else:
                                        unit_value = str(raw_unit)

                                else:

                                    unit_value = ""

                                # --------------------------------------------------
                                # Quantity
                                # --------------------------------------------------

                                if quantity_col != none_option:

                                    quantity_value = parse_number(
                                        row[quantity_col]
                                    )

                                else:

                                    quantity_value = None

                                # --------------------------------------------------
                                # Rate
                                # --------------------------------------------------

                                if rate_col != none_option:

                                    rate_value = parse_number(
                                        row[rate_col]
                                    )

                                else:

                                    rate_value = None

                                # --------------------------------------------------
                                # Amount
                                # --------------------------------------------------

                                if amount_col != none_option:

                                    amount_value = parse_number(
                                        row[amount_col]
                                    )

                                else:

                                    amount_value = None

                                # --------------------------------------------------
                                # Duration
                                # --------------------------------------------------

                                if duration_col != none_option:

                                    duration_value = parse_duration(
                                        row[duration_col]
                                    )

                                else:

                                    duration_value = None

                                if duration_value is None:

                                    duration_value = 1
                                    duration_source = "Tentative"

                                else:

                                    duration_source = "BOQ/WBS"

                                # --------------------------------------------------
                                # Build imported activity record
                                # --------------------------------------------------

                                activity_id = (
                                    f"A{existing_count + len(imported_rows) + 1:03d}"
                                )

                                imported_rows.append({

                                    "ID":
                                        activity_id,

                                    "WBS":
                                        wbs_value,

                                    "Activity":
                                        activity_text,

                                    "Description":
                                        "",

                                    "Duration":
                                        duration_value,

                                    "Duration Source":
                                        duration_source,

                                    "Relationship":
                                        "No Predecessor",

                                    "Predecessor":
                                        "",

                                    "BOQ Qty":
                                        quantity_value,

                                    "Unit":
                                        unit_value,

                                    "Rate":
                                        rate_value,

                                    "Amount":
                                        amount_value
                                })

                            # ======================================================
                            # NOTHING TO IMPORT
                            # ======================================================

                            if not imported_rows:

                                st.warning(
                                    "No usable activities were found "
                                    "in the selected column."
                                )

                            # ======================================================
                            # DETERMINE WHETHER ALL ACTIVITIES HAVE WBS
                            # ======================================================
                            #
                            # The authoritative Activity Register must NEVER
                            # receive an activity without an assigned WBS.
                            #
                            # Therefore the decision is based on the actual
                            # imported activity rows — NOT merely on whether
                            # the WBS column looks hierarchical.
                            # ======================================================

                            all_activities_have_wbs = all(
                                str(
                                    row.get("WBS", "")
                                ).strip() != ""
                                for row in imported_rows
                            )

                            # ======================================================
                            # ALL ACTIVITIES HAVE WBS
                            # ======================================================

                            if all_activities_have_wbs:

                                # Every activity has an assigned WBS.
                                #
                                # These activities can safely enter the
                                # authoritative Activity Register.

                                new_df = pd.DataFrame(
                                    imported_rows
                                )

                                # Final safety check before append.
                                new_df["WBS"] = (
                                    new_df["WBS"]
                                    .fillna("")
                                    .astype(str)
                                    .str.strip()
                                )

                                new_df = new_df[
                                    new_df["WBS"] != ""
                                ].copy()

                                if new_df.empty:

                                    st.error(
                                        "No activities with assigned WBS "
                                        "are available for the Activity Register."
                                    )

                                else:

                                    st.session_state.activities = pd.concat(
                                        [
                                            st.session_state.activities,
                                            new_df
                                        ],
                                        ignore_index=True
                                    )

                                    st.success(
                                        f"{len(new_df)} activities imported "
                                        "successfully with assigned WBS."
                                    )

                                    st.rerun()

                            # ======================================================
                            # ONE OR MORE ACTIVITIES HAVE NO WBS
                            # ======================================================

                            else:

                                # IMPORTANT:
                                #
                                # DO NOT add ANY of these activities directly
                                # to the authoritative Activity Register.
                                #
                                # The complete BOQ is staged until every
                                # activity receives a reviewed and approved WBS.

                                stage_pending_boq_activities(
                                    imported_rows
                                )

                                st.warning(
                                    f"{len(imported_rows)} BOQ activities "
                                    "have been staged because one or more "
                                    "activities do not have an assigned WBS."
                                )

                                st.info(
                                    "These activities have NOT been added to "
                                    "the authoritative Activity Register. "
                                    "Generate and approve the project WBS, "
                                    "then review and approve the Activity → "
                                    "WBS mapping."
                                )

                                st.rerun()

            except Exception as e:

                st.error(
                    f"Unable to read or process the uploaded file: {e}"
                )

        # ==========================================================
        # PENDING BOQ → ACTIVITY / WBS MAPPING
        # ==========================================================

        render_activity_wbs_mapping()


    # ==========================================================
    # TAB 4 — EDIT EXISTING DATA
    # ==========================================================

    with tab4:

        st.subheader("Edit Existing Activity Data")

        if st.session_state.activities.empty:

            st.info(
                "No activities have been added or imported yet."
            )

        else:

            current_df = st.session_state.activities.copy()

            # --------------------------------------------------
            # BUILD DISPLAY NAMES FOR PREDECESSOR DROPDOWN
            # --------------------------------------------------

            predecessor_options = ["None 🔍"]

            activity_display_map = {}

            for _, activity_row in current_df.iterrows():

                activity_id = str(
                    activity_row["ID"]
                ).strip()

                activity_name = str(
                    activity_row["Activity"]
                ).strip()

                # Normal display:
                # PCC below footing
                #
                # If duplicate activity names exist, append ID
                # internally to keep the selection unambiguous.

                if activity_name in activity_display_map:

                    display_name = (
                        f"{activity_name} [{activity_id}]"
                    )

                else:

                    display_name = activity_name

                activity_display_map[display_name] = activity_id

                predecessor_options.append(
                    display_name
                )

            # --------------------------------------------------
            # CONVERT STORED IDs INTO DISPLAY NAMES
            # --------------------------------------------------

            display_df = current_df.copy()

            predecessor_display = []

            for _, activity_row in display_df.iterrows():

                predecessor_value = activity_row.get(
                    "Predecessor",
                    ""
                )

                if (
                    predecessor_value is None
                    or pd.isna(predecessor_value)
                    or str(predecessor_value).strip() == ""
                ):

                    predecessor_display.append(
                        "None 🔍"
                    )

                    continue

                predecessor_value = str(
                    predecessor_value
                ).strip()

                # ----------------------------------------------
                # Stored predecessor is an Activity ID
                # ----------------------------------------------

                matching_id = current_df[
                    current_df["ID"].astype(str).str.strip()
                    == predecessor_value
                ]

                if not matching_id.empty:

                    predecessor_activity = str(
                        matching_id.iloc[0]["Activity"]
                    ).strip()

                    # Check if duplicate activity name exists
                    duplicate_count = (
                        current_df["Activity"]
                        .astype(str)
                        .str.strip()
                        .eq(predecessor_activity)
                        .sum()
                    )

                    if duplicate_count > 1:

                        predecessor_display.append(
                            f"{predecessor_activity} "
                            f"[{predecessor_value}]"
                        )

                    else:

                        predecessor_display.append(
                            predecessor_activity
                        )

                    continue

                # ----------------------------------------------
                # Legacy stored activity name
                # ----------------------------------------------

                matching_name = current_df[
                    current_df["Activity"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    == predecessor_value.lower()
                ]

                if not matching_name.empty:

                    predecessor_display.append(
                        str(
                            matching_name.iloc[0]["Activity"]
                        ).strip()
                    )

                else:

                    # Unknown legacy value
                    predecessor_display.append(
                        predecessor_value
                    )

            display_df["Predecessor"] = predecessor_display

            # --------------------------------------------------
            # EDITABLE ACTIVITY TABLE
            # --------------------------------------------------

            st.info(
                "💡 The predecessor is optional. "
                "Click the predecessor cell and start typing "
                "the activity name to search. Select the required "
                "activity from the filtered list."
            )

            edited_df = st.data_editor(

                display_df,

                use_container_width=True,

                hide_index=True,

                disabled=["ID"],

                column_config={

                    "ID": st.column_config.TextColumn(
                        "ID",
                        disabled=True
                    ),

                    "WBS": st.column_config.TextColumn(
                        "WBS / BOQ Code"
                    ),

                    "Activity": st.column_config.TextColumn(
                        "Activity"
                    ),

                    "Description": st.column_config.TextColumn(
                        "Description"
                    ),

                    "Duration": st.column_config.NumberColumn(
                        "Duration",
                        min_value=1,
                        step=1
                    ),

                    "Duration Source": st.column_config.TextColumn(
                        "Duration Source",
                        disabled=True
                    ),

                    "Relationship": st.column_config.SelectboxColumn(
                        "Relationship",
                        options=RELATIONSHIP_OPTIONS,
                        required=True
                    ),

                    "Predecessor": st.column_config.SelectboxColumn(
                        "Predecessor",
                        options=predecessor_options,
                        required=False,
                        help=(
                            "Optional. Type part of an activity "
                            "name to search and select a predecessor."
                        )
                    ),

                    "BOQ Qty": st.column_config.NumberColumn(
                        "BOQ Qty",
                        min_value=0.0
                    ),

                    "Unit": st.column_config.TextColumn(
                        "Unit"
                    ),

                    "Rate": st.column_config.NumberColumn(
                        "Rate",
                        min_value=0.0
                    ),

                    "Amount": st.column_config.NumberColumn(
                        "Amount",
                        min_value=0.0
                    )
                },

                key="activity_editor"
            )

            # --------------------------------------------------
            # SAVE CHANGES
            # --------------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "💾 Save Changes",
                    type="primary",
                    use_container_width=True
                ):

                    saved_df = edited_df.copy()

                    converted_predecessors = []

                    conversion_errors = []

                    for row_number, predecessor_value in enumerate(
                        saved_df["Predecessor"],
                        start=1
                    ):

                        # --------------------------------------
                        # No predecessor
                        # --------------------------------------

                        if (
                            predecessor_value is None
                            or pd.isna(predecessor_value)
                            or str(predecessor_value).strip()
                            in ["", "None 🔍"]
                        ):

                            converted_predecessors.append("")

                            continue

                        predecessor_text = str(
                            predecessor_value
                        ).strip()

                        # --------------------------------------
                        # Direct display-name → ID conversion
                        # --------------------------------------

                        if predecessor_text in activity_display_map:

                            predecessor_id = (
                                activity_display_map[
                                    predecessor_text
                                ]
                            )

                            converted_predecessors.append(
                                predecessor_id
                            )

                            continue

                        # --------------------------------------
                        # Handle duplicate activity display
                        # Example:
                        # RCC columns [A006]
                        # --------------------------------------

                        if "[" in predecessor_text and \
                           predecessor_text.endswith("]"):

                            possible_id = (
                                predecessor_text
                                .rsplit("[", 1)[-1]
                                .replace("]", "")
                                .strip()
                            )

                            matching_id = current_df[
                                current_df["ID"]
                                .astype(str)
                                .str.strip()
                                == possible_id
                            ]

                            if not matching_id.empty:

                                converted_predecessors.append(
                                    possible_id
                                )

                                continue

                        # --------------------------------------
                        # Legacy Activity ID
                        # --------------------------------------

                        matching_id = current_df[
                            current_df["ID"]
                            .astype(str)
                            .str.strip()
                            == predecessor_text
                        ]

                        if not matching_id.empty:

                            converted_predecessors.append(
                                predecessor_text
                            )

                            continue

                        # --------------------------------------
                        # Legacy Activity Name
                        # --------------------------------------

                        matching_name = current_df[
                            current_df["Activity"]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            == predecessor_text.lower()
                        ]

                        if len(matching_name) == 1:

                            converted_predecessors.append(
                                matching_name.iloc[0]["ID"]
                            )

                            continue

                        # --------------------------------------
                        # Could not resolve
                        # --------------------------------------

                        conversion_errors.append(
                            f"Row {row_number}: "
                            f"Unable to identify predecessor "
                            f"'{predecessor_text}'."
                        )

                        converted_predecessors.append(
                            predecessor_text
                        )

                    # --------------------------------------------------
                    # STOP SAVE IF PREDECESSOR CANNOT BE RESOLVED
                    # --------------------------------------------------

                    if conversion_errors:

                        st.error(
                            "Some predecessor selections could not "
                            "be resolved:"
                        )

                        for error in conversion_errors:

                            st.markdown(
                                f"• {error}"
                            )

                    else:

                        saved_df["Predecessor"] = (
                            converted_predecessors
                        )

                        # ----------------------------------------------
                        # PREVENT SELF-PREDECESSOR
                        # ----------------------------------------------

                        invalid_self = []

                        for _, activity_row in saved_df.iterrows():

                            if (
                                str(
                                    activity_row["Predecessor"]
                                ).strip()
                                ==
                                str(
                                    activity_row["ID"]
                                ).strip()
                            ):

                                invalid_self.append(
                                    activity_row["ID"]
                                )

                        if invalid_self:

                            st.error(
                                "An activity cannot be its own "
                                "predecessor: "
                                + ", ".join(invalid_self)
                            )

                        else:

                            st.session_state.activities = (
                                saved_df.copy()
                            )

                            st.success(
                                "Activity data updated successfully."
                            )

                            st.rerun()

            # --------------------------------------------------
            # DELETE ACTIVITY
            # --------------------------------------------------

            with col2:

                delete_options = (
                    st.session_state.activities["ID"]
                    .astype(str)
                    .tolist()
                )

                delete_id = st.selectbox(
                    "Select Activity to Delete",
                    delete_options,
                    key="delete_activity_id"
                )

                if st.button(
                    "🗑️ Delete Selected Activity",
                    use_container_width=True
                ):

                    delete_index = (
                        st.session_state.activities
                        .index[
                            st.session_state.activities["ID"]
                            == delete_id
                        ]
                    )

                    if len(delete_index) > 0:

                        delete_activity(
                            delete_index[0]
                        )

                        st.success(
                            f"Activity {delete_id} deleted."
                        )

                        st.rerun()

    # ==========================================================
    # ACTIVITY SUMMARY
    # ==========================================================

    st.divider()

    st.subheader("Activity Register")

    # ==========================================================
    # AUTHORITATIVE ACTIVITY REGISTER SAFETY CHECK
    # ==========================================================
    #
    # Activity Register may contain ONLY activities that
    # have an assigned WBS.
    #
    # Pending / unmapped BOQ activities belong in:
    #     st.session_state.pending_boq_activities
    #
    # They must never exist in the authoritative register.
    # ==========================================================

    activities = st.session_state.activities.copy()

    if not activities.empty:

        activities["WBS"] = (
            activities["WBS"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # Remove any legacy/bad rows without WBS.
        activities = activities[
            activities["WBS"] != ""
        ].copy()

        # Write cleaned register back to session state.
        if len(activities) != len(
            st.session_state.activities
        ):

            st.session_state.activities = (
                activities.copy()
            )

    # ==========================================================
    # DISPLAY AUTHORITATIVE ACTIVITY REGISTER
    # ==========================================================

    if activities.empty:

        st.info(
            "No activities have been added or approved yet."
        )

    else:

        st.caption(
            f"{len(activities)} activities in the authoritative Activity Register."
        )

        st.dataframe(
            activities,
            use_container_width=True,
            hide_index=True
        )

        # ==========================================================
        # PROCEED TO STEP 3
        # ==========================================================

        st.divider()

        if st.button(
            "➡️ Proceed to Step 3 — Planning & Scheduling",
            type="primary",
            use_container_width=True
        ):
            st.session_state.current_step = 3
            st.rerun()
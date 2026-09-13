import json

import pandas as pd
from openai import OpenAI


# ==========================================================
# CONSTANTS
# ==========================================================

RELATIONSHIP_OPTIONS = [
    "No Predecessor",
    "Finish-to-Start (FS)",
    "Start-to-Start (SS)",
    "Finish-to-Finish (FF)",
    "Start-to-Finish (SF)",
]


# ==========================================================
# AI SCHEDULE BUILDER
# ==========================================================

def get_ai_schedule_suggestions(
    activities,
    api_key,
    model="openai/gpt-oss-20b",
):
    """
    Use an LLM to propose construction schedule logic.

    The AI proposes:
        - predecessor
        - relationship
        - confidence
        - reason

    The AI does NOT calculate dates.

    Returns a DataFrame compatible with the existing
    AI relationship editor.
    """

    if activities is None or activities.empty:
        return pd.DataFrame()

    if not api_key:
        raise ValueError(
            "Groq API key is required."
        )

    # ------------------------------------------------------
    # PREPARE COMPACT ACTIVITY CONTEXT
    # ------------------------------------------------------

    required_columns = [
        "ID",
        "WBS",
        "Activity",
        "Duration",
        "Duration Source",
    ]

    available_columns = [
        column
        for column in required_columns
        if column in activities.columns
    ]

    context_data = activities[
        available_columns
    ].copy()

    context_data = context_data.fillna("")

    records = context_data.to_dict(
        orient="records"
    )

    # ------------------------------------------------------
    # CREATE COMPACT ACTIVITY LIST
    # ------------------------------------------------------

    activity_lines = []

    for record in records:

        activity_lines.append(
            "ID: {id} | WBS: {wbs} | "
            "Activity: {activity} | "
            "Duration: {duration} | "
            "Duration Source: {duration_source}".format(
                id=record.get("ID", ""),
                wbs=record.get("WBS", ""),
                activity=record.get("Activity", ""),
                duration=record.get("Duration", ""),
                duration_source=record.get(
                    "Duration Source",
                    ""
                ),
            )
        )

    activity_context = "\n".join(
        activity_lines
    )

    # ------------------------------------------------------
    # SYSTEM INSTRUCTIONS
    # ------------------------------------------------------

    system_prompt = """
You are an expert construction planning and scheduling
engineer.

Your task is to propose logical predecessor relationships
for construction activities.

You are NOT calculating project dates.

You are NOT creating a complete dated schedule.

You are only proposing schedule logic that a human planner
will review before the application calculates the schedule.

IMPORTANT RULES:

1. Use ONLY activities provided in the input.

2. Every predecessor must be an existing Activity ID.

3. Never invent an Activity ID.

4. An activity may have no predecessor when it can logically
   start independently.

5. Prefer Finish-to-Start (FS) when a normal sequential
   construction dependency exists.

6. Use Start-to-Start (SS), Finish-to-Finish (FF), or
   Start-to-Finish (SF) only when there is a clear
   construction-planning reason.

7. Do not create unnecessary dependencies merely because
   activities appear in the same WBS.

8. Consider normal construction sequencing, including:
   site preparation, excavation, foundations, PCC, RCC,
   reinforcement, formwork, masonry, roofing, waterproofing,
   plaster, flooring, doors, windows, plumbing and electrical
   works.

9. Parallel activities should remain independent when there
   is no logical dependency.

10. Do not invent resources, crews, productivity rates,
    equipment, working hours, weather conditions or site
    constraints.

11. Duration is provided for context only. Do not change it.

12. Do not calculate Planned Start or Planned Finish.

13. Confidence must be one of:
    High
    Medium
    Low

14. Reason must be extremely short: maximum 8 words.

15. The first activity does NOT automatically have to be the
    project starting activity. Decide based on the activities.

16. Avoid circular dependencies.

17. Return ONLY valid JSON.

The JSON must contain an array called "activities".

Each item must contain exactly these fields:

{
    "ID": "activity ID",
    "Predecessor": "predecessor ID or empty string",
    "Relationship": "relationship",
    "Confidence": "High | Medium | Low",
    "Reason": "maximum 8 words"
}
"""

    user_prompt = f"""
Analyze the following construction activities and propose
logical schedule relationships.

ACTIVITIES:

{activity_context}

Return one JSON record for every activity.

Do not omit activities.
Do not add activities.
Do not calculate dates.
"""

    # ------------------------------------------------------
    # CONNECT TO GROQ
    # ------------------------------------------------------

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    # ------------------------------------------------------
    # CALL AI
    # ------------------------------------------------------

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        response_format={
            "type": "json_object"
        },
        max_tokens=6000,
    )

    # ------------------------------------------------------
    # EXTRACT RESPONSE
    # ------------------------------------------------------

    response_text = response.choices[0].message.content.strip()

    # ------------------------------------------------------
    # REMOVE MARKDOWN CODE FENCES IF PRESENT
    # ------------------------------------------------------

    if response_text.startswith("```"):

        response_text = (
            response_text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    # ------------------------------------------------------
    # PARSE JSON
    # ------------------------------------------------------

    try:

        result = json.loads(
            response_text
        )

    except json.JSONDecodeError as exc:

        raise ValueError(
            "AI returned invalid JSON. "
            f"Raw response: {response_text}"
        ) from exc

    if not isinstance(result, dict):

        raise ValueError(
            "AI response must be a JSON object."
        )

    ai_records = result.get(
        "activities"
    )

    if not isinstance(ai_records, list):

        raise ValueError(
            "AI response does not contain "
            "a valid 'activities' array."
        )

    # ------------------------------------------------------
    # BUILD LOOKUPS
    # ------------------------------------------------------

    valid_ids = set(
        activities["ID"]
        .astype(str)
        .str.strip()
    )

    activity_names = {}

    for _, row in activities.iterrows():

        activity_names[
            str(row["ID"]).strip()
        ] = str(
            row["Activity"]
        ).strip()

    # ------------------------------------------------------
    # CONVERT AI OUTPUT
    # ------------------------------------------------------

    ai_lookup = {}

    for record in ai_records:

        if not isinstance(record, dict):
            continue

        activity_id = str(
            record.get("ID", "")
        ).strip()

        if activity_id:

            ai_lookup[
                activity_id
            ] = record

    suggestions = []

    # ------------------------------------------------------
    # PRESERVE ORIGINAL ACTIVITY ORDER
    # ------------------------------------------------------

    for _, row in activities.iterrows():

        activity_id = str(
            row["ID"]
        ).strip()

        activity_name = str(
            row["Activity"]
        ).strip()

        # --------------------------------------------------
        # AI RECORD
        # --------------------------------------------------

        ai_record = ai_lookup.get(
            activity_id
        )

        if ai_record is None:

            predecessor = ""

            relationship = (
                "No Predecessor"
            )

            confidence = "Low"

            reason = (
                "AI did not return a proposal."
            )

        else:

            predecessor = str(
                ai_record.get(
                    "Predecessor",
                    ""
                )
            ).strip()

            relationship = str(
                ai_record.get(
                    "Relationship",
                    "No Predecessor"
                )
            ).strip()

            confidence = str(
                ai_record.get(
                    "Confidence",
                    "Low"
                )
            ).strip()

            reason = str(
                ai_record.get(
                    "Reason",
                    ""
                )
            ).strip()

        # --------------------------------------------------
        # VALIDATE PREDECESSOR
        # --------------------------------------------------

        if predecessor:

            if predecessor not in valid_ids:

                predecessor = ""

                relationship = (
                    "No Predecessor"
                )

                confidence = "Low"

                reason = (
                    "AI proposed an invalid predecessor "
                    "ID; planner review required."
                )

            elif predecessor == activity_id:

                predecessor = ""

                relationship = (
                    "No Predecessor"
                )

                confidence = "Low"

                reason = (
                    "AI proposed a self-reference; "
                    "planner review required."
                )

        # --------------------------------------------------
        # NORMALIZE RELATIONSHIP
        # --------------------------------------------------

        relationship_map = {
            "FS": "Finish-to-Start (FS)",
            "SS": "Start-to-Start (SS)",
            "FF": "Finish-to-Finish (FF)",
            "SF": "Start-to-Finish (SF)",
            "Finish-to-Start": "Finish-to-Start (FS)",
            "Start-to-Start": "Start-to-Start (SS)",
            "Finish-to-Finish": "Finish-to-Finish (FF)",
            "Start-to-Finish": "Start-to-Finish (SF)",
        }

        relationship = relationship_map.get(
            relationship,
            relationship
        )

        # --------------------------------------------------
        # VALIDATE RELATIONSHIP
        # --------------------------------------------------

        if relationship not in RELATIONSHIP_OPTIONS:

            relationship = (
                "No Predecessor"
                if not predecessor
                else "Finish-to-Start (FS)"
            )

            confidence = "Low"

            reason = (
                "AI returned an invalid relationship; "
                "planner review required."
            )

        # --------------------------------------------------
        # NO PREDECESSOR CONSISTENCY
        # --------------------------------------------------

        if (
            relationship == "No Predecessor"
            and predecessor
        ):

            predecessor = ""

        if (
            relationship != "No Predecessor"
            and not predecessor
        ):

            relationship = (
                "No Predecessor"
            )

            confidence = "Low"

            reason = (
                "Relationship required a predecessor "
                "but none was provided."
            )

        # --------------------------------------------------
        # CONVERT ID TO ACTIVITY NAME
        #
        # Existing table displays activity names.
        # --------------------------------------------------

        if predecessor:

            predecessor_display = (
                activity_names.get(
                    predecessor,
                    predecessor
                )
            )

        else:

            predecessor_display = (
                "None 🔍"
            )

        # --------------------------------------------------
        # CREATE EXISTING TABLE FORMAT
        # --------------------------------------------------

        suggestions.append({

            "ID": activity_id,

            "Activity": activity_name,

            "Suggested Predecessor": (
                predecessor_display
            ),

            "Relationship": relationship,

            "Confidence": confidence,

            "Reason": reason,

            "Approve": False,

            "Status": "⏳ Pending"
        })

    return pd.DataFrame(
        suggestions
    )
import json

import pandas as pd
from openai import OpenAI


# ==========================================================
# CONSTANTS
# ==========================================================

WBS_STATUS_OPTIONS = [
    "⏳ Pending",
    "✅ Approved",
    "✏️ Modified",
]


# ==========================================================
# AI WBS BUILDER
# ==========================================================

def get_ai_wbs_suggestions(
    project_name,
    project_description,
    api_key,
    model="openai/gpt-oss-20b",
):
    """
    Use an LLM to propose a construction WBS hierarchy.

    The AI proposes:
        - WBS ID
        - WBS name
        - parent WBS
        - hierarchy level
        - description

    The AI does NOT create:
        - activities
        - relationships
        - durations
        - dates
        - resources
        - costs

    Returns a DataFrame suitable for the WBS review table.
    """

    # ------------------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------------------

    if not project_name or not str(project_name).strip():
        raise ValueError(
            "Project name is required."
        )

    if not project_description or not str(
        project_description
    ).strip():
        raise ValueError(
            "Project description is required."
        )

    if not api_key or not str(api_key).strip():
        raise ValueError(
            "Groq API key is required."
        )

    project_name = str(project_name).strip()
    project_description = str(
        project_description
    ).strip()

    # ------------------------------------------------------
    # SYSTEM INSTRUCTIONS
    # ------------------------------------------------------

    system_prompt = """
You are an expert construction planning engineer
specializing in Work Breakdown Structures (WBS).

Your task is to create a logical construction WBS
for the project provided by the user.

IMPORTANT:

1. Create ONLY the WBS hierarchy.

2. Do NOT create construction activities.

3. Do NOT create activity relationships.

4. Do NOT create durations.

5. Do NOT create planned dates.

6. Do NOT create resources, crews, equipment,
   productivity rates or costs.

7. The WBS must represent logical work packages
   required to organize and control the project.

8. Use standard construction planning principles.

9. Organize the WBS from major project work packages
   into progressively more detailed sub-WBS elements.

10. Avoid unnecessary excessive decomposition.

11. WBS Level 1 should normally represent major
    project phases or work packages.

12. Level 2 and Level 3 may be used where useful.

13. Use hierarchical WBS IDs such as:
    1.0
    1.1
    1.2
    2.0
    2.1

14. The numbering must follow this structure:
    Level 1: 1.0, 2.0, 3.0, etc.
    Level 2: 1.1, 1.2, 2.1, 2.2, etc.
    Level 3: 1.1.1, 1.1.2, 1.2.1, etc.

15. The Parent_WBS of 1.0, 2.0, 3.0, etc.
    MUST be an empty string.

16. The Parent_WBS of 1.1 must be 1.0.
    The Parent_WBS of 1.2 must be 1.0.
    The Parent_WBS of 2.1 must be 2.0.

17. A child WBS must always reference its
    immediate parent only.

18. Level 1 WBS elements are the top-level project
    work packages and MUST NOT have a parent WBS.

19. Every WBS element below Level 1 MUST have a valid
    immediate parent WBS.

20. A Level 2 WBS must have a Level 1 parent.

21. A Level 3 WBS must have a Level 2 parent.

22. Parent_WBS must contain ONLY the immediate parent
    WBS ID.

23. For every Level 1 WBS, Parent_WBS MUST be an
    empty string "".

24. Do not create orphan WBS elements.

25. WBS IDs must be unique.

26. WBS names must be concise and professional.

27. Description must be short and explain the scope
    of the WBS element.

28. Do not invent project-specific facts that were
    not provided by the user.

29. Where the project scope is broad, use reasonable
    standard construction planning structure.

30. The WBS should be suitable for later mapping
    to construction activities and Primavera P6.

31. Do not generate activities disguised as WBS elements.
    For example, "Excavate foundation" is an activity.
    "Earthworks" is a suitable WBS element.

32. Return ONLY valid JSON.

The JSON must contain an array called "wbs".

Each item must contain exactly:

{
    "WBS_ID": "hierarchical WBS ID",
    "WBS_Name": "WBS name",
    "Parent_WBS": "parent WBS ID or empty string",
    "Level": 1,
    "Description": "short scope description"
}
"""

    # ------------------------------------------------------
    # USER PROMPT
    # ------------------------------------------------------

    user_prompt = f"""
Create a construction WBS for the following project.

PROJECT NAME:
{project_name}

PROJECT DESCRIPTION:
{project_description}

Requirements:

- Start with major construction work packages.
- Decompose only where useful for planning and control.
- Maintain a clear parent-child hierarchy.
- Use sequential WBS numbering.
- Do not create activities.
- Do not create dates or relationships.
- Return only the JSON object.
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
        max_tokens=4000,
    )

    # ------------------------------------------------------
    # EXTRACT RESPONSE
    # ------------------------------------------------------

    response_text = (
        response.choices[0]
        .message
        .content
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
            "AI returned invalid WBS JSON. "
            f"Raw response: {response_text}"
        ) from exc

    if not isinstance(result, dict):

        raise ValueError(
            "AI WBS response must be a JSON object."
        )

    ai_records = result.get("wbs")

    if not isinstance(ai_records, list):

        raise ValueError(
            "AI response does not contain "
            "a valid 'wbs' array."
        )

    # ------------------------------------------------------
    # CONVERT AI OUTPUT
    # ------------------------------------------------------

    records = []

    for record in ai_records:

        if not isinstance(record, dict):
            continue

        wbs_id = str(
            record.get(
                "WBS_ID",
                ""
            )
        ).strip()

        wbs_name = str(
            record.get(
                "WBS_Name",
                ""
            )
        ).strip()

        parent_wbs = str(
            record.get(
                "Parent_WBS",
                ""
            )
        ).strip()

        description = str(
            record.get(
                "Description",
                ""
            )
        ).strip()

        # --------------------------------------------------
        # LEVEL
        # --------------------------------------------------

        try:

            level = int(
                record.get(
                    "Level",
                    1
                )
            )

        except (TypeError, ValueError):

            level = 1

        # --------------------------------------------------
        # BASIC RECORD VALIDATION
        # --------------------------------------------------

        if not wbs_id or not wbs_name:
            continue

        if level < 1:
            level = 1

        records.append(
            {
                "WBS ID": wbs_id,
                "WBS Name": wbs_name,
                "Parent WBS": parent_wbs,
                "Level": level,
                "Description": description,
                "Approve": False,
                "Status": "⏳ Pending",
            }
        )

    if not records:

        raise ValueError(
            "AI did not return any valid WBS elements."
        )

    # ------------------------------------------------------
    # VALIDATE WBS STRUCTURE
    # ------------------------------------------------------

    df = pd.DataFrame(records)

    # ------------------------------------------------------
    # NORMALIZE LEVEL 1 WBS
    # ------------------------------------------------------

    # Level 1 WBS elements are always top-level
    # and therefore cannot have a parent.
    df.loc[
        df["Level"] == 1,
        "Parent WBS"
    ] = ""

    # ------------------------------------------------------
    # DUPLICATE WBS IDS
    # ------------------------------------------------------

    duplicate_ids = (
        df["WBS ID"]
        .duplicated()
    )

    if duplicate_ids.any():

        duplicates = (
            df.loc[
                duplicate_ids,
                "WBS ID"
            ]
            .tolist()
        )

        raise ValueError(
            "AI returned duplicate WBS IDs: "
            + ", ".join(
                str(x)
                for x in duplicates
            )
        )

    # ------------------------------------------------------
    # BUILD WBS LOOKUP
    # ------------------------------------------------------

    valid_wbs_ids = set(
        df["WBS ID"]
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------
    # VALIDATE PARENTS
    # ------------------------------------------------------

    validation_errors = []

    for _, row in df.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        parent_wbs = str(
            row["Parent WBS"]
        ).strip()

        level = int(
            row["Level"]
        )

        # Root / Level 1
        if level == 1:

            if parent_wbs:
                validation_errors.append(
                    f"{wbs_id}: Level 1 WBS "
                    "cannot have a parent."
                )

        # Child WBS
        else:

            if not parent_wbs:

                validation_errors.append(
                    f"{wbs_id}: Level {level} "
                    "requires a parent WBS."
                )

            elif parent_wbs not in valid_wbs_ids:

                validation_errors.append(
                    f"{wbs_id}: parent WBS "
                    f"'{parent_wbs}' does not exist."
                )

    # ------------------------------------------------------
    # VALIDATE HIERARCHICAL LEVELS
    # ------------------------------------------------------

    level_lookup = {
        str(row["WBS ID"]).strip():
        int(row["Level"])
        for _, row in df.iterrows()
    }

    for _, row in df.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        parent_wbs = str(
            row["Parent WBS"]
        ).strip()

        level = int(
            row["Level"]
        )

        if parent_wbs in level_lookup:

            parent_level = level_lookup[
                parent_wbs
            ]

            if level != parent_level + 1:

                validation_errors.append(
                    f"{wbs_id}: WBS level must be "
                    f"one level below its parent."
                )

    # ------------------------------------------------------
    # VALIDATE WBS ID FORMAT
    # ------------------------------------------------------

    for _, row in df.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        parts = wbs_id.split(".")

        if not all(
            part.isdigit()
            for part in parts
        ):

            validation_errors.append(
                f"{wbs_id}: invalid WBS ID format."
            )

    # ------------------------------------------------------
    # STOP IF STRUCTURE IS INVALID
    # ------------------------------------------------------

    if validation_errors:

        raise ValueError(
            "AI generated an invalid WBS structure:\n"
            + "\n".join(
                validation_errors
            )
        )

    # ------------------------------------------------------
    # SORT WBS HIERARCHICALLY
    # ------------------------------------------------------

    def wbs_sort_key(value):

        parts = str(
            value
        ).split(".")

        return tuple(
            int(part)
            if part.isdigit()
            else 999999
            for part in parts
        )

    df["_sort_key"] = df[
        "WBS ID"
    ].apply(
        wbs_sort_key
    )

    df = (
        df.sort_values(
            "_sort_key"
        )
        .drop(
            columns=["_sort_key"]
        )
        .reset_index(
            drop=True
        )
    )

    return df

def get_ai_activity_wbs_mapping(
    activities,
    approved_wbs,
    api_key,
    model="openai/gpt-oss-20b",
):
    """
    Propose a WBS assignment for each imported BOQ/activity.

    AI only proposes the WBS mapping.
    It does not create or modify the WBS.
    It does not assign duration, relationships, dates,
    resources, costs, or schedule information.
    """

    if not activities:
        raise ValueError(
            "No activities were provided for WBS mapping."
        )

    if approved_wbs is None or approved_wbs.empty:
        raise ValueError(
            "No approved WBS is available for activity mapping."
        )

    if not api_key or not api_key.strip():
        raise ValueError(
            "Groq API key is required."
        )

    required_wbs_columns = [
        "WBS ID",
        "WBS Name",
    ]

    for column in required_wbs_columns:
        if column not in approved_wbs.columns:
            raise ValueError(
                f"Approved WBS is missing required column: {column}"
            )

    client = OpenAI(
        api_key=api_key.strip(),
        base_url="https://api.groq.com/openai/v1",
    )

    # --------------------------------------------------
    # BUILD COMPACT WBS CONTEXT
    # --------------------------------------------------

    wbs_context = []

    valid_wbs_ids = set()

    for _, row in approved_wbs.iterrows():

        wbs_id = str(
            row["WBS ID"]
        ).strip()

        wbs_name = str(
            row["WBS Name"]
        ).strip()

        if not wbs_id:
            continue

        valid_wbs_ids.add(wbs_id)

        wbs_context.append(
            f"{wbs_id} | {wbs_name}"
        )

    if not wbs_context:
        raise ValueError(
            "Approved WBS contains no usable WBS elements."
        )

    # --------------------------------------------------
    # BUILD ACTIVITY CONTEXT
    # --------------------------------------------------

    activity_context = []

    for activity in activities:

        if isinstance(activity, dict):

            activity_index = activity.get(
                "Activity Index",
                len(activity_context) + 1
            )

            activity_text = str(
                activity.get("Activity", "")
            ).strip()

        else:

            activity_index = (
                len(activity_context) + 1
            )

            activity_text = str(
                activity
            ).strip()

        if not activity_text:
            continue

        activity_context.append(
            f"{activity_index} | {activity_text}"
        )

    if not activity_context:
        raise ValueError(
            "No usable activity descriptions were provided."
        )

    # --------------------------------------------------
    # COMPACT AI PROMPT
    # --------------------------------------------------

    system_prompt = """
You are a construction planning WBS mapping assistant.

Your task is to assign each imported construction activity
to the most appropriate WBS element from the APPROVED WBS.

IMPORTANT RULES:

1. Use ONLY WBS IDs supplied in the approved WBS.
2. Do NOT create new WBS elements.
3. Do NOT modify WBS names.
4. Assign exactly one WBS to each activity.
5. Use the activity description and construction meaning.
6. Do not assign WBS based only on similar wording.
7. If uncertain, choose the best available WBS and use lower confidence.
8. Do not create durations, dates, relationships, predecessors,
   resources, costs, quantities, or schedule information.
9. Preserve the activity index exactly.
10. Return valid JSON only.

CONFIDENCE must be one of:
"High", "Medium", "Low"

Return:

{
  "mappings": [
    {
      "Activity Index": 1,
      "Suggested WBS": "1.1",
      "Confidence": "High",
      "Reason": "Very short reason, max 8 words"
    }
  ]
}
"""

    user_prompt = (
        "APPROVED WBS:\n"
        + "\n".join(wbs_context)
        + "\n\nIMPORTED ACTIVITIES:\n"
        + "\n".join(activity_context)
    )

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
        temperature=0,
        max_tokens=2500,
        response_format={
            "type": "json_object"
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "AI returned an empty response."
        )

    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "AI returned invalid JSON."
        ) from exc

    mappings = result.get(
        "mappings",
        []
    )

    if not isinstance(mappings, list):
        raise ValueError(
            "AI returned an invalid mapping structure."
        )

    # --------------------------------------------------
    # VALIDATE AI OUTPUT
    # --------------------------------------------------

    valid_activity_indexes = set()

    for item in activities:

        if isinstance(item, dict):
            index = item.get(
                "Activity Index",
                len(valid_activity_indexes) + 1
            )
        else:
            index = (
                len(valid_activity_indexes) + 1
            )

        valid_activity_indexes.add(
            int(index)
        )

    records = []

    seen_indexes = set()

    for mapping in mappings:

        if not isinstance(mapping, dict):
            continue

        try:
            activity_index = int(
                mapping.get(
                    "Activity Index"
                )
            )
        except (
            TypeError,
            ValueError
        ):
            continue

        suggested_wbs = str(
            mapping.get(
                "Suggested WBS",
                ""
            )
        ).strip()

        confidence = str(
            mapping.get(
                "Confidence",
                "Low"
            )
        ).strip()

        reason = str(
            mapping.get(
                "Reason",
                ""
            )
        ).strip()

        # Activity must exist
        if activity_index not in valid_activity_indexes:
            continue

        # No duplicate activity mappings
        if activity_index in seen_indexes:
            continue

        # WBS must exist in approved WBS
        if suggested_wbs not in valid_wbs_ids:
            continue

        if confidence not in [
            "High",
            "Medium",
            "Low",
        ]:
            confidence = "Low"

        seen_indexes.add(
            activity_index
        )

        records.append(
            {
                "Activity Index": activity_index,
                "Suggested WBS": suggested_wbs,
                "Confidence": confidence,
                "Reason": reason,
                "Approve": False,
                "Status": "⏳ Pending",
            }
        )

    # --------------------------------------------------
    # ENSURE EVERY ACTIVITY HAS A MAPPING
    # --------------------------------------------------

    missing_indexes = (
        valid_activity_indexes
        - seen_indexes
    )

    if missing_indexes:

        missing_text = ", ".join(
            str(index)
            for index in sorted(
                missing_indexes
            )
        )

        raise ValueError(
            "AI did not return a valid WBS mapping "
            f"for activity index(es): {missing_text}"
        )

    mapping_df = pd.DataFrame(
        records
    )

    mapping_df = mapping_df.sort_values(
        "Activity Index"
    ).reset_index(
        drop=True
    )

    return mapping_df
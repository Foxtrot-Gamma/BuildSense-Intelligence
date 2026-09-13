
import json
import streamlit as st
import pandas as pd


# ============================================================
# BASELINE HTML EXPORT
# ============================================================

def generate_baseline_html(finalized_schedule):

    try:

        data = finalized_schedule.copy()

        # ------------------------------------------------------
        # VALIDATE REQUIRED COLUMNS
        # ------------------------------------------------------

        required_columns = [
            "ID",
            "Activity",
            "Planned Start",
            "Planned Finish",
            "Total Float",
            "Critical"
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            st.error(
                "Cannot generate HTML report. "
                "Missing columns: "
                + ", ".join(missing_columns)
            )

            return None

        # ------------------------------------------------------
        # PREPARE DATES
        # ------------------------------------------------------

        data["Planned Start"] = pd.to_datetime(
            data["Planned Start"],
            errors="coerce"
        )

        data["Planned Finish"] = pd.to_datetime(
            data["Planned Finish"],
            errors="coerce"
        )

        data = data[
            data["Planned Start"].notna()
            & data["Planned Finish"].notna()
        ].copy()

        if data.empty:

            st.error(
                "No valid schedule dates are available "
                "for the HTML report."
            )

            return None

        data = data.reset_index(drop=True)

        # ------------------------------------------------------
        # PROJECT INFORMATION
        # ------------------------------------------------------

        project_name = str(
            st.session_state.get(
                "project_name",
                "Construction Project"
            )
        )

        project_start = data[
            "Planned Start"
        ].min()

        project_finish = data[
            "Planned Finish"
        ].max()

        project_duration = (
            project_finish - project_start
        ).days + 1

        activity_count = len(data)

        critical_count = int(
            data["Critical"]
            .fillna(False)
            .astype(bool)
            .sum()
        )

        # ------------------------------------------------------
        # BUILD NETWORK NODES
        # ------------------------------------------------------

        nodes = []

        for _, row in data.iterrows():

            critical_value = bool(
                row.get(
                    "Critical",
                    False
                )
            )

            total_float = pd.to_numeric(
                row.get(
                    "Total Float",
                    0
                ),
                errors="coerce"
            )

            if pd.isna(total_float):

                total_float = 0

            node = {
                "id": str(
                    row.get("ID", "")
                ),

                "wbs": str(
                    row.get("WBS", "")
                ),

                "activity": str(
                    row.get("Activity", "")
                ),

                "duration": str(
                    row.get("Duration", "")
                ),

                "start": row[
                    "Planned Start"
                ].strftime("%d %b %Y"),

                "finish": row[
                    "Planned Finish"
                ].strftime("%d %b %Y"),

                "float": int(
                    total_float
                ),

                "critical": critical_value
            }

            nodes.append(node)

        # ------------------------------------------------------
        # BUILD LOGIC EDGES
        # ------------------------------------------------------

        edges = []

        activity_ids = set(
            str(value)
            for value in data["ID"].tolist()
        )

        for _, row in data.iterrows():

            successor = str(
                row.get(
                    "ID",
                    ""
                )
            ).strip()

            predecessor = str(
                row.get(
                    "Predecessor",
                    ""
                )
            ).strip()

            relationship = str(
                row.get(
                    "Relationship",
                    "Finish-to-Start (FS)"
                )
            ).strip()

            # --------------------------------------------------
            # NO PREDECESSOR
            # --------------------------------------------------

            if (
                not predecessor
                or predecessor.lower()
                in [
                    "nan",
                    "none",
                    "no predecessor",
                    "-"
                ]
            ):

                continue

            # --------------------------------------------------
            # NORMALIZE RELATIONSHIP
            # --------------------------------------------------

            if relationship.startswith(
                "Finish-to-Start"
            ):

                relationship_code = "FS"

            elif relationship.startswith(
                "Start-to-Start"
            ):

                relationship_code = "SS"

            elif relationship.startswith(
                "Finish-to-Finish"
            ):

                relationship_code = "FF"

            elif relationship.startswith(
                "Start-to-Finish"
            ):

                relationship_code = "SF"

            else:

                relationship_code = "FS"

            # --------------------------------------------------
            # MULTIPLE PREDECESSORS
            # --------------------------------------------------

            predecessor_items = [
                item.strip()
                for item in predecessor.split(",")
                if item.strip()
            ]

            for predecessor_id in predecessor_items:

                if predecessor_id in activity_ids:

                    edges.append({
                        "from": predecessor_id,
                        "to": successor,
                        "type": relationship_code
                    })

        # ------------------------------------------------------
        # SERIALIZE DATA FOR JAVASCRIPT
        # ------------------------------------------------------

        nodes_json = json.dumps(
            nodes,
            ensure_ascii=False
        )

        edges_json = json.dumps(
            edges,
            ensure_ascii=False
        )

        project_name_json = json.dumps(
            project_name,
            ensure_ascii=False
        )

        # ------------------------------------------------------
        # PROJECT DISPLAY VALUES
        # ------------------------------------------------------

        project_start_text = (
            project_start.strftime(
                "%d %b %Y"
            )
        )

        project_finish_text = (
            project_finish.strftime(
                "%d %b %Y"
            )
        )

        # ======================================================
        # HTML DOCUMENT
        #
        # IMPORTANT:
        # This is deliberately NOT an f-string.
        # ======================================================

        html = """
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Baseline Network Report</title>

<link rel="preconnect"
      href="https://fonts.googleapis.com">

<link rel="preconnect"
      href="https://fonts.gstatic.com"
      crossorigin>

<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
      rel="stylesheet">

<style>

:root {

    --bg:#0B1420;
    --panel:#101B29;
    --panel2:#0D1826;

    --line:rgba(255,255,255,0.08);
    --line-strong:rgba(255,255,255,0.16);

    --ink:#DCE4EA;
    --muted:#7C8FA3;
    --muted2:#56687C;

    --fs:#4FA8D8;
    --ss:#3FBF8F;
    --ff:#C084E0;
    --sf:#D8A84E;

    --crit:#E8622C;
    --crit-bg:rgba(232,98,44,0.12);

    --near:#E8C43D;
    --good:#3FBF8F;

    --radius:3px;
}

* {
    box-sizing:border-box;
}

body {

    margin:0;

    background:var(--bg);

    color:var(--ink);

    font-family:
        "IBM Plex Sans",
        Arial,
        sans-serif;
}

.header {

    padding:24px 32px;

    border-bottom:
        1px solid var(--line);

    display:flex;

    justify-content:space-between;

    align-items:flex-start;

    gap:30px;
}

.title {

    font-size:24px;

    font-weight:700;

    letter-spacing:0.5px;
}

.subtitle {

    margin-top:5px;

    color:var(--muted);

    font-size:13px;
}

.meta {

    display:flex;

    gap:28px;

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:11px;

    text-transform:uppercase;

    color:var(--muted);
}

.meta strong {

    display:block;

    margin-top:5px;

    color:var(--ink);

    font-size:12px;
}

.container {

    padding:24px 32px 40px;
}

.tabs {

    display:flex;

    border-bottom:
        1px solid var(--line);

    margin-bottom:20px;
}

.tab {

    padding:11px 18px;

    color:var(--muted);

    cursor:pointer;

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:12px;

    border-bottom:
        2px solid transparent;
}

.tab.active {

    color:var(--ink);

    border-bottom:
        2px solid var(--fs);
}

.panel {

    display:none;
}

.panel.active {

    display:block;
}

.stats {

    display:grid;

    grid-template-columns:
        repeat(5, 1fr);

    border:
        1px solid var(--line);

    margin-bottom:20px;
}

.stat {

    padding:16px;

    border-right:
        1px solid var(--line);
}

.stat:last-child {

    border-right:0;
}

.stat-label {

    color:var(--muted);

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:10px;

    text-transform:uppercase;

    margin-bottom:7px;
}

.stat-value {

    font-size:20px;

    font-weight:600;
}

.card {

    background:var(--panel);

    border:
        1px solid var(--line);

    border-radius:var(--radius);

    margin-bottom:20px;

    overflow:hidden;
}

.card-title {

    padding:12px 16px;

    border-bottom:
        1px solid var(--line);

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:11px;

    text-transform:uppercase;

    color:var(--muted);
}

.network-wrapper {

    overflow:auto;

    background:#09111B;

    min-height:500px;
}

svg {

    display:block;

    min-width:1100px;
}

.node {

    cursor:pointer;
}

.node rect {

    fill:#101B29;

    stroke:#344658;

    stroke-width:1;
}

.node.critical rect {

    stroke:var(--crit);

    stroke-width:2;
}

.node-title {

    fill:var(--ink);

    font-size:11px;

    font-weight:600;
}

.node-small {

    fill:var(--muted);

    font-size:9px;

    font-family:
        "IBM Plex Mono",
        monospace;
}

.edge {

    fill:none;

    stroke-width:1.5;
}

.edge.fs {

    stroke:var(--fs);
}

.edge.ss {

    stroke:var(--ss);
}

.edge.ff {

    stroke:var(--ff);
}

.edge.sf {

    stroke:var(--sf);
}

.edge.critical {

    stroke:var(--crit);

    stroke-width:2.5;
}

.edge-label {

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:9px;

    fill:var(--muted);
}

.legend {

    display:flex;

    gap:24px;

    padding:14px 16px;

    border-top:
        1px solid var(--line);

    color:var(--muted);

    font-size:11px;
}

.legend-item {

    display:flex;

    align-items:center;

    gap:7px;
}

.dot {

    width:9px;

    height:9px;

    border-radius:50%;
}

.table-wrap {

    overflow:auto;
}

table {

    width:100%;

    border-collapse:collapse;

    font-size:12px;
}

th {

    text-align:left;

    color:var(--muted);

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:10px;

    text-transform:uppercase;

    font-weight:500;

    padding:10px 12px;

    border-bottom:
        1px solid var(--line);
}

td {

    padding:10px 12px;

    border-bottom:
        1px solid var(--line);

    vertical-align:top;
}

tr.critical-row td {

    background:var(--crit-bg);
}

.badge {

    display:inline-block;

    padding:3px 7px;

    border-radius:2px;

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:9px;
}

.badge-critical {

    color:var(--crit);

    background:var(--crit-bg);
}

.badge-normal {

    color:var(--good);

    background:
        rgba(63,191,143,0.08);
}

.report {

    max-width:1100px;

    padding:20px;
}

.report h2 {

    font-size:18px;

    margin:
        24px 0 10px;
}

.report p {

    color:#B6C2CC;

    line-height:1.65;

    font-size:13px;
}

.logic {

    font-family:
        "IBM Plex Mono",
        monospace;

    font-size:11px;

    color:var(--muted);

    line-height:1.8;
}

@media(max-width:800px) {

    .header {

        flex-direction:column;
    }

    .meta {

        flex-wrap:wrap;
    }

    .stats {

        grid-template-columns:
            repeat(2, 1fr);
    }
}

</style>

</head>


<body>


<!-- =======================================================
     HEADER
     ======================================================= -->

<div class="header">

    <div>

        <div class="title">
            WBS Network & Baseline Report
        </div>

        <div class="subtitle"
             id="projectName">
        </div>

    </div>


    <div class="meta">

        <div>
            DOC TYPE
            <strong>BASE-NET</strong>
        </div>

        <div>
            REV
            <strong>A</strong>
        </div>

        <div>
            STATUS
            <strong>BASELINE</strong>
        </div>

    </div>

</div>


<div class="container">


<!-- =======================================================
     TABS
     ======================================================= -->

<div class="tabs">

    <div class="tab active"
         data-tab="network">
        1 · Network
    </div>

    <div class="tab"
         data-tab="schedule">
        2 · Schedule
    </div>

    <div class="tab"
         data-tab="report">
        3 · Logic Report
    </div>

</div>


<!-- =======================================================
     NETWORK TAB
     ======================================================= -->

<div id="network"
     class="panel active">


<div class="stats">


    <div class="stat">

        <div class="stat-label">
            Project Start
        </div>

        <div class="stat-value">
            __PROJECT_START__
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            Project Finish
        </div>

        <div class="stat-value">
            __PROJECT_FINISH__
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            Duration
        </div>

        <div class="stat-value">
            __PROJECT_DURATION__ days
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            Activities
        </div>

        <div class="stat-value">
            __ACTIVITY_COUNT__
        </div>

    </div>


    <div class="stat">

        <div class="stat-label">
            Critical
        </div>

        <div class="stat-value">
            __CRITICAL_COUNT__
        </div>

    </div>


</div>


<div class="card">


    <div class="card-title">
        Baseline Network Logic
    </div>


    <div class="network-wrapper"
         id="networkContainer">
    </div>


    <div class="legend">


        <div class="legend-item">

            <span class="dot"
                  style="background:#4FA8D8">
            </span>

            FS

        </div>


        <div class="legend-item">

            <span class="dot"
                  style="background:#3FBF8F">
            </span>

            SS

        </div>


        <div class="legend-item">

            <span class="dot"
                  style="background:#C084E0">
            </span>

            FF

        </div>


        <div class="legend-item">

            <span class="dot"
                  style="background:#D8A84E">
            </span>

            SF

        </div>


        <div class="legend-item">

            <span class="dot"
                  style="background:#E8622C">
            </span>

            Critical

        </div>


    </div>


</div>


</div>


<!-- =======================================================
     SCHEDULE TAB
     ======================================================= -->

<div id="schedule"
     class="panel">


<div class="card">


    <div class="card-title">
        Baseline Schedule Register
    </div>


    <div class="table-wrap">


        <table>


            <thead>

                <tr>

                    <th>ID</th>

                    <th>WBS</th>

                    <th>Activity</th>

                    <th>Duration</th>

                    <th>Relationship</th>

                    <th>Predecessor</th>

                    <th>Start</th>

                    <th>Finish</th>

                    <th>Float</th>

                    <th>Status</th>

                </tr>

            </thead>


            <tbody id="scheduleBody">
            </tbody>


        </table>


    </div>


</div>


</div>


<!-- =======================================================
     REPORT TAB
     ======================================================= -->

<div id="report"
     class="panel">


<div class="card">


    <div class="card-title">
        Baseline Logic Report
    </div>


    <div class="report">


        <h2>
            Executive Summary
        </h2>


        <p id="executiveSummary">
        </p>


        <h2>
            Critical Path
        </h2>


        <p id="criticalPath">
        </p>


        <h2>
            Logic Register
        </h2>


        <div class="logic"
             id="logicRegister">
        </div>


    </div>


</div>


</div>


</div>


<!-- =======================================================
     JAVASCRIPT
     ======================================================= -->

<script>

const PROJECT_NAME = __PROJECT_NAME_JSON__;

const NODES = __NODES_JSON__;

const EDGES = __EDGES_JSON__;


document.getElementById(
    "projectName"
).textContent = PROJECT_NAME;


// ==========================================================
// TABS
// ==========================================================

document.querySelectorAll(
    ".tab"
).forEach(function(tab) {

    tab.addEventListener(
        "click",
        function() {

            document.querySelectorAll(
                ".tab"
            ).forEach(function(item) {

                item.classList.remove(
                    "active"
                );

            });


            document.querySelectorAll(
                ".panel"
            ).forEach(function(panel) {

                panel.classList.remove(
                    "active"
                );

            });


            tab.classList.add(
                "active"
            );


            document.getElementById(
                tab.dataset.tab
            ).classList.add(
                "active"
            );

        }
    );

});


// ==========================================================
// NETWORK PARAMETERS
// ==========================================================

const NODE_W = 190;

const NODE_H = 92;

const COL_GAP = 120;

const ROW_GAP = 28;


// ==========================================================
// PREDECESSOR MAP
// ==========================================================

const predecessors = {};

NODES.forEach(function(node) {

    predecessors[node.id] = [];

});


EDGES.forEach(function(edge) {

    if (!predecessors[edge.to]) {

        predecessors[edge.to] = [];

    }

    predecessors[edge.to].push(
        edge.from
    );

});


// ==========================================================
// CALCULATE NETWORK LEVEL
// ==========================================================

const levels = {};


function calculateLevel(id, visited) {

    if (levels[id] !== undefined) {

        return levels[id];

    }


    if (visited[id]) {

        return 0;

    }


    visited[id] = true;


    const preds =
        predecessors[id] || [];


    if (preds.length === 0) {

        levels[id] = 0;

        return 0;

    }


    let maxLevel = 0;


    preds.forEach(function(pred) {

        maxLevel = Math.max(
            maxLevel,
            calculateLevel(
                pred,
                visited
            ) + 1
        );

    });


    levels[id] = maxLevel;

    return maxLevel;

}


NODES.forEach(function(node) {

    calculateLevel(
        node.id,
        {}
    );

});


// ==========================================================
// GROUP NODES INTO COLUMNS
// ==========================================================

const columns = {};


NODES.forEach(function(node) {

    const level =
        levels[node.id] || 0;


    if (!columns[level]) {

        columns[level] = [];

    }


    columns[level].push(
        node
    );

});


// ==========================================================
// CALCULATE NODE POSITIONS
// ==========================================================

const positions = {};


Object.keys(columns).forEach(
    function(level) {

        columns[level].forEach(
            function(node, index) {

                positions[node.id] = {

                    x:
                        40
                        + Number(level)
                        * (
                            NODE_W
                            + COL_GAP
                        ),

                    y:
                        40
                        + index
                        * (
                            NODE_H
                            + ROW_GAP
                        )

                };

            }
        );

    }
);


// ==========================================================
// ESCAPE HTML
// ==========================================================

function escapeHtml(value) {

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// ==========================================================
// EDGE CLASS
// ==========================================================

function edgeClass(type) {

    if (type === "FS") {

        return "fs";

    }

    if (type === "SS") {

        return "ss";

    }

    if (type === "FF") {

        return "ff";

    }

    if (type === "SF") {

        return "sf";

    }

    return "fs";

}


// ==========================================================
// RENDER NETWORK
// ==========================================================

function renderNetwork() {

    const container =
        document.getElementById(
            "networkContainer"
        );


    if (!NODES.length) {

        container.innerHTML =
            "<p style='padding:20px;color:#7C8FA3'>"
            + "No network data available."
            + "</p>";

        return;

    }


    let maxX = 0;

    let maxY = 0;


    Object.keys(
        positions
    ).forEach(function(id) {

        maxX = Math.max(
            maxX,
            positions[id].x
            + NODE_W
        );


        maxY = Math.max(
            maxY,
            positions[id].y
            + NODE_H
        );

    });


    let svg = "";


    svg +=
        "<svg "
        + "width='"
        + maxX
        + "' "
        + "height='"
        + maxY
        + "' "
        + "viewBox='0 0 "
        + maxX
        + " "
        + maxY
        + "'>";


    // ------------------------------------------------------
    // ARROW DEFINITIONS
    // ------------------------------------------------------

    svg += "<defs>";


    svg +=
        "<marker id='arrowFS' "
        + "markerWidth='7' "
        + "markerHeight='7' "
        + "refX='6' "
        + "refY='3.5' "
        + "orient='auto'>"
        + "<path d='M0,0 L7,3.5 L0,7 Z' "
        + "fill='#4FA8D8'/>"
        + "</marker>";


    svg +=
        "<marker id='arrowSS' "
        + "markerWidth='7' "
        + "markerHeight='7' "
        + "refX='6' "
        + "refY='3.5' "
        + "orient='auto'>"
        + "<path d='M0,0 L7,3.5 L0,7 Z' "
        + "fill='#3FBF8F'/>"
        + "</marker>";


    svg +=
        "<marker id='arrowFF' "
        + "markerWidth='7' "
        + "markerHeight='7' "
        + "refX='6' "
        + "refY='3.5' "
        + "orient='auto'>"
        + "<path d='M0,0 L7,3.5 L0,7 Z' "
        + "fill='#C084E0'/>"
        + "</marker>";


    svg +=
        "<marker id='arrowSF' "
        + "markerWidth='7' "
        + "markerHeight='7' "
        + "refX='6' "
        + "refY='3.5' "
        + "orient='auto'>"
        + "<path d='M0,0 L7,3.5 L0,7 Z' "
        + "fill='#D8A84E'/>"
        + "</marker>";


    svg += "</defs>";


    // ------------------------------------------------------
    // DRAW EDGES
    // ------------------------------------------------------

    EDGES.forEach(function(edge) {

        const from =
            positions[edge.from];


        const to =
            positions[edge.to];


        if (!from || !to) {

            return;

        }


        const x1 =
            from.x + NODE_W;


        const y1 =
            from.y + NODE_H / 2;


        const x2 =
            to.x;


        const y2 =
            to.y + NODE_H / 2;


        const midX =
            (x1 + x2) / 2;


        const nodeTo =
            NODES.find(
                function(n) {

                    return n.id === edge.to;

                }
            );


        const critical =
            nodeTo
            && nodeTo.critical;


        svg +=
            "<path "
            + "class='edge "
            + edgeClass(edge.type)
            + (
                critical
                ? " critical"
                : ""
            )
            + "' "
            + "d='M "
            + x1
            + " "
            + y1
            + " C "
            + midX
            + " "
            + y1
            + ", "
            + midX
            + " "
            + y2
            + ", "
            + x2
            + " "
            + y2
            + "' "
            + "marker-end='url(#arrow"
            + edge.type
            + ")'>"
            + "</path>";


        svg +=
            "<text "
            + "class='edge-label' "
            + "x='"
            + midX
            + "' "
            + "y='"
            + (
                (y1 + y2) / 2
                - 5
            )
            + "' "
            + "text-anchor='middle'>"
            + escapeHtml(
                edge.type
            )
            + "</text>";

    });


    // ------------------------------------------------------
    // DRAW NODES
    // ------------------------------------------------------

    NODES.forEach(function(node) {

        const p =
            positions[node.id];


        if (!p) {

            return;

        }


        const nodeClass =
            node.critical
            ? "node critical"
            : "node";


        svg +=
            "<g class='"
            + nodeClass
            + "' "
            + "transform='translate("
            + p.x
            + ","
            + p.y
            + ")'>";


        svg +=
            "<rect "
            + "width='"
            + NODE_W
            + "' "
            + "height='"
            + NODE_H
            + "' "
            + "rx='3'/>";


        svg +=
            "<text "
            + "class='node-small' "
            + "x='10' "
            + "y='14'>"
            + escapeHtml(
                node.wbs
            )
            + "</text>";


        svg +=
            "<text "
            + "class='node-small' "
            + "x='"
            + (
                NODE_W - 10
            )
            + "' "
            + "y='14' "
            + "text-anchor='end'>"
            + (
                node.critical
                ? "CRITICAL"
                : "FLOAT "
                + escapeHtml(
                    node.float
                )
            )
            + "</text>";


        svg +=
            "<text "
            + "class='node-title' "
            + "x='10' "
            + "y='34'>"
            + escapeHtml(
                node.activity
            )
            + "</text>";


        svg +=
            "<text "
            + "class='node-small' "
            + "x='10' "
            + "y='50'>"
            + "DUR "
            + escapeHtml(
                node.duration
            )
            + " days"
            + "</text>";


        svg +=
            "<text "
            + "class='node-small' "
            + "x='10' "
            + "y='66'>"
            + escapeHtml(
                node.start
            )
            + " → "
            + escapeHtml(
                node.finish
            )
            + "</text>";


        svg +=
            "<text "
            + "class='node-small' "
            + "x='10' "
            + "y='82'>"
            + "ID "
            + escapeHtml(
                node.id
            )
            + "</text>";


        svg += "</g>";

    });


    svg += "</svg>";


    container.innerHTML = svg;

}


// ==========================================================
// SCHEDULE TABLE
// ==========================================================

function renderSchedule() {

    const body =
        document.getElementById(
            "scheduleBody"
        );


    body.innerHTML = "";


    NODES.forEach(function(node) {

        const row =
            document.createElement(
                "tr"
            );


        if (node.critical) {

            row.classList.add(
                "critical-row"
            );

        }


        const status =
            node.critical
            ? "<span class='badge badge-critical'>CRITICAL</span>"
            : "<span class='badge badge-normal'>NORMAL</span>";


        row.innerHTML =
            "<td>"
            + escapeHtml(node.id)
            + "</td>"

            + "<td>"
            + escapeHtml(node.wbs)
            + "</td>"

            + "<td>"
            + escapeHtml(node.activity)
            + "</td>"

            + "<td>"
            + escapeHtml(node.duration)
            + "</td>"

            + "<td>"
            + escapeHtml(
                getRelationship(
                    node.id
                )
            )
            + "</td>"

            + "<td>"
            + escapeHtml(
                getPredecessor(
                    node.id
                )
            )
            + "</td>"

            + "<td>"
            + escapeHtml(node.start)
            + "</td>"

            + "<td>"
            + escapeHtml(node.finish)
            + "</td>"

            + "<td>"
            + escapeHtml(node.float)
            + "</td>"

            + "<td>"
            + status
            + "</td>";


        body.appendChild(
            row
        );

    });

}


// ==========================================================
// GET RELATIONSHIP
// ==========================================================

function getRelationship(id) {

    const matches =
        EDGES.filter(
            function(edge) {

                return edge.to === id;

            }
        );


    if (!matches.length) {

        return "No Predecessor";

    }


    return matches
        .map(
            function(edge) {

                return edge.type;

            }
        )
        .join(", ");

}


// ==========================================================
// GET PREDECESSOR
// ==========================================================

function getPredecessor(id) {

    const matches =
        EDGES.filter(
            function(edge) {

                return edge.to === id;

            }
        );


    if (!matches.length) {

        return "-";

    }


    return matches
        .map(
            function(edge) {

                return edge.from;

            }
        )
        .join(", ");

}


// ==========================================================
// REPORT
// ==========================================================

function renderReport() {

    const criticalNodes =
        NODES.filter(
            function(node) {

                return node.critical;

            }
        );


    const names =
        criticalNodes.map(
            function(node) {

                return node.activity;

            }
        );


    document.getElementById(
        "executiveSummary"
    ).textContent =

        "The approved baseline contains "
        + NODES.length
        + " activities with a project duration of "
        + "__PROJECT_DURATION__"
        + " days. "
        + criticalNodes.length
        + " activities are identified as critical "
        + "and therefore have zero total float.";


    document.getElementById(
        "criticalPath"
    ).textContent =

        names.length
        ? names.join(" → ")
        : "No critical activities identified.";


    const logic =
        document.getElementById(
            "logicRegister"
        );


    logic.innerHTML = "";


    EDGES.forEach(function(edge) {

        const line =
            document.createElement(
                "div"
            );


        line.textContent =
            edge.from
            + "  →  "
            + edge.to
            + "   ["
            + edge.type
            + "]";


        logic.appendChild(
            line
        );

    });

}


// ==========================================================
// INITIALIZE
// ==========================================================

renderNetwork();

renderSchedule();

renderReport();

</script>


</body>

</html>
"""

        # ======================================================
        # INSERT PYTHON DATA INTO HTML
        # ======================================================

        html = html.replace(
            "__PROJECT_NAME_JSON__",
            project_name_json
        )

        html = html.replace(
            "__NODES_JSON__",
            nodes_json
        )

        html = html.replace(
            "__EDGES_JSON__",
            edges_json
        )

        html = html.replace(
            "__PROJECT_START__",
            project_start_text
        )

        html = html.replace(
            "__PROJECT_FINISH__",
            project_finish_text
        )

        html = html.replace(
            "__PROJECT_DURATION__",
            str(project_duration)
        )

        html = html.replace(
            "__ACTIVITY_COUNT__",
            str(activity_count)
        )

        html = html.replace(
            "__CRITICAL_COUNT__",
            str(critical_count)
        )

        return html

    except Exception as e:

        st.error(
            "HTML generation error: "
            + str(e)
        )

        return None

# BuildSense Intelligence

**Construction Planning, Scheduling & Progress Control — MVP**

BuildSense Intelligence is a Streamlit-based construction planning and control application that converts project BOQ/WBS data into structured activities, baseline schedules, progress updates, and visual project-control insights.

It combines **deterministic scheduling** with **AI-assisted planning** to support construction teams in moving from project setup to execution monitoring and recovery planning.

## 🚀 Core Workflow

**Project Setup → BOQ/WBS & Activity Data → Planning & Scheduling → Review & Baseline → Progress Updating → Dashboard & Recovery Control**

### Key Capabilities

* **Project Setup** — Define project information, dates, and basic parameters.
* **BOQ/WBS & Activity Data** — Create, import, edit, and manage project activities.
* **AI WBS Builder** — Generate a proposed WBS/BOQ structure for human review and approval.
* **AI Schedule Builder** — Assist with activity sequencing and schedule relationships.
* **Deterministic Scheduling** — Calculate activity dates using logical relationships including:

  * Finish-to-Start (FS)
  * Start-to-Start (SS)
  * Finish-to-Finish (FF)
  * Start-to-Finish (SF)
* **Review & Baseline** — Validate the schedule and establish a controlled baseline.
* **Progress Updating** — Record actual progress and monitor schedule performance.
* **Project Dashboard** — Visualize planned vs. actual progress, status, variances, and key project indicators.
* **Gantt Views** — Visualize baseline, progress, and look-ahead schedules.
* **AI Recovery Assistance** — Provide recovery recommendations without automatically modifying the approved baseline.
* **Excel & HTML Export** — Generate shareable project-control deliverables.

## 🤖 AI Philosophy

AI is used as an **assistant, not the authority**.

AI-generated WBS structures, schedules, relationships, and recovery recommendations remain subject to human review and approval. The approved project baseline is preserved and is not silently altered by AI recommendations.

## 🛠️ Technology

* **Python**
* **Streamlit**
* **Pandas**
* **Plotly**
* **Groq / LLM integration**
* **Excel & HTML export**

## 📁 Project Structure

```text
construction-mvp/
├── app.py
├── requirements.txt
├── state.py
├── utils.py
├── test_groq.py
└── modules/
    ├── activity_data.py
    ├── ai_assistant.py
    ├── ai_schedule_builder.py
    ├── ai_wbs_builder.py
    ├── dashboard.py
    ├── excel_export.py
    ├── html_export.py
    ├── progress_control.py
    ├── project_setup.py
    └── scheduling.py
```

## ▶️ Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

For AI functionality, configure the required API credentials through environment variables or Streamlit Secrets. **Do not commit API keys or other secrets to the repository.**

## 📌 Project Status

**MVP — Active Development**

BuildSense Intelligence is being developed incrementally, with emphasis on practical construction planning, deterministic schedule control, AI-assisted decision support, and clear planned-vs-actual visibility.

Future development may include enhanced navigation, advanced recovery controls, additional reporting, and further AI-assisted planning capabilities.

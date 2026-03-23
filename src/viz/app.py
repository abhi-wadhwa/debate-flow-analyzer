"""Streamlit UI for the AI Debate Flow Analyzer."""

from __future__ import annotations

import json
from typing import List

import streamlit as st

from src.core.dropped import DroppedArgumentDetector
from src.core.extractor import Argument, ArgumentExtractor
from src.core.flow_sheet import FlowSheet
from src.core.formats import list_formats, get_format
from src.core.impact import ImpactCalculus
from src.core.llm_client import create_client, LLMClient
from src.core.parser import SpeechParser
from src.core.win_prob import WinProbabilityEstimator


# -----------------------------------------------------------------------
# Colour palette for sides
# -----------------------------------------------------------------------
SIDE_COLOURS = {
    "affirmative": "#2E86AB",
    "negative": "#E84855",
    "government": "#2E86AB",
    "opposition": "#E84855",
    "proposition": "#2E86AB",
}

DEFAULT_COLOUR = "#888888"


def _side_colour(side: str) -> str:
    return SIDE_COLOURS.get(side.lower(), DEFAULT_COLOUR)


# -----------------------------------------------------------------------
# Streamlit app
# -----------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Debate Flow Analyzer",
        page_icon="",
        layout="wide",
    )

    st.title("AI Debate Flow Analyzer")
    st.markdown(
        "Paste or upload a debate transcript to generate a flow sheet, "
        "detect dropped arguments, and estimate win probability."
    )

    # ---- Sidebar controls ----
    with st.sidebar:
        st.header("Settings")

        fmt_name = st.selectbox("Debate Format", list_formats())

        api_key = st.text_input("OpenAI API Key", type="password", help="Leave empty to use OPENAI_API_KEY env var")
        model = st.text_input("Model", value="gpt-4o-mini")

        use_mock = st.checkbox("Use mock LLM (demo mode)", value=True)

        st.markdown("---")
        st.markdown(
            "**Weights** for win-probability estimation"
        )
        w_cov = st.slider("Argument coverage", 0.0, 1.0, 0.25, 0.05)
        w_reb = st.slider("Rebuttal coverage", 0.0, 1.0, 0.20, 0.05)
        w_drop = st.slider("Dropped argument penalty", 0.0, 1.0, 0.25, 0.05)
        w_imp = st.slider("Impact calculus", 0.0, 1.0, 0.30, 0.05)

    # ---- Transcript input ----
    st.subheader("Transcript Input")
    tab_paste, tab_upload = st.tabs(["Paste", "Upload"])

    transcript = ""
    with tab_paste:
        transcript = st.text_area(
            "Paste debate transcript here",
            height=300,
            placeholder="1AC: Our plan is ...\n1NC: The opposition argues ...",
        )
    with tab_upload:
        uploaded = st.file_uploader("Upload a .txt transcript", type=["txt"])
        if uploaded is not None:
            transcript = uploaded.read().decode("utf-8")
            st.text_area("Preview", transcript, height=200, disabled=True)

    if not transcript.strip():
        st.info("Enter or upload a transcript to begin analysis.")
        return

    # ---- Run analysis ----
    if st.button("Analyse Debate", type="primary"):
        _run_analysis(
            transcript=transcript,
            fmt_name=fmt_name,
            use_mock=use_mock,
            api_key=api_key,
            model=model,
            weights=(w_cov, w_reb, w_drop, w_imp),
        )


def _run_analysis(
    transcript: str,
    fmt_name: str,
    use_mock: bool,
    api_key: str,
    model: str,
    weights: tuple,
) -> None:
    """Execute the full analysis pipeline and render results."""

    # 1. Create LLM client
    if use_mock:
        llm = _build_mock_client()
    else:
        llm = create_client("openai", api_key=api_key or None, model=model)

    fmt = get_format(fmt_name.lower().replace(" ", "-"))

    with st.spinner("Parsing transcript..."):
        parser = SpeechParser(fmt)
        speeches = parser.parse(transcript)

    if not speeches:
        st.error("Could not parse any speeches from the transcript.")
        return

    st.success(f"Parsed {len(speeches)} speeches.")

    with st.spinner("Extracting arguments..."):
        extractor = ArgumentExtractor(llm)
        arguments = extractor.extract_all(speeches)

    st.success(f"Extracted {len(arguments)} arguments.")

    # 2. Build flow sheet
    flow = FlowSheet()
    flow.build(arguments)

    # 3. Detect dropped arguments
    detector = DroppedArgumentDetector()
    dropped = detector.detect(flow)

    # 4. Impact calculus
    impact_calc = ImpactCalculus(llm)
    root_args = flow.get_root_arguments()
    impact_assessments = impact_calc.assess(root_args) if root_args else []

    # 5. Win probability
    w_cov, w_reb, w_drop, w_imp = weights
    estimator = WinProbabilityEstimator(w_cov, w_reb, w_drop, w_imp)
    win_est = estimator.estimate(flow, dropped, impact_assessments)

    # ---- Render results ----
    _render_flow_sheet(flow)
    _render_dropped(dropped)
    _render_impact(impact_assessments, impact_calc)
    _render_win_probability(win_est, estimator)


# -----------------------------------------------------------------------
# Rendering helpers
# -----------------------------------------------------------------------

def _render_flow_sheet(flow: FlowSheet) -> None:
    st.subheader("Flow Sheet")
    if not flow.columns:
        st.warning("No arguments to display.")
        return

    cols = st.columns(len(flow.columns))
    for col_ui, flow_col in zip(cols, flow.columns):
        colour = _side_colour(flow_col.side)
        with col_ui:
            st.markdown(
                f"<div style='background:{colour};color:white;padding:6px 10px;"
                f"border-radius:6px;text-align:center;font-weight:bold'>"
                f"{flow_col.speech_label}</div>",
                unsafe_allow_html=True,
            )
            st.caption(flow_col.side)
            for arg in flow_col.arguments:
                border = "2px dashed orange" if arg.parent_id else f"2px solid {colour}"
                arrow_text = f"Rebuts [{arg.parent_id}]" if arg.parent_id else ""
                st.markdown(
                    f"<div style='border:{border};border-radius:8px;padding:8px;"
                    f"margin:6px 0;font-size:0.85em'>"
                    f"<strong>{arg.claim}</strong><br/>"
                    f"<em>Warrant:</em> {arg.warrant}<br/>"
                    f"<em>Impact:</em> {arg.impact}"
                    f"{'<br/><span style=\"color:orange\">' + arrow_text + '</span>' if arrow_text else ''}"
                    f"</div>",
                    unsafe_allow_html=True,
                )


def _render_dropped(dropped: list) -> None:
    st.subheader("Dropped Arguments")
    if not dropped:
        st.success("No dropped arguments detected!")
        return

    for da in dropped:
        severity_colour = {"high": "red", "medium": "orange", "low": "gray"}.get(
            da.severity, "gray"
        )
        with st.expander(
            f"[{da.severity.upper()}] {da.argument.claim} "
            f"({da.argument.speech_label})"
        ):
            st.markdown(f"**Severity:** :{severity_colour}[{da.severity}]")
            st.markdown(f"**Side:** {da.argument.side}")
            st.markdown(f"**Impact:** {da.argument.impact}")
            st.markdown(
                f"**Should have been addressed in:** "
                f"{', '.join(da.expected_responses_from)}"
            )


def _render_impact(assessments: list, calc) -> None:
    st.subheader("Impact Calculus")
    if not assessments:
        st.info("No impact assessments.")
        return

    for a in sorted(assessments, key=lambda x: x.composite_score, reverse=True):
        with st.expander(f"[{a.argument_id}] {a.claim} -- Score: {a.composite_score:.1f}/10"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Magnitude", f"{a.magnitude}/10")
            c2.metric("Timeframe", f"{a.timeframe}/10")
            c3.metric("Probability", f"{a.probability}/10")
            c4.metric("Reversibility", f"{a.reversibility}/10")
            st.markdown(a.explanation)


def _render_win_probability(est, estimator) -> None:
    st.subheader("Win Probability")
    if not est.sides:
        st.info("Not enough data to estimate.")
        return

    cols = st.columns(len(est.sides))
    for col_ui, (side, score) in zip(cols, est.sides.items()):
        with col_ui:
            colour = _side_colour(side)
            prob_pct = score.win_probability * 100
            st.markdown(
                f"<div style='text-align:center'>"
                f"<h2 style='color:{colour}'>{side}</h2>"
                f"<h1 style='color:{colour}'>{prob_pct:.1f}%</h1>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.metric("Arguments", score.argument_count)
            st.metric("Rebuttals", score.rebuttal_count)
            st.metric("Opponent dropped", score.dropped_by_opponent)

    st.markdown(f"**Predicted winner:** {est.predicted_winner}")
    st.markdown(f"**Confidence:** {est.confidence:.1%}")
    st.markdown(f"**Rationale:** {est.rationale}")


# -----------------------------------------------------------------------
# Mock LLM for demo mode
# -----------------------------------------------------------------------

def _build_mock_client():
    from src.core.llm_client import MockLLMClient

    client = MockLLMClient()

    # Argument extraction response -- will be reused for all speeches
    extraction_response = json.dumps({
        "arguments": [
            {
                "claim": "Economic growth requires infrastructure investment",
                "warrant": "Historical data shows GDP growth correlates with infrastructure spending",
                "impact": "Without investment, GDP growth stalls affecting millions of jobs",
                "tags": ["economy", "infrastructure"],
                "parent_id": None,
            },
            {
                "claim": "Environmental regulations protect public health",
                "warrant": "EPA studies show reduced pollution leads to fewer respiratory illnesses",
                "impact": "Deregulation risks thousands of preventable deaths annually",
                "tags": ["environment", "health"],
                "parent_id": None,
            },
        ]
    })

    # Impact assessment response
    impact_response = json.dumps({
        "assessments": [
            {
                "argument_id": "placeholder",
                "magnitude": 7,
                "timeframe": 6,
                "probability": 7,
                "reversibility": 5,
                "explanation": "Significant economic impact with moderate timeline.",
            }
        ]
    })

    client.add_response(extraction_response)
    client.add_response(extraction_response)
    client.add_response(impact_response)

    return client


if __name__ == "__main__":
    main()

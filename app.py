import streamlit as st
from pathlib import Path
from scripts.rule_based_validation import validate_dataset

# Page Config
st.set_page_config(page_title="Data Validation Suite", layout="wide")

# Custom CSS (bright pastel, simple layout, fixed summary cards)
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(to right, #e0f7fa, #e8f5e9);
    }
    .main-title {
        font-size: 32px;
        font-weight: 600;
        text-align: center;
        color: #ffffff;  /* White title */
        margin-bottom: 1rem;
    }
    .stFileUploader {
        border: 2px dashed #60a5fa;
        background-color: #f0f9ff;
        border-radius: 12px;
        padding: 2rem;
        width: 70% !important;
        margin: auto;
    }
    .metric-card {
        background: #fef9c3;
        padding: 0.8rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        word-wrap: break-word;
        white-space: normal;
        min-height: 90px;  /* prevent overflow */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-number {
        font-size: 22px;
        font-weight: 700;
        color: #065f46;
    }
    .metric-label {
        font-size: 14px;
        color: #334155;
        margin-top: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar
st.sidebar.title("Navigation")
st.sidebar.markdown("Upload CSV → Validate → Download styled reports.")

# Main Title
st.markdown("<div class='main-title'>Data Validation Dashboard</div>", unsafe_allow_html=True)

# File Uploader
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
rules_file = Path("data/validation_rules.json")

if uploaded_file:
    # Save uploaded file
    temp_file = Path("data/raw") / uploaded_file.name
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_file, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Run validation
    bad_rows, report_file, issues_summary = validate_dataset(
        temp_file, rules_file if rules_file.exists() else None
    )

    # Summary
    st.markdown("### Validation Summary")
    if issues_summary:
        cols = st.columns(len(issues_summary))
        for i, (issue, count) in enumerate(issues_summary.items()):
            with cols[i]:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-number">{count}</div>
                        <div class="metric-label">{issue}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.success("No issues found! 🎉")

    # Tabs
    tab1, tab2 = st.tabs(["Preview Issues", "Download Reports"])

    with tab1:
        if bad_rows.empty:
            st.info("No issues to preview.")
        else:
            for category, df_cat in bad_rows.groupby("issue"):
                with st.expander(f"{category} ({len(df_cat)} rows)"):
                    st.dataframe(df_cat.drop(columns=["issue"]).head(5))

    with tab2:
        st.markdown("#### Download Reports")
        if not bad_rows.empty:
            file_stem = Path(uploaded_file.name).stem.replace(" ", "_")
            csv_data = bad_rows.drop(columns=["issue"]).to_csv(index=False).encode()
            st.download_button(
                label="Download Issues CSV",
                data=csv_data,
                file_name=f"{file_stem}_issues.csv",
                mime="text/csv"
            )
        if report_file.exists():
            st.markdown(f"[Open HTML Validation Report]({report_file.as_uri()})", unsafe_allow_html=True)
            with open(report_file, "rb") as f:
                st.download_button(
                    label="Download HTML Report",
                    data=f,
                    file_name=report_file.name,
                    mime="text/html"
                )

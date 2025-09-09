import pandas as pd
import json
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

MAX_DISPLAY_ROWS = 5

# CSS for HTML report
CSS_STYLE = """
<style>
body { font-family: 'Segoe UI', sans-serif; background-color: #f0fff4; color: #333; padding: 20px; }
h1 { color: #2e7d32; }
details { background-color: #e6f4ea; margin: 10px 0; padding: 10px; border-radius: 8px; }
summary { font-weight: bold; cursor: pointer; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th, td { border: 1px solid #999; padding: 8px; text-align: left; }
th { background-color: #a5d6a7; color: #000; }
</style>
"""

def generate_html_section(title, df, issue_count=None):
    count_info = f"<p><b>Total:</b> {issue_count}</p>" if issue_count else ""
    if df.empty:
        return f"<details><summary>{title}</summary>{count_info}<p>No {title} found.</p></details>"
    display_df = df.head(MAX_DISPLAY_ROWS)
    html_table = display_df.to_html(index=False, escape=False)
    more_rows_note = "<p>...and more rows not shown</p>" if len(df) > MAX_DISPLAY_ROWS else ""
    return f"<details><summary>{title} ({len(df)} rows)</summary>{count_info}{html_table}{more_rows_note}</details>"

def apply_json_rules(df, rules):
    violations = pd.DataFrame()
    for col, rule in rules.items():
        if col not in df.columns:
            continue
        if "min" in rule:
            invalid = df[df[col] < rule["min"]].copy()
            if not invalid.empty:
                invalid['issue'] = f"{col}_below_min"
                violations = pd.concat([violations, invalid])
        if "max" in rule:
            invalid = df[df[col] > rule["max"]].copy()
            if not invalid.empty:
                invalid['issue'] = f"{col}_above_max"
                violations = pd.concat([violations, invalid])
        if "allowed" in rule:
            invalid = df[~df[col].isin(rule["allowed"])].copy()
            if not invalid.empty:
                invalid['issue'] = f"{col}_invalid_value"
                violations = pd.concat([violations, invalid])
    return violations

def validate_dataset(file_path, rules_path=None):
    BASE_DIR = Path(__file__).resolve().parent.parent
    PROCESSED_DIR = BASE_DIR / "data" / "processed"
    REPORTS_DIR = BASE_DIR / "reports"
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(file_path, na_values=["", "NA", "N/A", "-"])
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    bad_rows = pd.DataFrame()
    issues_summary = {}

    # --- Missing Values ---
    missing_rows = df[df.isnull().any(axis=1)]
    if not missing_rows.empty:
        issues_summary['Missing Values'] = len(missing_rows)
        bad_rows = pd.concat([bad_rows, missing_rows.assign(issue='missing')])

    # --- Duplicate Rows ---
    duplicates = df[df.duplicated()]
    if not duplicates.empty:
        issues_summary['Duplicate Rows'] = len(duplicates)
        bad_rows = pd.concat([bad_rows, duplicates.assign(issue='duplicate')])

    # --- Negative Values ---
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    for col in numeric_cols:
        neg = df[df[col] < 0]
        if not neg.empty:
            bad_rows = pd.concat([bad_rows, neg.assign(issue=f"{col}_negative")])
            issues_summary[f'Negative Values ({col})'] = len(neg)

    # --- Outliers ---
    for col in numeric_cols:
        mean, std = df[col].mean(), df[col].std()
        outliers = df[(df[col] > mean + 3*std) | (df[col] < mean - 3*std)]
        if not outliers.empty:
            bad_rows = pd.concat([bad_rows, outliers.assign(issue=f"{col}_outlier")])
            issues_summary[f'Outliers ({col})'] = len(outliers)

    # --- Invalid Categories ---
    cat_cols = df.select_dtypes(include=['object']).columns
    for col in cat_cols:
        invalid = df[df[col].isnull()]
        if not invalid.empty:
            bad_rows = pd.concat([bad_rows, invalid.assign(issue=f"{col}_invalid_category")])
            issues_summary[f'Invalid Categories ({col})'] = len(invalid)

    # --- ML Anomalies ---
    if len(numeric_cols) > 0:
        ml_df = df[numeric_cols].dropna()
        if not ml_df.empty:
            iso = IsolationForest(contamination=0.01, random_state=42)
            iso_labels = iso.fit_predict(ml_df)
            iso_outliers = ml_df[iso_labels == -1]
            lof = LocalOutlierFactor(n_neighbors=20, contamination=0.01)
            lof_labels = lof.fit_predict(ml_df)
            lof_outliers = ml_df[lof_labels == -1]
            ml_outliers = pd.concat([iso_outliers, lof_outliers]).drop_duplicates()
            if not ml_outliers.empty:
                bad_rows = pd.concat([bad_rows, ml_outliers.assign(issue='ML_anomaly')])
                issues_summary['ML Anomalies'] = len(ml_outliers)

    # --- JSON Rules ---
    json_rows = pd.DataFrame()
    if rules_path and Path(rules_path).exists():
        with open(rules_path, "r") as f:
            rules = json.load(f)
        json_rows = apply_json_rules(df, rules)
        if not json_rows.empty:
            bad_rows = pd.concat([bad_rows, json_rows])
            issues_summary['JSON Rule Violations'] = len(json_rows)

    # --- Save HTML Report ---
    html_sections = [CSS_STYLE, "<h1>Data Validation Report</h1>"]
    html_sections.append(generate_html_section("Missing Values", missing_rows, len(missing_rows)))
    html_sections.append(generate_html_section("Duplicate Rows", duplicates, len(duplicates)))
    html_sections.append(generate_html_section("Negative Values", bad_rows[bad_rows['issue'].str.contains('_negative')], 
                                               sum(bad_rows['issue'].str.contains('_negative'))))
    html_sections.append(generate_html_section("Outliers", bad_rows[bad_rows['issue'].str.contains('_outlier')],
                                               sum(bad_rows['issue'].str.contains('_outlier'))))
    html_sections.append(generate_html_section("Invalid Categories", bad_rows[bad_rows['issue'].str.contains('_invalid_category')],
                                               sum(bad_rows['issue'].str.contains('_invalid_category'))))
    html_sections.append(generate_html_section("ML Anomalies", bad_rows[bad_rows['issue']=='ML_anomaly'],
                                               sum(bad_rows['issue']=='ML_anomaly')))
    html_sections.append(generate_html_section("JSON Rule Violations", json_rows, len(json_rows)))

    report_file = REPORTS_DIR / f"validation_summary_{Path(file_path).stem}.html"
    with open(report_file, "w") as f:
        f.write("<html><head><title>Validation Report</title></head><body>")
        f.write("".join(html_sections))
        f.write("</body></html>")

    return bad_rows, report_file, issues_summary

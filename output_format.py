import streamlit as st
import pandas as pd


# Helper functions for layout analysis results processing and rendering
def build_table_df(table: dict) -> pd.DataFrame:

    rows, cols = table["row_count"], table["column_count"]
    grid = [[""] * cols for _ in range(rows)]

    for cell in table["cells"]:
        grid[cell["row_index"]][cell["col_index"]] = cell["content"]
    return pd.DataFrame(grid)


def render_layout_results(result: dict):
    st.markdown("---")

    # Summary metrics
    handwritten = any(s.get("is_handwritten") for s in result.get("styles", []))
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pages", len(result["pages"]))
    col2.metric("Paragraphs", len(result["paragraphs"]))
    col3.metric("Tables", len(result["tables"]))
    col4.metric("Handwritten", "Yes" if handwritten else "No")

    st.markdown("---")

    # Two-column layout: JSON  |  Structured view
    json_col, structured_col = st.columns(2, gap="large")

    # LEFT: raw JSON
    with json_col:
        
        st.subheader("Raw JSON output")
        with st.expander("Full result JSON", expanded=False):
            st.json(result)

    # RIGHT: structured tables
    with structured_col:
        st.subheader("Structured view")

        # key-value pairs
        if result.get("key_value_pairs"):
            with st.expander(f"Key-Value Pairs ({len(result['key_value_pairs'])})", expanded=True):
                df_kv = pd.DataFrame(result["key_value_pairs"])
                st.dataframe(df_kv, width='stretch', hide_index=True)

        # paragraphs grouped by role
        paragraphs = result.get("paragraphs", [])

        if paragraphs:
            with st.expander(f"Paragraphs ({len(paragraphs)})", expanded=True):
                
                heading_roles = {"pageHeader", "title", "sectionHeading", "pageFooter", "pageNumber"}
                
                # Group paragraphs: each heading starts a new group with its following body paragraphs
                groups = []
                current_group = []
                
                for p in paragraphs:
                    role = p.get("role")
                    if role in heading_roles and current_group:
                        groups.append(current_group)
                        current_group = [p]
                    else:
                        current_group.append(p)
                if current_group:
                    groups.append(current_group)
                
                # Render each group as its own small table
                for group in groups:
                    heading = group[0]
                    body_items = group[1:]
                    
                    heading_role = heading.get("role", "Body")
                    rows = [{"Role": heading_role, 
                            "Content": heading["content"][:120] + ("…" if len(heading["content"]) > 120 else "")}]
                    
                    for p in body_items:
                        role = p.get("role", "Body")
                        rows.append({
                            "Role": role,
                            "Content": p["content"][:120] + ("…" if len(p["content"]) > 120 else "")
                        })
                    
                    df_group = pd.DataFrame(rows)
                    st.dataframe(df_group, width='stretch', hide_index=True)
                    st.markdown("")  # small spacing between groups

        # per-page lines
        for page in result["pages"]:
            with st.expander(
                f"Page {page['page_number']} — {len(page['lines'])} lines, "
                f"{len(page['selection_marks'])} selection marks"
            ):
                if page["lines"]:
                    df_lines = pd.DataFrame([
                        {
                            "Line #": l["line_index"],
                            "Content": l["content"],
                            "Words": l["word_count"],
                        }
                        for l in page["lines"]
                    ])
                    st.dataframe(df_lines, width='stretch', hide_index=True)

                if page["selection_marks"]:
                    st.markdown("**Selection marks**")
                    df_marks = pd.DataFrame([
                        {
                            "State": m["state"],
                            "Confidence": m["confidence"],
                        }
                        for m in page["selection_marks"]
                    ])
                    st.dataframe(df_marks, width='stretch', hide_index=True)

        # tables
        for table in result["tables"]:
            caption = f" — {table['caption']}" if table.get("caption") else ""
            with st.expander(
                f"Table {table['table_index']}{caption} — "
                f"{table['row_count']} rows × {table['column_count']} columns",
                expanded=False
            ):
                df_table = build_table_df(table)
                st.dataframe(df_table, width='stretch', hide_index=True)

        # figures
        if result.get("figures"):
            with st.expander(f"Figures ({len(result['figures'])})"):
                for fig in result["figures"]:
                    caption = fig.get("caption") or "No caption"
                    st.markdown(f"- **Figure {fig['id']}**: {caption}")
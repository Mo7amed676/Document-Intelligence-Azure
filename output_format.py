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


# Receipt helpers
def render_receipt_results(result: dict):
 
    st.markdown("---")
 
    receipts = result.get("receipts", [])
 
    # Summary metrics
    total_sum = sum(r["total"] for r in receipts if r.get("total") is not None)
    col1, col2, col3 = st.columns(3)
    col1.metric("Pages", result.get("page_count", "—"))
    col2.metric("Receipts found", len(receipts))
    col3.metric("Combined total", f"{total_sum:.2f}" if total_sum else "—")
 
    st.markdown("---")
 
    json_col, structured_col = st.columns(2, gap="large")
 
    # LEFT: raw JSON
    with json_col:
        st.subheader("Raw JSON output")
        with st.expander("Full result JSON", expanded=False):
            st.json(result)
 
    # RIGHT: structured view
    with structured_col:
        st.subheader("Structured view")
 
        if not receipts:
            st.info("No receipts were extracted from this document.")
            return
 
        for receipt in receipts:
            label = f"Receipt #{receipt['receipt_index'] + 1}"
            if receipt.get("merchant_name"):
                label += f" — {receipt['merchant_name']}"
            if receipt.get("total") is not None:
                label += f" (Total: {receipt['total']:.2f})"
 
            with st.expander(label, expanded=True):
 
                # Header info table
                header_rows = [
                    {"Field": "Receipt Type", "Value": receipt.get("receipt_type") or "—", "Confidence": "—"},
                    {"Field": "Country", "Value": receipt.get("country_region") or "—", "Confidence": "—"},
                    {"Field": "Merchant", "Value": receipt.get("merchant_name") or "—",
                     "Confidence": f"{receipt['merchant_name_confidence']:.2f}" if receipt.get("merchant_name_confidence") else "—"},
                    {"Field": "Address", "Value": receipt.get("merchant_address") or "—", "Confidence": "—"},
                    {"Field": "Phone", "Value": receipt.get("merchant_phone") or "—", "Confidence": "—"},
                    {"Field": "Date", "Value": receipt.get("transaction_date") or "—",
                     "Confidence": f"{receipt['transaction_date_confidence']:.2f}" if receipt.get("transaction_date_confidence") else "—"},
                    {"Field": "Time", "Value": receipt.get("transaction_time") or "—", "Confidence": "—"},
                    {"Field": "Subtotal", "Value": f"{receipt['subtotal']:.2f}" if receipt.get("subtotal") is not None else "—",
                     "Confidence": f"{receipt['subtotal_confidence']:.2f}" if receipt.get("subtotal_confidence") else "—"},
                    {"Field": "Tax", "Value": f"{receipt['tax']:.2f}" if receipt.get("tax") is not None else "—",
                     "Confidence": f"{receipt['tax_confidence']:.2f}" if receipt.get("tax_confidence") else "—"},
                    {"Field": "Tip", "Value": f"{receipt['tip']:.2f}" if receipt.get("tip") is not None else "—",
                     "Confidence": f"{receipt['tip_confidence']:.2f}" if receipt.get("tip_confidence") else "—"},
                    {"Field": "Total", "Value": f"{receipt['total']:.2f}" if receipt.get("total") is not None else "—",
                     "Confidence": f"{receipt['total_confidence']:.2f}" if receipt.get("total_confidence") else "—"},
                ]
                st.dataframe(pd.DataFrame(header_rows), hide_index=True, width='stretch')
 
                # Line items
                if receipt.get("items"):
                    st.markdown("**Line items**")
                    df_items = pd.DataFrame([
                        {
                            "Description": item.get("description") or "—",
                            "Qty": item.get("quantity") if item.get("quantity") is not None else "—",
                            "Unit Price": f"{item['price']:.2f}" if item.get("price") is not None else "—",
                            "Total": f"{item['total_price']:.2f}" if item.get("total_price") is not None else "—",
                        }
                        for item in receipt["items"]
                    ])
                    st.dataframe(df_items, hide_index=True, width='stretch')
                else:
                    st.caption("No line items extracted.")

def render_invoice_results(result: dict):

    st.markdown("---")

    invoices = result.get("invoices", [])

    # =========================
    # Summary Metrics
    # =========================
    total_sum = sum(
        inv.get("total") for inv in invoices if inv.get("total") is not None
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Pages", result.get("page_count", "—"))
    col2.metric("Invoices found", len(invoices))
    col3.metric(
        "Combined total",
        f"{total_sum:.2f}" if total_sum else "—"
    )

    st.markdown("---")

    json_col, structured_col = st.columns(2, gap="large")

    # =========================
    # LEFT: Raw JSON
    # =========================
    with json_col:
        st.subheader("Raw JSON output")
        with st.expander("Full result JSON", expanded=False):
            st.json(result)

    # =========================
    # RIGHT: Structured View
    # =========================
    with structured_col:
        st.subheader("Structured view")

        if not invoices:
            st.info("No invoices were extracted from this document.")
            return

        for invoice in invoices:

            label = f"Invoice #{invoice['invoice_index'] + 1}"

            if invoice.get("invoice_id"):
                label += f" — {invoice['invoice_id']}"

            if invoice.get("total") is not None:
                label += f" (Total: {invoice['total']:.2f})"

            with st.expander(label, expanded=True):

                # =========================
                # Header Table
                # =========================
                header_rows = [
                    {
                        "Field": "Invoice ID",
                        "Value": invoice.get("invoice_id") or "—",
                        "Confidence": f"{invoice['invoice_id_confidence']:.2f}"
                        if invoice.get("invoice_id_confidence") else "—",
                    },
                    {
                        "Field": "Invoice Date",
                        "Value": invoice.get("invoice_date") or "—",
                        "Confidence": f"{invoice['invoice_date_confidence']:.2f}"
                        if invoice.get("invoice_date_confidence") else "—",
                    },
                    {
                        "Field": "Due Date",
                        "Value": invoice.get("due_date") or "—",
                        "Confidence": f"{invoice['due_date_confidence']:.2f}"
                        if invoice.get("due_date_confidence") else "—",
                    },
                    {
                        "Field": "Vendor",
                        "Value": invoice.get("vendor_name") or "—",
                        "Confidence": f"{invoice['vendor_name_confidence']:.2f}"
                        if invoice.get("vendor_name_confidence") else "—",
                    },
                    {
                        "Field": "Customer",
                        "Value": invoice.get("customer_name") or "—",
                        "Confidence": f"{invoice['customer_name_confidence']:.2f}"
                        if invoice.get("customer_name_confidence") else "—",
                    },
                    {
                        "Field": "Subtotal",
                        "Value": f"{invoice['subtotal']:.2f}"
                        if invoice.get("subtotal") is not None else "—",
                        "Confidence": f"{invoice['subtotal_confidence']:.2f}"
                        if invoice.get("subtotal_confidence") else "—",
                    },
                    {
                        "Field": "Tax",
                        "Value": f"{invoice['tax']:.2f}"
                        if invoice.get("tax") is not None else "—",
                        "Confidence": f"{invoice['tax_confidence']:.2f}"
                        if invoice.get("tax_confidence") else "—",
                    },
                    {
                        "Field": "Total",
                        "Value": f"{invoice['total']:.2f}"
                        if invoice.get("total") is not None else "—",
                        "Confidence": f"{invoice['total_confidence']:.2f}"
                        if invoice.get("total_confidence") else "—",
                    },
                    {
                        "Field": "Amount Due",
                        "Value": f"{invoice['amount_due']:.2f}"
                        if invoice.get("amount_due") is not None else "—",
                        "Confidence": f"{invoice['amount_due_confidence']:.2f}"
                        if invoice.get("amount_due_confidence") else "—",
                    },
                ]

                st.dataframe(
                    pd.DataFrame(header_rows),
                    hide_index=True,
                    width="stretch"
                )

                # =========================
                # Line Items
                # =========================
                if invoice.get("items"):

                    st.markdown("**Line items**")

                    df_items = pd.DataFrame([
                        {
                            "Description": item.get("description") or "—",
                            "Qty": item.get("quantity") if item.get("quantity") is not None else "—",
                            "Unit Price": f"{item['unit_price']:.2f}" if item.get("unit_price") is not None else "—",
                            "Amount": f"{item['amount']:.2f}" if item.get("amount") is not None else "—",
                            "Product Code": item.get("product_code") or "—",
                        }
                        for item in invoice["items"]
                    ])

                    st.dataframe(df_items, hide_index=True, width="stretch")

                else:
                    st.caption("No line items extracted.")

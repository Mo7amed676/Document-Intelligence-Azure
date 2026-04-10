import logging
from config import get_client
from azure.ai.documentintelligence.models import DocumentAnalysisFeature

client = get_client()
logger = logging.getLogger(__name__)


def analyze_general(file_bytes: bytes) -> dict:
    if not file_bytes:
        raise ValueError("file_bytes must not be empty or None")

    logger.info("Starting document analysis")

    try:
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=file_bytes,
            content_type="application/octet-stream",
            features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS]  # enables KV extraction
        )
        result = poller.result()
    except Exception as e:
        raise RuntimeError(f"Document analysis failed: {e}") from e

    logger.info("Analysis complete")

    output = {
        "key_value_pairs": [],
        "page_count": len(result.pages) if result.pages else 0,
        "full_text": "",
        "pages": [],
        "paragraphs": [],
        "tables": [],

    }

    # Process each page
    if result.pages:
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "angle": page.angle,
                "width": page.width,
                "height": page.height,
                "unit": page.unit,
                "lines": [],
                "selection_marks": [],
            }

            # Extract lines
            if page.lines:
                for line_idx, line in enumerate(page.lines):
                    line_data = {
                        "line_index": line_idx,
                        "content": line.content,
                        "word_count": len(line.content.split()) if line.content else 0,
                        "confidence": round(line.confidence, 4) if hasattr(line, 'confidence') and line.confidence else None,
                    }
                    page_data["lines"].append(line_data)

            # Extract selection marks
            if page.selection_marks:
                for mark in page.selection_marks:
                    mark_data = {
                        "state": mark.state,
                        "confidence": round(mark.confidence, 4) if hasattr(mark, 'confidence') and mark.confidence else None,
                    }
                    page_data["selection_marks"].append(mark_data)

            output["pages"].append(page_data)

    # Extract all text content
    if result.pages:
        all_text = []
        for page in result.pages:
            for line in (page.lines or []):
                all_text.append(line.content)
        output["full_text"] = "\n".join(all_text)

    # Extract key-value pairs
    for kv in (result.key_value_pairs or []):
        output["key_value_pairs"].append({
            "key": kv.key.content if kv.key else "",
            "value": kv.value.content if kv.value else "",
            "confidence": round(kv.confidence, 4) if kv.confidence is not None else None,
        })

    # Extract paragraphs
    if result.paragraphs:
        for para in result.paragraphs:
            output["paragraphs"].append({
                "role": para.role or "body",
                "content": para.content,
                "bounding_regions": [
                    {
                        "page_number": r.page_number,
                        "polygon": r.polygon,
                    }
                    for r in (para.bounding_regions or [])
                ],
                "spans": [
                    {"offset": s.offset, "length": s.length}
                    for s in (para.spans or [])
                ],
            })

    # Extract tables
    if result.tables:
        for table_idx, table in enumerate(result.tables):
            table_data = {
                "table_index": table_idx,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "caption": None,
                "bounding_regions": [
                    {
                        "page_number": r.page_number,
                        "polygon": r.polygon,
                    }
                    for r in (table.bounding_regions or [])
                ],
                "cells": [],
            }

            # table caption (if present)
            if hasattr(table, "caption") and table.caption:
                table_data["caption"] = table.caption.content

            # Extract each cell
            for cell in table.cells:
                table_data["cells"].append({
                    "kind": getattr(cell, "kind", "content") or "content",
                    "row_index": cell.row_index,
                    "col_index": cell.column_index,
                    "content": cell.content,
                    "bounding_regions": [
                        {
                            "page_number": r.page_number,
                            "polygon": r.polygon,
                        }
                        for r in (cell.bounding_regions or [])
                    ],
                    "spans": [
                        {"offset": s.offset, "length": s.length}
                        for s in (cell.spans or [])
                    ],
                })

            output["tables"].append(table_data)

    return output
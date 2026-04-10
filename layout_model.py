from azure.ai.documentintelligence.models import AnalyzeResult # result type returned by Azure

from config import get_client


def _in_span(word, spans):
    """"
    Check if a word lies inside any of the given spans(text range).
    """
    for span in spans:
        # if the start of the word >= span start and the end of the word <= span end:
        if word.span.offset >= span.offset and (
            word.span.offset + word.span.length
        ) <= (span.offset + span.length):
            return True
    return False


def get_words(page, line):
    """
    Extract words that belong to a specific line based on span matching.
    """
    result = []
    for word in page.words:
        # Check if word belongs to this line.
        if _in_span(word, line.spans):
            result.append(word)
    return result


def analyze_layout(file_bytes: bytes) -> dict:
    """
    Send document bytes to Azure prebuilt-layout and return a structured dict
    that mirrors the Azure REST response closely.
    """

    # Create client and call Azure
    client = get_client()

    # Send the document bytes to Azure's prebuilt layout model.
    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=file_bytes,
        content_type="application/octet-stream", # sending raw binary data
    )

    # Get the results (Page, Line, Word, SelectionMark, Paragraph, Table, Figure data)
    result: AnalyzeResult = poller.result()

    # output dict that will be returned
    output = {
        "content": result.content or "",
        "styles": [],
        "pages": [],
        "paragraphs": [],
        "tables": [],
        "figures": [],
    }

    # Checks if any text is handwritten vs printed, and how confident Azure is about it
    if result.styles:
        for style in result.styles:
            output["styles"].append({
                "is_handwritten": style.is_handwritten,
                "confidence": round(style.confidence, 4) if style.confidence else None,
                "spans": [
                    {"offset": s.offset, "length": s.length}
                    for s in (style.spans or [])
                ],
            })

    # Process each page and collect its metadata and elements (words, lines, marks)
    for page in result.pages:
        page_data = {
            "page_number": page.page_number,
            "angle": page.angle,
            "width": page.width,
            "height": page.height,
            "unit": page.unit,
            "words": [],
            "lines": [],
            "selection_marks": [],
        }

        # Extract all words on the page with their text, position, and confidence
        if page.words:
            for word in page.words:
                page_data["words"].append({
                    "content": word.content,
                    "confidence": round(word.confidence, 4),
                    "span": {
                        "offset": word.span.offset,
                        "length": word.span.length,
                    },
                    "polygon": word.polygon,
                })

        # Extract lines and link them with their words using span matching
        if page.lines:
            for line_idx, line in enumerate(page.lines):
                words = get_words(page, line)
                page_data["lines"].append({
                    "line_index": line_idx,
                    "content": line.content,
                    "word_count": len(words),
                    "polygon": line.polygon,
                    "spans": [
                        {"offset": s.offset, "length": s.length}
                        for s in (line.spans or [])
                    ],
                })

        # Extract selection marks(checkboxes) with their state and position
        if page.selection_marks:
            for mark in page.selection_marks:
                page_data["selection_marks"].append({
                    "state": mark.state,
                    "confidence": round(mark.confidence, 4),
                    "polygon": mark.polygon,
                    "span": {
                        "offset": mark.span.offset,
                        "length": mark.span.length,
                    },
                })

        # Add the processed page data to the final output
        output["pages"].append(page_data)

    # Extract paragraphs with their role (title, header, body, etc.) and location
    if result.paragraphs:
        for para in result.paragraphs:
            output["paragraphs"].append({
                "role": para.role or "body",          # title, sectionHeading, pageHeader, pageFooter, pageNumber, body
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

    # Extract tables including structure (row, col) and all cells with their content and position
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

            # Extract each cell with its position, type, and content
            for cell in table.cells:
                table_data["cells"].append({
                    "kind": getattr(cell, "kind", "content") or "content",   # columnHeader, rowHeader, content
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

            # Add the processed table to the final output
            output["tables"].append(table_data)

    # Extract figures with captions and positions if available
    if hasattr(result, "figures") and result.figures:
        for fig in result.figures:
            fig_data = {
                "id": fig.id,
                "caption": fig.caption.content if (hasattr(fig, "caption") and fig.caption) else None,
                "bounding_regions": [
                    {
                        "page_number": r.page_number,
                        "polygon": r.polygon,
                    }
                    for r in (fig.bounding_regions or [])
                ],
                "spans": [
                    {"offset": s.offset, "length": s.length}
                    for s in (fig.spans or [])
                ],
            }
            output["figures"].append(fig_data)

    return output
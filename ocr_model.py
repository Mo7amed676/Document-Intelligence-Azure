import logging
from azure.ai.documentintelligence.models import AnalyzeResult
from config import get_client

logger = logging.getLogger(__name__)

def get_words(page, line):
    """
    Extract words that belong to a specific line based on span matching.
    """
    result = []
    if not page.words:
        return result
    
    for word in page.words:
        for span in (line.spans or []):
            if word.span.offset >= span.offset and (
                word.span.offset + word.span.length
            ) <= (span.offset + span.length):
                result.append(word)
                break
    return result

def analyze_ocr(file_bytes: bytes) -> dict:
    """
    Send document bytes to Azure prebuilt-read (OCR) and return a structured dict
    that mimics the expected format for render_layout_results.
    """
    if not file_bytes:
        raise ValueError("file_bytes must not be empty or None")

    logger.info("Starting OCR analysis")

    client = get_client()

    try:
        # Using prebuilt-read for OCR
        poller = client.begin_analyze_document(
            "prebuilt-read",
            body=file_bytes,
            content_type="application/octet-stream"
        )
        result: AnalyzeResult = poller.result()
    except Exception as e:
        raise RuntimeError(f"OCR analysis failed: {e}") from e

    logger.info("OCR Analysis complete")

    # Mirroring the output structure of layout_model.py to work with output_format.py
    output = {
        "content": result.content or "",
        "styles": [],
        "pages": [],
        "paragraphs": [],  # prebuilt-read doesn't typically extract paragraphs
        "tables": [],      # prebuilt-read doesn't extract tables
        "figures": [],     # prebuilt-read doesn't extract figures
        "key_value_pairs": [] # prebuilt-read doesn't extract KVs
    }

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

    if result.pages:
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

            if page.words:
                for word in page.words:
                    page_data["words"].append({
                        "content": word.content,
                        "confidence": round(word.confidence, 4) if hasattr(word, 'confidence') and word.confidence else None,
                        "span": {
                            "offset": word.span.offset,
                            "length": word.span.length,
                        } if hasattr(word, 'span') and word.span else None,
                        "polygon": word.polygon if hasattr(word, 'polygon') else None,
                    })

            if hasattr(page, 'lines') and page.lines:
                for line_idx, line in enumerate(page.lines):
                    words = get_words(page, line)
                    page_data["lines"].append({
                        "line_index": line_idx,
                        "content": line.content,
                        "word_count": len(words) if words else (len(line.content.split()) if line.content else 0),
                        "polygon": line.polygon if hasattr(line, 'polygon') else None,
                        "spans": [
                            {"offset": s.offset, "length": s.length}
                            for s in (line.spans or [])
                        ],
                    })
            
            if hasattr(page, 'selection_marks') and page.selection_marks:
                for mark in page.selection_marks:
                    page_data["selection_marks"].append({
                        "state": mark.state,
                        "confidence": round(mark.confidence, 4) if hasattr(mark, 'confidence') and mark.confidence else None,
                        "polygon": mark.polygon if hasattr(mark, 'polygon') else None,
                        "span": {
                            "offset": mark.span.offset,
                            "length": mark.span.length,
                        } if hasattr(mark, 'span') and mark.span else None,
                    })

            output["pages"].append(page_data)

    return output

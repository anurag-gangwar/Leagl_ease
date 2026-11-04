import os
import re


class DocumentExtractionError(RuntimeError):
    """A user-safe error raised when a document cannot be read."""


def extraction_error_message(error: Exception) -> str:
    """Map parser failures to actionable, provider-free browser messages."""
    details = str(error or '').lower()
    error_type = type(error).__name__.lower()

    if isinstance(error, DocumentExtractionError):
        return str(error)
    if isinstance(error, PermissionError) or 'permission' in details:
        return 'The file could not be opened. Move it to a local folder and try again.'
    if 'password' in details or 'encrypted' in details:
        return 'This PDF is password-protected. Remove the password and upload it again.'
    if 'no such file' in details or 'not found' in details:
        return 'The uploaded file is no longer available. Select it again from a local folder.'
    if 'memory' in details or 'too large' in details:
        return 'This document is too large to process. Try a smaller file or split the PDF.'
    if 'pdf' in details or 'fitz' in error_type or 'pdf' in error_type:
        return 'This PDF appears damaged or unsupported. Re-save it as a standard PDF and try again.'
    return 'The file could not be read. Try a local, unencrypted PDF or a plain-text (.txt) file.'


def extract_text(filepath: str) -> str:
    """
    Extract text from a PDF or plain-text file.
    Tries PyMuPDF first; falls back to pdfplumber, then pytesseract for scanned PDFs.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.txt':
        return _read_text_file(filepath)
    elif ext == '.pdf':
        return _extract_from_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _read_text_file(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _extract_from_pdf(filepath: str) -> str:
    errors = []

    # Try PyMuPDF (fitz) first — fastest and most accurate.
    try:
        import fitz  # PyMuPDF
        text = _extract_with_pymupdf(filepath)
        if _has_meaningful_text(text):
            return text
    except Exception as exc:
        errors.append(exc)

    # Fallback: pdfplumber
    try:
        import pdfplumber
        text = _extract_with_pdfplumber(filepath)
        if _has_meaningful_text(text):
            return text
    except Exception as exc:
        errors.append(exc)

    # Fallback: OCR via pytesseract (for scanned/image-only PDFs).
    try:
        text = _extract_with_ocr(filepath)
        if _has_meaningful_text(text):
            return text
    except DocumentExtractionError:
        raise
    except Exception as exc:
        errors.append(exc)

    raise DocumentExtractionError(
        'This PDF does not contain readable text. It may be scanned or image-only. '
        'Save it as a searchable PDF, or install OCR support and try again.'
    ) from (errors[-1] if errors else None)


def _has_meaningful_text(text: str) -> bool:
    """Ignore page markers/whitespace when deciding whether extraction worked."""
    if not text:
        return False
    alphanumeric = re.sub(r'[^\w]', '', text, flags=re.UNICODE)
    return len(alphanumeric) >= 50


def _extract_with_pymupdf(filepath: str) -> str:
    import fitz
    doc = fitz.open(filepath)
    pages_text = []
    for page_num, page in enumerate(doc):
        page_text = page.get_text("text")
        pages_text.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
    doc.close()
    return "\n".join(pages_text)


def _extract_with_pdfplumber(filepath: str) -> str:
    import pdfplumber
    pages_text = []
    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ''
            pages_text.append(f"\n--- Page {page_num + 1} ---\n{page_text}")
    return "\n".join(pages_text)


def _extract_with_ocr(filepath: str) -> str:
    """Use pytesseract OCR for scanned PDFs, rendering pages with PyMuPDF."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise DocumentExtractionError(
            'This PDF appears to be scanned. OCR is not installed; '
            'install the project requirements and Tesseract, then try again.'
        ) from exc

    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise DocumentExtractionError(
            'This PDF appears to be scanned. Install Tesseract OCR '
            '(macOS: brew install tesseract) and try again.'
        ) from exc

    pages_text = []
    doc = fitz.open(filepath)
    try:
        for i, page in enumerate(doc):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes('RGB', [pixmap.width, pixmap.height], pixmap.samples)
            text = pytesseract.image_to_string(image, lang='eng')
            pages_text.append(f"\n--- Page {i + 1} (OCR) ---\n{text}")
    finally:
        doc.close()

    result = "\n".join(pages_text)
    if not _has_meaningful_text(result):
        raise DocumentExtractionError(
            'OCR completed but could not find readable text in this PDF. '
            'Please upload a clearer document.'
        )
    return result


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize line breaks."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def split_into_chunks(text: str, max_chars: int = 12000) -> list:
    """
    Split large contract text into manageable chunks for LLM processing.
    Tries to split at paragraph boundaries.
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split('\n\n')
    chunks = []
    current = ''

    for para in paragraphs:
        if len(current) + len(para) < max_chars:
            current += '\n\n' + para
        else:
            if current:
                chunks.append(current.strip())
            current = para

    if current:
        chunks.append(current.strip())

    return chunks

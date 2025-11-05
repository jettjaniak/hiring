"""
HTTP response utility functions
"""
from io import BytesIO
from fastapi.responses import RedirectResponse, StreamingResponse


def redirect_to(url: str) -> RedirectResponse:
    """
    Create a standard redirect response.

    Eliminates the pattern:
        return RedirectResponse(url="/some/path", status_code=302)

    Args:
        url: URL to redirect to

    Returns:
        RedirectResponse with status code 302
    """
    return RedirectResponse(url=url, status_code=302)


def stream_document(doc_bytes: bytes, filename: str, media_type: str) -> StreamingResponse:
    """
    Stream a document file as a download.

    Args:
        doc_bytes: Document content as bytes
        filename: Filename to use in Content-Disposition header
        media_type: MIME type (e.g. "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    Returns:
        StreamingResponse configured for file download
    """
    return StreamingResponse(
        BytesIO(doc_bytes),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

from fastapi import HTTPException, Request, status


def reject_oversized_request(
    request: Request,
    max_bytes: int,
    detail: str,
) -> None:
    content_length = request.headers.get("content-length", "").strip()
    if not content_length:
        return

    try:
        request_size = int(content_length)
    except ValueError:
        return

    if request_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=detail,
        )

"""Serve the built frontend after normal API routing has run."""

from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException


def serve_frontend(app: FastAPI, directory: Path) -> None:
    """Serve built assets and let the browser resolve non-API page routes."""
    files = StaticFiles(directory=directory)

    @app.exception_handler(HTTPStatus.NOT_FOUND)
    async def frontend_or_not_found(
        request: Request, not_found: HTTPException
    ) -> Response:
        path = files.get_path(request.scope)
        file_path = Path(path)
        parts = file_path.parts
        if (
            request.method not in {"GET", "HEAD"}
            or (parts and parts[0] == "api")
            or "\x00" in path
            or ".." in request.url.path.split("/")
        ):
            return await http_exception_handler(request, not_found)

        candidates = [path]
        if not parts or (
            parts[0] != "assets"
            and not parts[-1].startswith(".")
            and (not file_path.suffix or file_path.parent == Path("note"))
        ):
            candidates.append("index.html")

        for candidate in candidates:
            try:
                return await files.get_response(candidate, request.scope)
            except HTTPException as exc:
                if exc.status_code != HTTPStatus.NOT_FOUND:
                    return await http_exception_handler(request, exc)
        return await http_exception_handler(request, not_found)

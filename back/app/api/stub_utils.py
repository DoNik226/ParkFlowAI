from typing import Any

from fastapi.responses import JSONResponse


def not_implemented_response(method: str, path: str, contract: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "message": "Endpoint stub registered but not implemented yet",
            "stub": True,
            "method": method,
            "path": path,
            "contract": contract,
        },
    )

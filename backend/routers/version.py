from fastapi import APIRouter

from version import get_version_info

router = APIRouter(tags=["version"])


@router.get("/version")
async def get_version():
    return get_version_info()

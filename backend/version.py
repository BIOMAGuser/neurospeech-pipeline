from config import settings


def get_version_info():
    return {
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME,
        "build_date": settings.BUILD_DATE,
        "features": [
            "German speech analysis",
            "SQLite database integration",
            "Multi-task audio processing",
            "Real-time transcription",
        ],
    }

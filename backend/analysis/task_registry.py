"""
Central task registry — single source of truth for all task types.

To add a new task:
1. Create backend/analysis/analyse_newtask.py with an analyze function
2. Add an entry to _build_registry() below
3. Add whisper/gpt prompts in prompts.yml (if needed)
4. Add frontend config in frontend/src/constants/tasks.ts
5. Add to TaskType union in frontend/src/types/audio.ts
"""

from typing import Dict, Any, Callable, Optional


class TaskDef:
    """Definition of a single task type."""

    def __init__(
        self,
        analyze_fn: Callable[..., Dict[str, Any]],
        requires_api_key: bool,
        points_key: str = "points",
    ):
        self.analyze_fn = analyze_fn
        self.requires_api_key = requires_api_key
        self.points_key = points_key

    def analyze(self, transcript: str, api_key: str = None) -> Dict[str, Any]:
        if self.requires_api_key:
            return self.analyze_fn(transcript, api_key=api_key)
        return self.analyze_fn(transcript)

    def extract_points(self, metrics: Dict[str, Any]) -> int:
        return metrics.get(self.points_key, 0)


_registry: Optional[Dict[str, TaskDef]] = None


def _build_registry() -> Dict[str, TaskDef]:
    from analysis.analyse_veggie import analyze_veggie
    from analysis.analyse_saying import analyze_saying
    from analysis.analyse_picture import analyze_picture

    return {
        "veggie": TaskDef(
            analyze_fn=analyze_veggie,
            requires_api_key=True,
            points_key="points",
        ),
        "saying": TaskDef(
            analyze_fn=analyze_saying,
            requires_api_key=True,
            points_key="points",
        ),
        "picture": TaskDef(
            analyze_fn=analyze_picture,
            requires_api_key=False,
            points_key="pic_points",
        ),
    }


def get_task_registry() -> Dict[str, TaskDef]:
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def get_task_def(task_name: str) -> Optional[TaskDef]:
    return get_task_registry().get(task_name)


def valid_task_names() -> list:
    return list(get_task_registry().keys())

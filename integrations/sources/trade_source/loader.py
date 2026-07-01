from pathlib import Path


class TradeSourceLoader:
    """Phase 1 placeholder for upstream trade project access."""

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)

    def exists(self) -> bool:
        return self.project_root.exists()


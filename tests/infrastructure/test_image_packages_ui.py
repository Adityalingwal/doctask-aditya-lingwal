from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_the_built_image_contains_the_production_ui() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY --from=ui-build /ui/dist /workspace/ui/dist" in dockerfile
    assert "ui/\n" not in dockerignore
    assert "ui/node_modules/" in dockerignore
    assert "ui/dist/" in dockerignore

from pathlib import Path


def test_m0_01_artifact_exists_with_expected_content() -> None:
    artifact_path = Path(__file__).with_name("test_m0_01.txt")

    assert artifact_path.is_file()
    assert artifact_path.read_text(encoding="utf-8") == "M0-01 completed\n"

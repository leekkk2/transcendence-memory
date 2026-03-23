from transcendence_memory.cli import app


def test_doctor_reports_auto_fixable_for_missing_roots(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
        ],
    )
    assert result.exit_code == 1
    assert "auto-fixable" in result.stdout


def test_doctor_fix_creates_missing_directories(bootstrap_roots, runner) -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--config-path",
            str(bootstrap_roots["config_root"]),
            "--secret-path",
            str(bootstrap_roots["secret_root"]),
            "--fix",
        ],
    )
    assert result.exit_code == 1
    assert bootstrap_roots["config_root"].exists()
    assert bootstrap_roots["secret_root"].exists()
    assert "needs input" in result.stdout or "auto-fixable" in result.stdout

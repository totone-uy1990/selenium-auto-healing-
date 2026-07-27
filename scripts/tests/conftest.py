"""Shared pytest fixtures for the heal_locator test suite."""

import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import heal_locator  # noqa: E402

FRAMEWORK_TRACE = """customExceptions.FrameworkException: No se pudo encontrar el elemento con el localizador: By.xpath: //label[text()='Username']/following-sibling::div//input tras el tiempo de espera configurado.
\tat pages.BasePage.findElement(BasePage.java:111)
\tat pages.LoginPage.enterUsername(LoginPage.java:30)
\tat steps.LoginSteps.the_user_enters_credentials(LoginSteps.java:42)
Caused by: org.openqa.selenium.TimeoutException: Expected condition failed
\tat org.openqa.selenium.support.ui.WebDriverWait.timeoutException(WebDriverWait.java:84)
"""

VERIFICATION_TRACE = """customExceptions.VerificationException: El mensaje de éxito no se mostró
\tat assertions.CustomAssertions.assertTrue(CustomAssertions.java:20)
\tat steps.SuccessSteps.the_success_modal_is_shown(SuccessSteps.java:18)
"""

GENERIC_TRACE = """java.lang.NullPointerException: Cannot invoke method on null
\tat steps.CheckoutSteps.something(CheckoutSteps.java:10)
"""


def make_result_file(directory: Path, name: str, trace: str, status: str = "failed") -> Path:
    """Write a minimal Allure *-result.json fixture and return its path."""
    payload = {
        "name": name,
        "fullName": f"com.qa.features.{name}",
        "status": status,
        "statusDetails": {"message": trace.splitlines()[0], "trace": trace},
    }
    path = directory / f"{uuid.uuid4()}-result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def results_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "allure-results"
    directory.mkdir()
    return directory


@pytest.fixture
def locators_dir(tmp_path: Path) -> Path:
    """A locator directory mirroring the real JSON contract."""
    directory = tmp_path / "locators"
    directory.mkdir()
    (directory / "login.json").write_text(
        json.dumps(
            {
                "userNameField": {
                    "type": "xpath",
                    "value": "//label[text()='Username']/following-sibling::div//input",
                },
                "loginButton": {"type": "xpath", "value": "//button[text()='Login']"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (directory / "success.json").write_text(
        json.dumps({"msgStatus": {"type": "xpath", "value": "//h2 | //h4"}}, indent=2),
        encoding="utf-8",
    )
    return directory

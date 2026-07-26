"""RED (task 2.2): deterministic failure classification.

FrameworkException traces are locator-eligible and expose the Selenium
``By.toString()`` type+value; VerificationException and any other exception
are real bugs and must never reach the LLM.
"""

from conftest import FRAMEWORK_TRACE, GENERIC_TRACE, VERIFICATION_TRACE, make_result_file

import heal_locator


def _classify(trace: str) -> heal_locator.Classification:
    return heal_locator.classify_trace(trace)


def test_framework_exception_is_locator_eligible():
    result = _classify(FRAMEWORK_TRACE)
    assert result.kind == "locator"


def test_framework_exception_extracts_by_type_and_value():
    result = _classify(FRAMEWORK_TRACE)
    assert result.locator_type == "xpath"
    assert result.locator_value == "//label[text()='Username']/following-sibling::div//input"


def test_css_selector_maps_to_json_css_type():
    trace = (
        "customExceptions.FrameworkException: No se pudo encontrar el elemento con el "
        "localizador: By.cssSelector: div[role='alert'] tras el tiempo de espera configurado.\n"
        "\tat pages.BasePage.findElement(BasePage.java:111)\n"
    )
    result = _classify(trace)
    assert result.kind == "locator"
    assert result.locator_type == "css"
    assert result.locator_value == "div[role='alert']"


def test_verification_exception_is_a_bug():
    result = _classify(VERIFICATION_TRACE)
    assert result.kind == "bug"
    assert result.locator_type is None
    assert result.locator_value is None


def test_other_exceptions_are_bugs():
    result = _classify(GENERIC_TRACE)
    assert result.kind == "bug"


def test_framework_exception_without_by_is_a_bug():
    trace = (
        "customExceptions.FrameworkException: No se definió el archivo JSON "
        "(locatorFile) para esta Page.\n\tat pages.BasePage.getBy(BasePage.java:94)\n"
    )
    result = _classify(trace)
    assert result.kind == "bug"


def test_classify_result_uses_scenario_trace(results_dir):
    path = make_result_file(results_dir, "Login with valid credentials", FRAMEWORK_TRACE)
    scenario = heal_locator.parse_result_file(path)
    result = heal_locator.classify_result(scenario)
    assert result.kind == "locator"
    assert result.scenario == "Login with valid credentials"
    assert result.locator_type == "xpath"

# Agent Guidelines for QA-Framework

Welcome! You are an AI agent operating within the `QA-Framework` repository. This project is an enterprise-grade test automation architecture built with **Java 24**, **Selenium**, **Cucumber**, and **JUnit 5 Platform**. 

These instructions dictate your behavior, coding style, and tool usage when operating in this codebase.

## 1. Build, Lint, and Test Commands

Always verify your changes by compiling and running tests. NEVER assume your code works without running the appropriate Gradle task.

*   **Clean and Compile:**
    ```bash
    ./gradlew clean compileTestJava
    ```
*   **Run All Tests:**
    ```bash
    ./gradlew clean test
    ```
*   **Run a Single Test (via Cucumber Tags):**
    This is the preferred method for isolated verification.
    ```bash
    ./gradlew test -Dcucumber.filter.tags="@YourTag"
    ```
*   **Generate & Serve Allure Report:**
    ```bash
    ./gradlew allureServe
    ```
    *(Note: Allure results are stored in `build/allure-results`)*

## 2. Project Structure

Adhere strictly to the established architectural boundaries:
*   `src/test/java/pages/`: Page Object Model (POM) classes. One class per logical UI page.
*   `src/test/java/steps/`: Cucumber Step Definitions. Keep these thin; delegate logic to pages.
*   `src/test/java/coreLocators/`: Core framework logic for parsing locators.
*   `src/test/java/customExceptions/`: Framework-specific exception handling.
*   `src/test/resources/features/`: Gherkin (`.feature`) files.
*   `src/test/resources/locators/`: Centralized JSON files containing UI element locators.

## 3. Code Style & Guidelines

### Java & Frameworks
*   **Language:** Java 24. Use modern features where appropriate (e.g., records, var, switch expressions, text blocks, pattern matching).
*   **Lombok:** Use `@Getter`, `@Setter`, `@Data`, and `@Builder` to reduce boilerplate, especially in data models (found in `src/test/java/steps/models/`).
*   **Assertions:** We use JUnit 5 (`org.junit.jupiter.api.Assertions`) wrapped in our custom assertion handler (`src/test/java/assertions/CustomAssertions.java`). Do not use raw TestNG assertions.

### Naming Conventions
*   **Classes/Interfaces:** `PascalCase` (e.g., `LoginPage`, `SuccessPage`). Page Objects MUST end with `Page`. Test runners MUST end with `Runner`.
*   **Methods/Variables:** `camelCase` (e.g., `clickLoginButton`, `userNameInput`).
*   **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`).
*   **Feature Files:** `snake_case.feature` (e.g., `practice_form.feature`).

### Imports
*   **DO NOT** use wildcard imports (e.g., `import java.util.*;`). Expand all imports explicitly.
*   Group imports: 1. Java standard libraries, 2. Third-party libraries (Selenium, JUnit, Cucumber), 3. Internal project imports.

### Error Handling
*   Avoid generic `Exception`. 
*   Always throw framework-specific exceptions located in `customExceptions/`:
    *   `AutomationException`: For logical test failures.
    *   `FrameworkException`: For internal framework issues (e.g., missing locator file).
    *   `VerificationException`: For assertion/validation failures.

## 4. Specific Rules for AI Agents

When implementing features, fixing bugs, or writing tests, you must follow these operational rules:

### A. Driver Encapsulation (MANDATORY)
**THE DRIVER MUST NEVER BE USED DIRECTLY OUTSIDE OF BASEPAGE.**

*   **BasePage**: The only layer that "sees" the Driver. Contains generic wrappers like `clickElement`, `write`, `getWebElement`, etc.
*   **Page Objects**: Inherit from `BasePage`. Orchestrate generic methods into business actions (e.g., `loginAs(user)`, `addProductToCart()`).
*   **Step Definitions**: Only interact with Page Objects. They know nothing about Selenium or `By` locators.

If you need a new Selenium action (e.g., drag and drop), add it to `BasePage` first as a generic wrapper, then use it from your Page Object. Never call `getDriverFromThread()` from a Step Definition.

### B. Custom Assertions (MANDATORY)
Use the custom assertion handler instead of raw JUnit assertions:
```java
// CORRECTO
CustomAssertions.assertTrue(page.isSuccessModalDisplayed(), "Modal not displayed");

// INCORRECTO
Assertions.assertTrue(page.isSuccessModalDisplayed(), "Modal not displayed");
```

All assertions should go through `CustomAssertions.java` which throws proper framework exceptions.

### C. Dynamic Locator Management
*   The framework supports **two modalities** for locators. Always ask or deduce from context which one to use:
    1.  **JSON-based (Preferred)**: Locators reside in JSON files under `src/test/resources/locators/` (e.g., `login.json`, `practice_form.json`). Access them via `LocatorRepository.getLocator("archivo", "key")`.
    2.  **Traditional**: Using `private final By` instance variables in the Page class.
*   When using JSON modality: When creating a new Page Object, first `read` or create the corresponding JSON file, then map the keys using the `LocatorRepository` mechanism.
*   When using Traditional modality: Define locators as `private final By` variables at the top of the Page class.

### D. Synchronization & Waits
*   **NEVER use `Thread.sleep()`**.
*   Rely on explicit waits (`WebDriverWait`) or the framework's internal waiting mechanisms configured in the `BasePage`.

### E. BDD (Behavior-Driven Development) Protocol
*   When asked to write a new test, start by writing the `Gherkin` scenario in `src/test/resources/features/`.
*   Keep scenarios declarative (business-focused), not imperative (UI-focused). 
    *   *Good:* `When the user logs in with valid credentials`
    *   *Bad:* `When the user clicks the username field and types "admin" and clicks the password field...`
*   Re-use existing step definitions whenever possible to avoid duplication. Use `grep` or `glob` to search existing steps in `src/test/java/steps/`.

### F. System Interaction Protocol
*   **Tool Usage:** Use `bash` to run gradle tasks. Wait for the compilation/test output.
*   **Pathing:** Always construct absolute paths or rely on the `workdir` param when using `bash` tools.
*   **No Proactive Destructive Actions:** Do not delete code without confirming the impact.

## 5. Typical Agent Workflow Example
If asked to "add a new login test for locked users":
1.  Read `login.json` and ensure the error message locator exists.
2.  Edit `Role-Based-login-Flow/Login.feature` to add the scenario.
3.  Check `loginFlowSteps.java` to see if steps exist. Add missing steps.
4.  Update `LoginPage.java` to handle the locked user UI interactions, fetching locators dynamically.
5.  Run `./gradlew test -Dcucumber.filter.tags="@LockedUser"` using `bash`.
6.  Verify success and notify the user.

## 6. Code Formatting Guidelines

*   **Braces**: Always use braces for control statements, even for single-line bodies.
*   **Line Length**: Keep lines under 120 characters when possible.
*   **Method Length**: Prefer small, focused methods (under 30 lines).
*   **Indentation**: 4 spaces (no tabs).
*   **Final Variables**: Use `final` for parameters and local variables where appropriate.
*   **Generics**: Use proper generic types (e.g., `ArrayList<String>` not raw `ArrayList`).

## 7. Additional Resources

- **[Standards](.opencode/standards/)**: Code standards and conventions (ALWAYS apply)
- **[Skills](skills/)**: Implementation patterns and techniques
- **[Workflows](workflows/)**: Team workflows and processes

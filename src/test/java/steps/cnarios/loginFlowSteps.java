package steps.cnarios;

import assertions.CustomAssertions;
import io.cucumber.java.en.*;
import pages.cnarios.LoginPage;
import steps.models.cnarios.loginFlow.LoginData;

public class loginFlowSteps {
    final private LoginPage loginFlow = new LoginPage();
    final private CustomAssertions verify = new CustomAssertions();

    @Given("the user is on the Cnarios test_login page {string}")
    public void navigatetoLoginFlow(String url) {
        loginFlow.navigateTo(url);
    }

    @When("the user enters his credentials:")
    public void fillingUsernameField(LoginData loginData) {
        loginFlow.writeUsernameField(loginData.getUsername());
        loginFlow.writePasswordField(loginData.getPassword());
    }

    @And("clicks on the login button")
    public void clickingButtonLogin() {
        loginFlow.clickButton();
    }

    @Then("the user should see an error message saying {string}")
    public void validatingErrorMessageLogin(String message) {
        verify.assertAnyElementContainsText(loginFlow.getErrorMessages(), message);
    }

    @Then("the user should be redirected to the {string} page")
    public void validatingWeAreDashBoardPanel(String expectedMessage) {
        verify.assertContainsText(loginFlow.dashBoardElement(),
                expectedMessage,
                "Mensaje de Admin");
    }

    @And("the user should see a welcome message containing {string}")
    public void verifyWelcomeMessage(String expectedMessage) {
        verify.assertContainsText(loginFlow.getMessageWelcome(),
                expectedMessage,
                "Mensaje de bienvenida");
    }

    @When("the user leaves the username field empty")
    public void theUserLeavesTheUsernameFieldEmpty() {
    }

    @When("the user leaves the password field empty")
    public void theUserLeavesThePasswordFieldEmpty() {
    }

    @Then("the user should see a validation message {string} under the username field")
    public void theUserShouldSeeAValidationMessageUnderTheUsernameField(String message) {
    }

    @Then("the user should see a validation message {string} under the password field")
    public void theUserShouldSeeAValidationMessageUnderThePasswordField(String message) {
    }
}

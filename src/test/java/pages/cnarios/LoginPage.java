package pages.cnarios;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import pages.BasePage;

import java.util.List;

public class LoginPage extends BasePage {
    private String TestLoginFlow = "https://www.cnarios.com/challenges/login-flow";

    public LoginPage() {
        super("login");
    }

    public void navigateToTestLogin() {
        navigateTo(TestLoginFlow);
    }

    public void writeUsernameField(String words) {
        write("userNameField", words);
    }

    public void writePasswordField(String words) {
        write("passwordField", words);
    }

    public void clickButton() {
        clickElement("loginButton");
    }

    // validadores
    public String getAdminLoggedMessage() {
        return getTextOfWebElement("messageAdmin");
    }

    public WebElement adminMessageElement() {
        return getWebElement("messageAdmin");
    }

    public WebElement dashBoardElement() {
        return getWebElement("dashboardLocator");
    }

    public WebElement getMessageWelcome() {
        return getWebElement("welcomeMessage");
    }

    public List<WebElement> getErrorMessages() {
        return findElements("alerts");
    }

    @Override
    protected WebElement getElement(By locator) {
        return getWebElement(locator);
    }

}

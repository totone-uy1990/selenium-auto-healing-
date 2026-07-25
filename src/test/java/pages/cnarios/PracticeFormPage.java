package pages.cnarios;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import pages.BasePage;
import steps.models.cnarios.practiceForm.PracticeFormData;

public class PracticeFormPage extends BasePage {

    // En el constructor le indicamos a la BasePage cuál es su JSON
    public PracticeFormPage() {
        super("practice_form");
    }

    public void fillBasicInfo(PracticeFormData data) {
        write("firstNameInput", data.getNombre());
        write("lastNameInput", data.getApellido());
        write("userEmailInput", data.getEmail());
    }

    public void fillHobbies(PracticeFormData data) {
        for (String locatorKey : data.getHobbiesLocatorKeys()) {
            if (locatorKey != null && !locatorKey.isEmpty()) {
                clickElement(locatorKey);
            }
        }
    }

    public void clickSubmit() {
        clickElement("submitButton");
    }

    public boolean elementIsDisplayed(String locatorKey) {
        return super.elementIsDisplayed(locatorKey);
    }

    public boolean isRegistrationSuccessful() {
        return elementIsDisplayed("successModalTitle");
    }

    @Override
    protected WebElement getElement(By locator) {
        return getWebElement(locator);
    }
}

package pages.cnarios;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import pages.BasePage;

public class SuccessPage extends BasePage {

    public SuccessPage() {
        super("success");
    }

    @Override
    protected WebElement getElement(By locator) {
        return getWebElement(locator);
    }

    public String getMessageText() {
        return getTextOfWebElement("msgStatus");
    }
    
    public boolean isOrderSuccess() {
        return getMessageText().contains("Order Placed Successfully");
    }

    public boolean isPaymentFailed() {
        return getMessageText().contains("Payment Failed");
    }
}

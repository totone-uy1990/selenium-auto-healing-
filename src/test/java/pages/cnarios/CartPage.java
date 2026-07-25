package pages.cnarios;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import pages.BasePage;

public class CartPage extends BasePage {

    public CartPage() {
        super("cart");
    }

    @Override
    protected WebElement getElement(By locator) {
        return getWebElement(locator);
    }

    public CheckoutPage proceedToAddress() {
        clickElement("btnProceedToAddress");
        return new CheckoutPage();
    }
}

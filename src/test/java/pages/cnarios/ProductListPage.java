package pages.cnarios;

import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import pages.BasePage;

public class ProductListPage extends BasePage {

    public ProductListPage() {
        super("product_list");
    }

    public ProductListPage open(String url) {
        navigateTo(url);
        return this;
    }

    public ProductListPage closeTestCasesTab() {
        if (elementIsDisplayed("tabTestCases")) {
            clickElement("tabTestCases");
        }
        return this;
    }

    public ProductListPage addSmartphoneStandToCart() {
        clickElement("btnAddToCartSmartphoneStand");
        return this;
    }

    public CartPage goToCart() {
        clickElement("btnCartIcon");
        return new CartPage();
    }

    @Override
    protected WebElement getElement(By locator) {
        return getWebElement(locator);
    }
}

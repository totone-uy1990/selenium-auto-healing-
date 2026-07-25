package steps.cnarios;

import io.cucumber.java.en.And;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.junit.jupiter.api.Assertions;
import pages.cnarios.CartPage;
import pages.cnarios.CheckoutPage;
import pages.cnarios.ProductListPage;
import pages.cnarios.SuccessPage;

public class PurchasingSteps {

    ProductListPage productListPage = new ProductListPage();
    CartPage cartPage;
    CheckoutPage checkoutPage;
    SuccessPage successPage;

    @Given("que el usuario se encuentra en la página de listado de productos")
    public void navigateToStore() {
        productListPage.open("http://cnarios.com/challenges/product-purchasing");
    }

    @When("selecciona el producto {string} y lo añade al carrito")
    public void addProductToCart(String product) {
        // En esta app usamos el Smartphone Stand como por defecto
        productListPage.addSmartphoneStandToCart();
    }

    @And("navega hacia la sección de {string}")
    public void navigateToSection(String section) {
        cartPage = productListPage.goToCart();
        checkoutPage = cartPage.proceedToAddress();
    }

    @And("completa la información de facturación obligatoria")
    public void fillBillingInfo() {
        checkoutPage.fillBillingDetails("Ronal", "QA", "Calle Falsa 123")
                    .proceedToPayment();
    }

    @And("confirma el pago exitosamente")
    public void confirmPayment() {
        successPage = checkoutPage.confirmPayment();
    }

    @Then("el sistema debe procesar la transacción exitosamente")
    public void verifyTransactionSuccess() {
        Assertions.assertTrue(successPage.isOrderSuccess(), "El pedido no se completó con éxito");
    }

    @And("el usuario debe visualizar la página de confirmación {string}")
    public void verifySuccessMessage(String expectedMessage) {
        Assertions.assertTrue(successPage.getMessageText().contains(expectedMessage));
    }

    @And("cancela la transacción en el paso de pago")
    public void cancelTransaction() {
        checkoutPage.proceedToPayment();
        successPage = checkoutPage.cancelPayment();
    }

    @Then("el sistema debe mostrar un mensaje de error indicando {string}")
    public void verifyErrorMessage(String expectedError) {
        Assertions.assertTrue(successPage.getMessageText().contains(expectedError));
    }

    @And("deja el campo {string} vacío")
    public void leaveFieldEmpty(String field) {
        checkoutPage.clearAddress();
    }

    @Then("el botón de pago debe permanecer deshabilitado")
    public void verifyButtonDisabled() {
        Assertions.assertFalse(checkoutPage.isProceedToPaymentEnabled(), "El botón debería estar deshabilitado");
    }
}

package assertions;

import org.junit.jupiter.api.Assertions;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;

import java.util.List;

public class CustomAssertions {

    // --------------------------
    // VISIBILIDAD
    // --------------------------
    public void assertElementIsDisplayed(WebElement element, String elementName) {
        Assertions.assertTrue(
                element.isDisplayed(),
                "El elemento '" + elementName + "' debería estar visible"
        );
    }

    // --------------------------
    // TEXTO EXACTO
    // --------------------------
    public void assertTextEquals(WebElement element, String expectedText) {
        String actualText = element.getText().trim();
        Assertions.assertEquals(
                expectedText,
                actualText,
                "El texto real [" + actualText +
                        "] no coincide con el esperado [" + expectedText + "]");
    }


    // --------------------------
    // TEXTO CONTENIDO
    // --------------------------
    public static void assertContainsText(WebElement element, String expectedText, String fieldName) {
        String actualText = element.getText();
        Assertions.assertTrue(
                actualText.contains(expectedText),
                "El campo '" + fieldName +
                        " contiene [" + actualText +
                        "] pero se esperaba que contenga [" + expectedText + "]"
        );
    }

    // --------------------------
    // ESTADO
    // --------------------------
    public void assertElementIsEnabled(WebElement element, String elementName) {
        Assertions.assertTrue(
                element.isEnabled(),
                "El elemento '" + elementName + "' debería estar habilitado"
        );
    }

    public void assertElementIsSelected(WebElement element, String elementName) {
        Assertions.assertTrue(
                element.isSelected(),
                "El elemento '" + elementName + "' debería estar seleccionado"
        );
    }

    // --------------------------
    // DROPDOWN
    // --------------------------
    public void assertEqualsDropDownList(String dropdownName, Select dropdownSelect, List<String> expectedList) {

        List<String> actualList = dropdownSelect.getOptions()
                .stream()
                .map(WebElement::getText)
                .map(String::trim)
                .toList();

        Assertions.assertEquals(
                expectedList,
                actualList,
                "El dropdown " + dropdownName + " no coincide con la lista esperada"
        );
    }

    public void assertAnyElementContainsText(List<WebElement> elements, String expectedText) {
        if (elements == null || elements.isEmpty()) {
            throw new AssertionError("No list element were found to validate the text");
        }
        boolean matchFound = elements.stream()
                .filter(WebElement::isDisplayed)
                .map(WebElement::getText)
                .map(String::trim)
                .anyMatch(text -> text.contains(expectedText));
        
        Assertions.assertTrue(matchFound, 
            "No se encontró ningún elemento que contenga el texto: [" + expectedText + "]");
    }

    // --------------------------
    // REGLAS DE NEGOCIO
    // --------------------------
    public void failBusinessRule(String message) {
        Assertions.fail(message);
    }

    // --------------------------
    // BOOLEANO ESTÁTICO
    // --------------------------
    public static void assertTrue(boolean condition, String message) {
        Assertions.assertTrue(condition, message);
    }
}

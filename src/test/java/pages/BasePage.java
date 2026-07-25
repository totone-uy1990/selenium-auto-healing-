package pages;

import customExceptions.FrameworkException;
import coreLocators.LocatorRepository;
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.Select;
import org.openqa.selenium.support.ui.WebDriverWait;
import java.time.Duration;
import java.util.List;

public abstract class BasePage {

    // --- NUEVO: Propiedad para el nombre del archivo JSON ---
    protected String locatorFile;

    // Constructor para pages que usan JSON
    public BasePage(String locatorFile) {
        this.locatorFile = locatorFile;
    }

    // Constructor vacío para pages viejas que aún usan variables By
    public BasePage() {}

    // metodo obligatorio para todos los page object //para validaciones
    protected abstract WebElement getElement(By locator);

    // Driver por hilo (clave del paralelismo)
    protected static final ThreadLocal<WebDriver> driver = new ThreadLocal<>();

    private static ChromeOptions options;

    // --------------------------
    // DRIVER INIT
    // --------------------------
    public static void initDriver() {

        options = new ChromeOptions();
        options.setAcceptInsecureCerts(true);// omision paginas peligrosas
        options.addArguments("--remote-allow-origins=*");
        // ----------------------------------------
        // CONFIGURACIÓN LOCAL vs GITHUB ACTIONS
        // ----------------------------------------

        // Detectamos si estamos en GitHub Actions buscando la variable "CI"
        String isCI = System.getenv("CI");

        if (isCI != null && isCI.equals("true")) {
            // --- GITHUB ACTIONS (HEADLESS) ---
            System.out.println("Entorno CI (GitHub) detectado: Ejecutando Headless");
            options.addArguments("--headless=new"); // Fundamental para servidores sin pantalla
            options.addArguments("--window-size=1920,1080"); // Simula pantalla Full HD
            options.addArguments("--no-sandbox"); // Requerido para contenedores Docker/Linux
            options.addArguments("--disable-dev-shm-usage"); // Evita crash por memoria compartida
            options.addArguments("--disable-gpu");
        } else {
            // ---PC LOCAL (display) ---
            System.out.println("Entorno LOCAL detectado: Ejecutando navegador visual");
            options.addArguments("--start-maximized");
        }

        driver.set(new ChromeDriver(options));

    }

    // --------------------------
    // GETTERS
    // --------------------------

    // obtenemos el driver del threadLocal
    public static WebDriver getDriverFromThread() {
        return driver.get();
    }

    // creamos la espera con el driver
    private WebDriverWait getWait() {
        return new WebDriverWait(getDriverFromThread(), Duration.ofSeconds(10));
    }

    // --------------------------
    // NAVIGATION
    // --------------------------
    public void navigateTo(String url) {
        getDriverFromThread().get(url);
    }

    // ----------------------------------------------------
    // METODO AUXILIAR: Transforma String Key en un By
    // ----------------------------------------------------
    protected By getBy(String locatorKey) {
        if (locatorFile == null) {
            throw new FrameworkException("No se definió el archivo JSON (locatorFile) para esta Page.", null);
        }
        return LocatorRepository.getLocator(locatorFile, locatorKey);
    }

    // --------------------------
    // FINDERS ORIGINALES (Reciben By)
    // --------------------------
    private WebElement findElement(By locator) {
        try {
            // Selenium intenta buscar el elemento
            return getWait()
                    .until(ExpectedConditions
                            .presenceOfElementLocated(locator));
        } catch (org.openqa.selenium.TimeoutException | org.openqa.selenium.NoSuchElementException e) {
            // Capturamos el error técnico de Selenium y lo "envolvemos" en tu
            // FrameworkException
            throw new FrameworkException("No se pudo encontrar el elemento con el localizador: "
                    + locator + " tras el tiempo de espera configurado.", e);
        }
    }

    protected List<WebElement> findElements(By locator) {
        try {
            return getWait().until(ExpectedConditions
                    .presenceOfAllElementsLocatedBy(locator));

        } catch (org.openqa.selenium.TimeoutException
                | org.openqa.selenium.NoSuchElementException e) {
            throw new FrameworkException("No se pudieron encontrar la lista de elementos con el locator: "
                    + locator.toString() + " pasado el tiempo de espera configurado", e);

        }
    }

    // --------------------------
    // ACTIONS ORIGINALES (Reciben By)
    // --------------------------
    public void clickElement(By locator) {
        findElement(locator).click();
    }

    public void write(By locator, String keysToSend) {
        WebElement element = findElement(locator);
        element.clear();
        element.sendKeys(normalizeText(keysToSend));
    }

    // DROPDOWN methods

    public Select selectDropdown(By locator) {
        return new Select(findElement(locator));
    }

    public void selectFromDropdownByValue(By locator, String value) {
        new Select(findElement(locator)).selectByValue(value);
    }

    public void selectFromDropdownByIndex(By locator, int index) {
        new Select(findElement(locator)).selectByIndex(index);
    }

    public int dropdownSize(By locator) {
        return new Select(findElement(locator)).getOptions().size();
    }

    public void selectFromDropDown(By locator, String text) {
        new Select(findElement(locator)).selectByVisibleText(text);
    }

    public List<String> getDropdownOptionsText(Select select) {
        return select.getOptions()
                .stream()
                .map(WebElement::getText)
                .map(String::trim)
                .toList();
    }

    // isDisplayed:
    public boolean elementIsDisplayed(By locator) {
        if (findElement(locator).isDisplayed()) {
            System.out.println("El elemento es visible");
        } else {
            System.out.println("El elemento no es visible");

        }
        return findElement(locator).isDisplayed();
    }

    public WebElement getWebElement(By locator) {
        return findElement(locator);

    }

    public String getTextOfWebElement(By locator) {
        return findElement(locator).getText();
    }

    // ==========================================================
    // NUEVAS ACTIONS SOBRECARGADAS (Reciben String desde el JSON)
    // ==========================================================

    public void clickElement(String locatorKey) {
        clickElement(getBy(locatorKey));
    }

    public void write(String locatorKey, String keysToSend) {
        write(getBy(locatorKey), keysToSend);
    }

    public Select selectDropdown(String locatorKey) {
        return selectDropdown(getBy(locatorKey));
    }

    public void selectFromDropdownByValue(String locatorKey, String value) {
        selectFromDropdownByValue(getBy(locatorKey), value);
    }

    public void selectFromDropdownByIndex(String locatorKey, int index) {
        selectFromDropdownByIndex(getBy(locatorKey), index);
    }

    public int dropdownSize(String locatorKey) {
        return dropdownSize(getBy(locatorKey));
    }

    public void selectFromDropDown(String locatorKey, String text) {
        selectFromDropDown(getBy(locatorKey), text);
    }

    public boolean elementIsDisplayed(String locatorKey) {
        return elementIsDisplayed(getBy(locatorKey));
    }

    public WebElement getWebElement(String locatorKey) {
        return getWebElement(getBy(locatorKey));
    }

    public String getTextOfWebElement(String locatorKey) {
        return getTextOfWebElement(getBy(locatorKey));
    }

    protected List<WebElement> findElements(String locatorKey) {
        return findElements(getBy(locatorKey));
    }

    // --------------------------
    // CLOSE DRIVER
    // --------------------------
    public static void closeDriver() {
        if (driver.get() != null) {
            driver.get().quit();
            driver.remove(); // ← CLAVE PARA PARALELISMO REAL
        }
    }

    // normalizador de textos para datos de cucumber
    private String normalizeText(String value) {
        if (value == null) {
            return null; // o "" según tu criterio
        }
        String actualText = value.trim().replace("\"", "");
        return switch (actualText) {
            case "EMPTY" -> "";
            case "SPACE" -> " ";
            default -> actualText;
        };
    }

}
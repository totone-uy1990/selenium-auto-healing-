package steps;

import allureUtils.AllureUtils;
import io.cucumber.java.After;
import io.cucumber.java.Before;
import io.cucumber.java.Scenario;
import io.qameta.allure.Allure;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebDriver;
import pages.BasePage;

public class Hooks {

    @Before
    public void setup() {
        BasePage.initDriver();
    }

    @After
    public void teardown(Scenario scenario) {
        if (scenario.isFailed()) {
            WebDriver driver = BasePage.getDriverFromThread();
            if (driver != null) {
                byte[] screenshot = ((TakesScreenshot) driver)
                        .getScreenshotAs(OutputType.BYTES);
                AllureUtils.attachScreenshot(screenshot);
                Allure.addAttachment(
                        "URL",
                        "text/plain",
                        driver.getCurrentUrl());
                String pageSource = driver.getPageSource();
                Allure.addAttachment(
                        "Page source",
                        "text/html",
                        pageSource,
                        ".html");

                // Guardar DOM en archivo fsico para diagnstico de Inteligencia Artificial
                // (Scripts)
                try {
                    java.io.File debugDir = new java.io.File("build/debug-artifacts");
                    if (!debugDir.exists()) {
                        debugDir.mkdirs();
                    }
                    String safeScenarioName = scenario.getName().replaceAll("[^a-zA-Z0-9.-]", "_");
                    java.nio.file.Files.writeString(
                            java.nio.file.Paths.get("build/debug-artifacts/dom_dump_" + safeScenarioName + ".html"),
                            pageSource);
                } catch (java.io.IOException e) {
                    System.err.println("Failed to save DOM for AI diagnostic: " + e.getMessage());
                }
            }
        }

        BasePage.closeDriver();
    }

}

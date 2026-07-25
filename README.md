# Selenium OpenCode Automation-QA-Framework

**¿Qué es este framework?** Un framework de automatización de pruebas moderno y escalable para ejecutar tests E2E en navegadores. Úsalo para automatizar flujos de usuario, validar funcionalidades web, o integrarlo en tu pipeline de CI/CD.

**Último Allure Report:** https://totone-uy1990.github.io/Opencode-QA-Core-Selenium/

---

## Descripcion del Framework

Este es un framework de automatizacion de pruebas empresariales construido con Java 24, Selenium, Cucumber y JUnit 5 Platform. El framework sigue el patron Page Object Model (POM) y esta disenado para ejecutar pruebas E2E en navegadores Chromium compatibles.

### Caracteristicas Principales

- Arquitectura POM: Page Objects abstractos que encapsulan la logica de interaccion con la UI.
- Locators Dinamicos: Los elementos UI se definen en archivos JSON centralizados.
- Soporte BDD: Ejecucion de escenarios Gherkin con Cucumber.
- Reporting Avanzado: Reportes HTML enriquecidos con Allure.
- Ejecucion Paralela: Configurada para ejecutar 4 escenarios en paralelo.
- Integracion AI: Soporte nativo para el agente AI Antigravity.

---

## Tech Stack

| Tecnologia | Version |
|------------|---------|
| Lenguaje | Java 21 (LTS) / Java 24 Compatible |
| Build Tool | Gradle 8.14.4 |
| BDD | Cucumber 7.20.1 |
| Browser Automation | Selenium 4.27.0 |
| Test Runner | JUnit 5 Platform Suite (1.11.3) |
| Reporting | Allure Report 2.29.0 |
| Assertions | JUnit 5 (CustomAssertions) |
| Lombok | 1.18.34 |
| Jackson | 2.15.2 |
| CI/CD | GitHub Actions |

---

## Estructura del Proyecto

framework-con-IA/

src/test/java/
  pages/
    BasePage.java
    cnarios/
      LoginPage.java
      PracticeFormPage.java
      ProductListPage.java
      CartPage.java
      CheckoutPage.java
      SuccessPage.java
  steps/
    Hooks.java
    cnarios/
      loginFlowSteps.java
      PracticeFormSteps.java
      PurchasingSteps.java
    models/
      cnarios/loginFlow/LoginData.java
      cnarios/practiceForm/PracticeFormData.java
  coreLocators/
    LocatorRepository.java
    Locator.java
  customExceptions/
    AutomationException.java
    FrameworkException.java
    VerificationException.java
  assertions/
    CustomAssertions.java
  allureUtils/
    AllureUtils.java
  runner/
    TestRunner.java

src/test/resources/
  features/
    purchasing_flow.feature
    practice_form.feature
    cnarios/Role-Based-login-Flow/Login.feature
  locators/
    login.json
    practice_form.json
    product_list.json
    cart.json
    CheckoutPage.json
    success.json
  junit-platform.properties
  allure.properties

.agent/
workflows/
build.gradle.kts
gradlew

---

## Configuracion del Entorno

### Prerequisites

1. JDK 21 o 24: El framework usa toolchain para builds target Java 21.
   - Verificar: java -version
2. Google Chrome: Navegador instalado.
3. Gradle Wrapper: Incluido en el proyecto.

### Variable de Entorno (Opcional)

CI=true: Ejecuta en modo headless (sin interfaz grafica).

### Getting Started

./gradlew clean test

---

## Comandos para Ejecutar Tests

### Ejecucion Estandar

./gradlew clean test

### Compilacion

./gradlew compileTestJava

### Tests Especificos por Tag

./gradlew test -Dcucumber.filter.tags=@SmokeTest
./gradlew test -Dcucumber.filter.tags=@Registro
./gradlew test -Dcucumber.filter.name=Successful login

### Tags Disponibles

| Tag | Descripcion | Archivo |
|-----|-------------|---------|
| @Registro | Registro de estudiantes | practice_form.feature |
| @Regresion | Suite de regresion | practice_form.feature |
| @US-001 | Flujo de compra | purchasing_flow.feature |
| @Ecommerce | Pruebas ecommerce | purchasing_flow.feature |
| @SuccessfulPurchase | Compra exitosa | purchasing_flow.feature |
| @DeclinedPayment | Pago rechazado | purchasing_flow.feature |
| @ValidationFields | Validacion de campos | purchasing_flow.feature |

---

## Reportes Allure

./gradlew allureServe

Este comando:
1. Genera el reporte HTML desde build/allure-results
2. Abre automaticamente el navegador.

./gradlew allureReport

Genera el reporte sin abrir el navegador.

### Contenido del Reporte

- Step-by-step execution details
- Attached screenshots (si configurado)
- Timeline e historial
- Graphs y estadisticas pass/fail
- Exception stacks trace

---

## Configuracion de Ejecucion

Archivo: src/test/resources/junit-platform.properties

# PLUGINS
cucumber.plugin=io.qameta.allure.cucumber7jvm.AllureCucumber7Jvm

# PARALELISMO
cucumber.execution.parallel.enabled=true
cucumber.execution.parallel.config.strategy=fixed
cucumber.execution.parallel.config.fixed.parallelism=4
cucumber.execution.parallel.config.fixed.max-pool-size=4

# ORDEN
cucumber.execution.order=lexical

### Modificar Paralelismo

cucumber.execution.parallel.config.fixed.parallelism=8
cucumber.execution.parallel.config.fixed.max-pool-size=8

---

## Comandos Utiles de Gradle

./gradlew tasks
./gradlew help
./gradlew clean
./gradlew dependencies
./gradlew wrapper --validate
./gradlew clean test --info
./gradlew clean test --stacktrace
./gradlew clean test --dry-run
CI=true ./gradlew clean test
./gradlew test -Dcucumber.execution.parallel.enabled=false

---


Creado y mantenido conRonal y Antigravity AI.

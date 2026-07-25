// probando algo
plugins {
    id("java")
    id("io.qameta.allure") version "3.0.2" // Plugin maneja el agente automáticamente
}

repositories {
    mavenCentral()
}

// Versiones consistentes
val allureVersion = "2.29.0" // Variable centralizada para Allure
val cucumber = "7.20.1"
val junitPlatform = "1.11.3"
val selenium = "4.27.0"
val testNG = "7.11.0"
val lombok = "1.18.34"

// Configuración del plugin de Allure
allure {
    version.set(allureVersion) // Usamos la variable aquí
    adapter {
        frameworks {
            junit5 { 
                adapterVersion.set(allureVersion) // Y también aquí
            }
        }
    }
}

dependencies {
    // Cucumber + JUnit Platform
    testImplementation("io.cucumber:cucumber-java:$cucumber")
    testImplementation("io.cucumber:cucumber-junit-platform-engine:$cucumber")
    testImplementation("org.junit.platform:junit-platform-suite:$junitPlatform")
    // JUnit 5 Assertions
    testImplementation("org.junit.jupiter:junit-jupiter-api:5.12.1")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:5.12.1")

    // Allure
    testImplementation(platform("io.qameta.allure:allure-bom:$allureVersion"))
    testImplementation("io.qameta.allure:allure-cucumber7-jvm")
    testImplementation("io.qameta.allure:allure-junit-platform")

    // Selenium
    implementation("org.seleniumhq.selenium:selenium-java:$selenium")
//JNA
    testImplementation("net.java.dev.jna:jna:5.14.0")
    testImplementation("net.java.dev.jna:jna-platform:5.14.0")
//TestNG para Assertions
    //testImplementation("org.testng:testng:$testNG")

//Lombok
    implementation("org.projectlombok:lombok:$lombok")
    // Para procesar anotaciones en el código principal
    annotationProcessor("org.projectlombok:lombok:$lombok")

    // Para procesar anotaciones en los tests (¡Muy importante para tus Page Objects!)
    testAnnotationProcessor("org.projectlombok:lombok:$lombok")

    // Jackson para leer locators JSON
    testImplementation("com.fasterxml.jackson.core:jackson-databind:2.15.2")
}



// Configuración para forzar la codificación UTF-8 en la compilación
tasks.withType<JavaCompile> {
    options.encoding = "UTF-8"
}

// Configuración recomendada para asegurar que los tests también usen UTF-8
tasks.withType<Test> {
    systemProperty("file.encoding", "UTF-8")
}


java {
    toolchain {
        // Asegúrate de tener la versión correcta de Java aquí (e.g., 21, 17)
        // Y que esté alineada con tu AspectJ si tienes ese problema pendiente.
         languageVersion.set(JavaLanguageVersion.of(21))
    }
}


tasks.test {
    useJUnitPlatform()
    
    // Configuración para que Allure sepa dónde dejar los resultados
    systemProperty("allure.results.directory", "build/allure-results")

    // Mejor visualización en consola.
    testLogging {
        events("passed", "skipped", "failed")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}
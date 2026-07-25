package coreLocators;

import java.io.InputStream;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.openqa.selenium.By;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

public class LocatorRepository {
    // Almacena los locators agrupados por archivo JSON (PageName -> (LocatorKey -> Locator))
    // ConcurrentHashMap prepara tu framework para ejecución en paralelo (Thread-safe)
    private static final Map<String, Map<String, Locator>> locatorsCache = new ConcurrentHashMap<>(); //con concurrentHashMap preparamos el framework para ejecucion en paralelo (Thread-safe)

    // Este método ahora es privado, se invoca automáticamente cuando se necesita
    // Carga los locators desde un archivo JSON:
    private static void loadLocators(String fileNameJson) {
        
        // 1. Obtenemos el flujo de bytes afuera del try-catch de lectura
        // buscamos el archivo en la carpeta locators como recurso en flujo de bytes:
        InputStream jsonStream = LocatorRepository.class.getResourceAsStream("/locators/" + fileNameJson);

        if (jsonStream == null) {
            // Lanzamos error claro si el archivo no existe sin que sea capturado por el catch genérico
            throw new RuntimeException("No se pudo encontrar el archivo: /locators/" + fileNameJson);
        }

        // 2. try-with-resources para asegurar el cierre automático del InputStream y evitar fugas de memoria
        try (jsonStream) { 
            var mapper = new ObjectMapper();
            
            // lee el archivo json y lo convierte en un mapa de locators
            Map<String, Locator> loadedLocators = mapper.readValue(jsonStream, new TypeReference<Map<String, Locator>>() {});
            
            // Guardamos los localizadores asociados a este archivo en concreto
            locatorsCache.put(fileNameJson, loadedLocators);

        } catch (com.fasterxml.jackson.core.JsonParseException e) {
            // Error de sintaxis en el JSON (faltan comillas, comas, llaves, etc)
            throw new RuntimeException("Sintaxis JSON inválida en el archivo: " + fileNameJson, e);
        } catch (com.fasterxml.jackson.databind.JsonMappingException e) {
            // Error mapeando el JSON a los objetos (la estructura no coincide con la clase Locator)
            throw new RuntimeException("Estructura JSON incorrecta para un Locator en el archivo: " + fileNameJson, e);
        } catch (java.io.IOException e) {
            // Error general de entrada/salida (I/O) al leer el archivo físico
            throw new RuntimeException("Error de lectura (I/O) procesando /locators/" + fileNameJson, e);
        }
    }






    // Ahora recibe de qué archivo buscar, además de la Key
    public static By getLocator(String fileName, String locatorKey) {        //   ===> unico metodo que necesita el framework para obtener los locators
        // Aseguramos que termine en .json para no obligar a la Page a enviarlo
        String jsonFile = fileName.endsWith(".json") ? fileName : fileName + ".json";

        // Carga perezosa (Lazy Loading): lo carga en memoria solo la primera vez que se necesita
        if (!locatorsCache.containsKey(jsonFile)) {
            loadLocators(jsonFile);
        }

        // Obtiene el agrupador específico para ese archivo
        Map<String, Locator> fileLocators = locatorsCache.get(jsonFile);
        Locator locator = fileLocators.get(locatorKey);

        // Prevención del NullPointerException
        if (locator == null) {
            throw new IllegalArgumentException("No se encontró el locator '" + locatorKey + "' en el archivo '" + jsonFile + "'");
        }

        return buildBy(locator);
    }

    public static Set<String> getKeys(String fileName) {
        String jsonFile = fileName.endsWith(".json") ? fileName : fileName + ".json";
        if (!locatorsCache.containsKey(jsonFile)) {
            loadLocators(jsonFile);
        }
        return locatorsCache.get(jsonFile).keySet();
    }

    private static By buildBy(Locator locator) {
        // toLowerCase por si alguien escribe "Id", "ID", o "CSS"
        String type = locator.getType().toLowerCase();
        String value = locator.getValue();
       
        return switch (type) {
            case "id" -> By.id(value);
            case "name" -> By.name(value);
            case "xpath" -> By.xpath(value);
            case "css", "cssselector" -> By.cssSelector(value);
            case "classname", "class" -> By.className(value);
            case "linktext" -> By.linkText(value);
            default -> throw new RuntimeException("Tipo de locator no soportado: " + type);
        };
    }
}

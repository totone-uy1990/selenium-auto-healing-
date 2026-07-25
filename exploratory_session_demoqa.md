# Sesión Exploratoria Automática: DemoQA Practice Form
**Fecha:** 14 de Marzo 2026
**URL:** https://demoqa.com/automation-practice-form
**Objetivo:** Identificar elementos, validaciones y diseñar cobertura de pruebas para el formulario de registro.

## 1. Mapeo de Elementos y Localizadores (POM)

| Campo | Tipo | Localizador Recomendado (By) | Notas |
| :--- | :--- | :--- | :--- |
| **First Name** | Input | `By.id("firstName")` | Requerido |
| **Last Name** | Input | `By.id("lastName")` | Requerido |
| **Email** | Input | `By.id("userEmail")` | Valida formato regex |
| **Gender (Male)** | Radio/Label | `By.cssSelector("label[for='gender-radio-1']")` | Requerido. Se usa el label para evitar *ElementClickInterceptedException*. |
| **Gender (Female)**| Radio/Label | `By.cssSelector("label[for='gender-radio-2']")` | |
| **Gender (Other)** | Radio/Label | `By.cssSelector("label[for='gender-radio-3']")` | |
| **Mobile** | Input | `By.id("userNumber")` | Requerido. Exactamente 10 dígitos. |
| **Date of Birth**| Input | `By.id("dateOfBirthInput")` | Abre un calendario al hacer foco/clic. |
| **Subjects** | Autocomplete| `By.id("subjectsInput")` | Escribir texto y presionar tecla ENTER. |
| **Hobbies (Sports)**| Checkbox/Label| `By.cssSelector("label[for='hobbies-checkbox-1']")` | |
| **Picture** | File | `By.id("uploadPicture")` | Usar `sendKeys` con la ruta absoluta del archivo. |
| **Current Address**| Textarea | `By.id("currentAddress")` | |
| **State** | Dropdown | `By.id("react-select-3-input")` | Componente React-Select. Enviar texto + ENTER |
| **City** | Dropdown | `By.id("react-select-4-input")` | Depende de State. Enviar texto + ENTER |
| **Submit** | Button | `By.id("submit")` | Gatilla validaciones HTML5/JS. |

## 2. Reglas de Validación
1. **Campos Obligatorios Vacíos:** Los campos First Name, Last Name, Gender y Mobile son obligatorios. Si se omite alguno, el formulario aplica la clase css `.was-validated` y los inputs adquieren pseudo-clase `:invalid` (borde rojo).
2. **Email Formato:** Requiere estructura válida (`usuario@dominio.ext`).
3. **Móvil Longitud:** Si no tiene exactamente 10 dígitos, se marca como inválido.
4. **Modal de Éxito:** Tras un envío exitoso, se abre un modal con ID `example-modal-sizes-title-lg` conteniendo el título *"Thanks for submitting the form"*.

## 3. Cobertura de Pruebas Diseñada
*   **ESC-01 (Happy Path - Completo):** Rellenar absolutamente todos los campos, subir archivo y validar que el modal de éxito muestre la información correcta.
*   **ESC-02 (Happy Path - Mínimo):** Rellenar solo los campos obligatorios y validar éxito.
*   **ESC-03 (Negativo - Obligatorios Visibles):** Intentar enviar el formulario en blanco y verificar que los bordes de los campos requeridos cambien a rojo.
*   **ESC-04 (Negativo - Móvil Inválido):** Enviar el formulario con un número de móvil de 9 dígitos y verificar fallo en la validación.
*   **ESC-05 (Negativo - Email Inválido):** Enviar un email sin formato de dominio y verificar fallo en la validación.

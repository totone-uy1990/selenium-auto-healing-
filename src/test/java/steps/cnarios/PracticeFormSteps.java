package steps.cnarios;

import assertions.CustomAssertions;
import io.cucumber.java.en.And;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import pages.cnarios.PracticeFormPage;
import steps.models.cnarios.practiceForm.PracticeFormData;

public class PracticeFormSteps {

    private final PracticeFormPage formPage = new PracticeFormPage();

    @Given("un administrador accede al formulario de inscripción de estudiantes")
    public void unAdministradorAccedeAlFormularioDeInscripcion() {
        formPage.navigateTo("https://demoqa.com/automation-practice-form");
    }

    @When("registra a un estudiante con los siguientes datos:")
    public void registraAUnEstudianteConLosSiguientesDatos(PracticeFormData data) {
        formPage.fillBasicInfo(data);
        formPage.fillHobbies(data);
        // Aquí podrías agregar en tu PracticeFormPage los métodos para 
        // llenar el resto de campos (género, teléfono, fecha, materias, etc.)
        formPage.clickSubmit();
    }

    @Then("el sistema debe confirmar el registro exitoso")
    public void elSistemaDebeConfirmarElRegistroExitoso() {
        CustomAssertions.assertTrue(
            formPage.isRegistrationSuccessful(), 
            "El modal de confirmación de registro no se mostró."
        );
    }

    @And("la ficha del estudiante debe mostrar la información ingresada correctamente")
    public void laFichaDelEstudianteDebeMostrarLaInformacionIngresadaCorrectamente() {
        // Aquí iría la aserción de los datos en la tabla del modal
    }

    @When("el administrador intenta enviar el formulario sin completar datos")
    public void elAdministradorIntentaEnviarElFormularioSinCompletarDatos() {
        formPage.clickSubmit();
    }

    @Then("el sistema debe marcar en rojo los campos obligatorios incompletos")
    public void elSistemaDebeMarcarEnRojoLosCamposObligatoriosIncompletos() {
        // Lógica para verificar los bordes rojos
    }

    @When("registra a un estudiante con un número de teléfono de {string}")
    public void registraAUnEstudianteConUnNumeroDeTelefonoDe(String telefono) {
        PracticeFormData data = new PracticeFormData();
        data.setTelefono(telefono);
        formPage.fillBasicInfo(data); // LLena datos básicos para pasar
        formPage.clickSubmit();
    }

    @Then("el sistema no debe permitir el registro y marca el campo del teléfono como inválido")
    public void elSistemaNoDebePermitirElRegistroYMarcaElCampoDelTelefonoComoInvalido() {
        // Lógica para verificar que falló y el campo es inválido
    }
}

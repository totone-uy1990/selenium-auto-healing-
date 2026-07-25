package steps.models.cnarios.practiceForm;

import io.cucumber.java.DataTableType;
import java.util.Map;

public class PracticeFormDataTransformer {
    
    @DataTableType
    public PracticeFormData transform(Map<String, String> entry) {
        PracticeFormData data = new PracticeFormData();

        // Extraer los valores de la tabla en formato Clave-Valor
        String campo = entry.get("Campo");
        String valor = entry.get("Valor");

        if (campo != null && valor != null) {
            switch (campo) {
                case "Nombre Completo":
                    data.setNombreCompleto(valor);
                    break;
                case "Email":
                    data.setEmail(valor);
                    break;
                case "Género":
                    data.setGeneroStr(valor);
                    break;
                case "Teléfono":
                    data.setTelefono(valor);
                    break;
                case "Fecha Nacimiento":
                    data.setFechaNacimiento(valor);
                    break;
                case "Materias":
                    data.setMateriasStr(valor);
                    break;
                case "Hobbies":
                    data.setHobbiesStr(valor);
                    break;
                case "Foto":
                    data.setFoto(valor);
                    break;
                case "Dirección":
                    data.setDireccion(valor);
                    break;
                case "Ubicación":
                    data.setUbicacion(valor);
                    break;
            }
        } else {
             // Fallback para tabla horizontal si se llegara a usar en un futuro
             data.setNombreCompleto(entry.get("Nombre Completo"));
             data.setEmail(entry.get("Email"));
             data.setGeneroStr(entry.get("Género"));
             data.setTelefono(entry.get("Teléfono"));
             data.setFechaNacimiento(entry.get("Fecha Nacimiento"));
             data.setMateriasStr(entry.get("Materias"));
             data.setHobbiesStr(entry.get("Hobbies"));
             data.setFoto(entry.get("Foto"));
             data.setDireccion(entry.get("Dirección"));
             data.setUbicacion(entry.get("Ubicación"));
        }
        
        return data;
    }
}

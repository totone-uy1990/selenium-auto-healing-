package steps.models.cnarios.practiceForm;

import lombok.Data;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@Data
public class PracticeFormData {
    private String nombre;
    private String apellido;
    private String email;
    private String generoLocatorKey;
    private String telefono;
    private String fechaNacimiento;
    private List<String> materias;
    private List<String> hobbiesLocatorKeys;
    private String foto;
    private String direccion;
    private String estado;
    private String ciudad;

    public void setNombreCompleto(String nombreCompleto) {
        Optional.ofNullable(nombreCompleto)
            .filter(n -> !n.trim().isEmpty())
            .ifPresent(n -> {
                String[] parts = n.split(" ", 2);
                this.nombre = parts[0];
                this.apellido = parts.length > 1 ? parts[1] : "";
            });
    }

    public void setUbicacion(String ubicacion) {
        Optional.ofNullable(ubicacion)
            .filter(u -> u.contains(" - "))
            .ifPresent(u -> {
                String[] parts = u.split(" - ");
                this.estado = parts[0].trim();
                this.ciudad = parts[1].trim();
            });
    }

    public void setMateriasStr(String materiasStr) {
        this.materias = Optional.ofNullable(materiasStr)
            .filter(s -> !s.trim().isEmpty())
            .map(s -> Arrays.stream(s.split(","))
                            .map(String::trim)
                            .collect(Collectors.toList()))
            .orElse(List.of());
    }

    public void setGeneroStr(String generoStr) {
        this.generoLocatorKey = Optional.ofNullable(generoStr)
            .map(String::toLowerCase)
            .map(g -> switch (g) {
                case "masculino", "male" -> "genderMaleRadio";
                case "femenino", "female" -> "genderFemaleRadio";
                default -> "genderOtherRadio";
            })
            .orElse(null);
    }

    public void setHobbiesStr(String hobbiesStr) {
        this.hobbiesLocatorKeys = Optional.ofNullable(hobbiesStr)
            .filter(s -> !s.trim().isEmpty())
            .map(s -> Arrays.stream(s.split(","))
                            .map(String::trim)
                            .map(String::toLowerCase)
                            .map(h -> switch (h) {
                                case "sports" -> "hobbiesSportsCheckbox";
                                case "reading" -> "hobbiesReadingCheckbox";
                                case "music" -> "hobbiesMusicCheckbox";
                                default -> "";
                            })
                            .filter(key -> !key.isEmpty())
                            .collect(Collectors.toList()))
            .orElse(List.of());
    }
}

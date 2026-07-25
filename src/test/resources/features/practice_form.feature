@Registro @Regresion
Feature: Student Enrollment Management
  The system must allow student registration by validating data integrity.

  Background:
    Given un administrador accede al formulario de inscripción de estudiantes

  Scenario: Registro exitoso de un estudiante con información completa
    When registra a un estudiante con los siguientes datos:
      | Campo              | Valor                                  |
      | Nombre Completo    | Ronal Tester                           |
      | Email              | ronal.tester@example.com               |
      | Género             | Masculino                              |
      | Teléfono           | 0987654321                             |
      | Fecha Nacimiento   | 15 May 1990                            |
      | Materias           | Computer Science, Maths                |
      | Hobbies            | Sports, Music                          |
      | Foto               | perfil_estudiante.jpg                  |
      | Dirección          | Av. 18 de Julio, Montevideo            |
      | Ubicación          | NCR - Delhi                            |
    Then el sistema debe confirmar el registro exitoso
    And la ficha del estudiante debe mostrar la información ingresada correctamente 

  Scenario: Fallo en el registro al intentar enviar el formulario vacío
    When el administrador intenta enviar el formulario sin completar datos
    Then el sistema debe marcar en rojo los campos obligatorios incompletos

  Scenario: Fallo en el registro por número de teléfono inválido
    When registra a un estudiante con un número de teléfono de "12345"
    Then el sistema no debe permitir el registro y marca el campo del teléfono como inválido

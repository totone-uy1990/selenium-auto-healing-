@US-001 @Ecommerce
Feature: Flujo de Compra de Producto en E-commerce
  Como un cliente del sitio
  Quiero completar un proceso de compra completo
  Para adquirir productos exitosamente

  Background:
    Given que el usuario se encuentra en la página de listado de productos

  @SuccessfulPurchase
  Scenario: Compra exitosa de un producto único
    When selecciona el producto "Smartphone Stand" y lo añade al carrito
    And navega hacia la sección de "Checkout"
    And completa la información de facturación obligatoria
    And confirma el pago exitosamente
    Then el sistema debe procesar la transacción exitosamente
    And el usuario debe visualizar la página de confirmación "Order Placed Successfully!"

  @DeclinedPayment
  Scenario: Intento de compra con pago cancelado
    When selecciona el producto "Smartphone Stand" y lo añade al carrito
    And navega hacia la sección de "Checkout"
    And completa la información de facturación obligatoria
    And cancela la transacción en el paso de pago
    Then el sistema debe mostrar un mensaje de error indicando "Payment Failed!"

  @ValidationFields
  Scenario: Validación de campos obligatorios en facturación
    When selecciona el producto "Smartphone Stand" y lo añade al carrito
    And navega hacia la sección de "Checkout"
    And deja el campo "Dirección" vacío
    Then el botón de pago debe permanecer deshabilitado

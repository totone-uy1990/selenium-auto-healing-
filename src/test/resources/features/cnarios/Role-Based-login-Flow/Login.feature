
Feature: Login Flow Challenge
  As a registered user
  I want to authenticate into the application
  So that I can access my secure account dashboard

  Background:
    Given the user is on the Cnarios test_login page "https://www.cnarios.com/challenges/login-flow"


  Scenario: Successful login with valid credentials
    When the user enters his credentials:
      |username|password|
      |admin   |admin123|
    And clicks on the login button
    Then the user should be redirected to the "Dashboard" page
    And the user should see a welcome message containing "Welcome"

  #@regression @negative_testing @ui
  Scenario Outline: Failed login with invalid credentials
    When the user enters his credentials:
      | username | password |
      | <username> | <password> |
    And clicks on the login button
    Then the user should see an error message saying "<error_message>"

    Examples:
      | username       | password      | error_message       |
      |   EMPTY        |  EMPTY        | Both fields are required.|
      |   EMPTY        | admin123      | Both fields are required.|
      | admin          | wrongPass     | Invalid password    |
      | admin          | EMPTY         | Invalid password    |
      | user           | wrongPass     | Invalid credentials |



  #@ui
  #Scenario: Login validation with empty fields
  #  When the user leaves the username field empty
   # And the user leaves the password field empty
    #And clicks on the login button
   # Then the user should see a validation message "This field is required" under the username field
   # And the user should see a validation message "This field is required" under the password field
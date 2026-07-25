package steps.models.cnarios.loginFlow;

import io.cucumber.java.DataTableType;

import java.util.Map;

public class LoginDataTransformer {
    @DataTableType
    public LoginData loginDataTransformer(Map<String, String> entry) {
        LoginData data = new LoginData();
        data.setUsername(entry.get("username"));
        data.setPassword(entry.get("password"));
        return data;
    }
}

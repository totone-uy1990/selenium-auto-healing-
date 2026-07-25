package allureUtils;

import io.qameta.allure.Attachment;

public class AllureUtils {

    @Attachment(value = "Screenshot - failure", type = "image/png")
    public static byte[] attachScreenshot(byte[] screenshot) {
        return screenshot;
    }

}

const { jsPDF } = require("jspdf");

try {
    const doc = new jsPDF();
    const { AcroFormTextField } = require("jspdf"); // wait, maybe on jsPDF object?
    var sign1 = new jsPDF.AcroForm.TextField();
    console.log("SUCCESS_ACROFORM");
} catch (e) {
    try {
        var sign2 = new jspdf.AcroFormTextField();
        console.log("SUCCESS_2");
    } catch (e2) {
        console.log("FAIL: ", e.message, e2.message);
    }
}

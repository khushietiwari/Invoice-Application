from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import io
import random
import os

app = Flask(__name__)

@app.route("/")
def home():
    """Renders the invoice generation form."""
    return render_template("invoice_form.html")

@app.route("/generate", methods=["POST"])
def generate_invoice():
    """
    Processes form data, generates a PDF invoice using ReportLab,
    and returns it as a downloadable file.
    """
    try:
        # 1. Extract Invoice Details
        buyer = request.form["buyer"]
        invoice_date = request.form["date"]

        # 2. Extract and Process Items
        desc_list = request.form.getlist("desc[]")
        hsn_list = request.form.getlist("hsn[]")
        qty_list = request.form.getlist("qty[]")
        rate_list = request.form.getlist("rate[]")

        # Convert quantities and rates to numbers
        qty_list = [int(q) for q in qty_list]
        rate_list = [float(r) for r in rate_list]

        # Fill empty HSN with random 8-digit numbers for placeholder
        hsn_list = [h if h.strip() else str(random.randint(10000000, 99999999)) for h in hsn_list]

        # Calculate amounts for each item
        amounts = [q * r for q, r in zip(qty_list, rate_list)]
        total_amount = sum(amounts)

        # --- Generate PDF ---
        buffer = io.BytesIO()
        # Set margin sizes for the document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            leftMargin=50, 
            rightMargin=50, 
            topMargin=50, 
            bottomMargin=50
        )
        elements = []
        styles = getSampleStyleSheet()

        # --- Utility Functions for styles ---
        def get_normal_style():
            style = styles["Normal"]
            style.spaceAfter = 6
            return style
        
        def get_title_style():
            style = styles["Title"]
            style.alignment = 1  # Center
            style.spaceAfter = 18
            return style

        # --- Header (Seller Info) ---
        elements.append(Paragraph("<b>SHIV BHOLE TRADERS & SERVICE</b>", get_title_style()))
        elements.append(Paragraph("L-39,106, Dhanlaxmi Residency, Ambika Park, Lavachha, Valsad, Gujarat", get_normal_style()))
        elements.append(Paragraph("GST: 24AQIPT6888R1ZI", get_normal_style()))
        elements.append(Spacer(1, 18))

        # --- Invoice Info & Buyer Details ---
        elements.append(Paragraph(
            f"<b>Invoice No:</b> 001 | <b>Date:</b> {invoice_date}", styles["Heading4"]
        ))
        elements.append(Paragraph(f"<b>Invoice To:</b> {buyer}", get_normal_style()))
        elements.append(Spacer(1, 12))

        # --- Items Table ---
        # Data structure: [["Description", "HSN", "Qty", "Rate", "Amount"], ...]
        table_data = [["Description", "HSN", "Qty", "Rate (₹)", "Amount (₹)"]]
        for desc, hsn, qty, rate, amt in zip(desc_list, hsn_list, qty_list, rate_list, amounts):
            table_data.append([
                Paragraph(desc, styles["Normal"]), 
                hsn, 
                qty, 
                f"{rate:.2f}", 
                f"{amt:.2f}"
            ])

        # Add total row
        table_data.append([
            Paragraph("<b>Total (Excl. Tax)</b>", styles["Normal"]), 
            "", 
            "", 
            "", 
            f"<b>{total_amount:.2f}</b>"
        ])

        # Define column widths (adjusting Description width)
        col_widths = [230, 70, 50, 70, 80]
        table = Table(table_data, colWidths=col_widths)
        
        # Style the table
        table.setStyle(TableStyle([
            # Header Row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor('#004d40')), # Dark Teal Header
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            
            # Content Rows
            ("ALIGN", (1, 1), (-1, -2), "CENTER"), # Center HSN, Qty, Rate, Amount
            ("ALIGN", (0, 1), (0, -2), "LEFT"),    # Left-align Description
            
            # Total Row (Last Row)
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor('#e0f2f1')), # Light Teal Background
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (4, -1), (-1, -1), "RIGHT"),
            
            # General Grid and Padding
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))

        # --- Totals & Taxes ---
        sgst_rate = 0.09
        cgst_rate = 0.09
        sgst = total_amount * sgst_rate
        cgst = total_amount * cgst_rate
        grand_total = total_amount + sgst + cgst
        
        # Tax table data
        tax_data = [
            ["Sub Total (Excl. Tax):", f"₹ {total_amount:.2f}"],
            [f"SGST ({sgst_rate*100:.0f}%) @ Gujarat", f"₹ {sgst:.2f}"],
            [f"CGST ({cgst_rate*100:.0f}%) @ Central", f"₹ {cgst:.2f}"],
            ["<b>GRAND TOTAL:</b>", f"<b>₹ {grand_total:.2f}</b>"]
        ]
        
        # Create a table for totals aligned to the right
        tax_table = Table(tax_data, colWidths=[400, 100])
        tax_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor('#ccffee')),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(tax_table)
        elements.append(Spacer(1, 20))

        # --- Footer Details ---
        elements.append(Paragraph("<b>Bank Details:</b>", styles["Heading4"]))
        elements.append(Paragraph("Bank: HDFC Bank, Silvassa", get_normal_style()))
        elements.append(Paragraph("A/c No: 50200065378797 | IFSC: HDFC0000074", get_normal_style()))
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Declaration:</b>", styles["Heading4"]))
        elements.append(Paragraph(
            "We declare that this invoice shows the actual price of the goods "
            "and that all particulars are true and correct. Complaints, if any, "
            "should be reported within 24 hours.",
            get_normal_style()
        ))
        elements.append(Spacer(1, 40))
        
        # Signature Line (Aligned Right)
        sig_data = [
            ["", "For SHIV BHOLE TRADERS & SERVICE"]
        ]
        sig_table = Table(sig_data, colWidths=[400, 100])
        sig_table.setStyle(TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
        ]))
        elements.append(sig_table)
        elements.append(Spacer(1, 30))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer, 
            as_attachment=True, 
            download_name="invoice.pdf", 
            mimetype="application/pdf"
        )
    except Exception as e:
        # Simple error handling for form validation issues
        app.logger.error(f"Error generating invoice: {e}")
        return render_template("error.html", error_message=str(e)), 400

# This is only executed when running locally for testing.
if __name__ == "__main__":
    # Use environment variables for port configuration on deployment
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
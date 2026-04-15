def build_transfer_funds_response(result):
    root = ET.Element(f"{{{TNS}}}transferFundsResponse")
    tx_id = ET.SubElement(root, f"{{{TNS}}}transactionId")
    tx_id.text = result["transaction_id"]
    status = ET.SubElement(root, f"{{{TNS}}}status")
    status.text = result["status"]
    amount = ET.SubElement(root, f"{{{TNS}}}amount")
    amount.text = decimal_text(result["amount"])
    currency = ET.SubElement(root, f"{{{TNS}}}currency")
    currency.text = result["currency"]
    return make_envelope(root)
"""Fiscal domain event constants for audit logging."""

# Invoice events
INVOICE_DRAFT_CREATED = "invoice.draft.created"
INVOICE_VALIDATED = "invoice.validated"
INVOICE_ISSUE_REQUESTED = "invoice.issue.requested"
INVOICE_ISSUED = "invoice.issued"
INVOICE_REJECTED = "invoice.rejected"
INVOICE_CANCEL_REQUESTED = "invoice.cancel.requested"
INVOICE_CANCELLED = "invoice.cancelled"
INVOICE_XML_DOWNLOADED = "invoice.xml.downloaded"
INVOICE_PDF_DOWNLOADED = "invoice.pdf.downloaded"
INVOICE_SENT_TO_CUSTOMER = "invoice.sent_to_customer"

# e-CAC events
ECAC_SYNC_REQUESTED = "ecac.sync.requested"
ECAC_TAX_STATUS_FETCHED = "ecac.tax_status.fetched"
ECAC_MAILBOX_FETCHED = "ecac.mailbox.fetched"

# Certificate events
CERTIFICATE_UPLOADED = "certificate.uploaded"
CERTIFICATE_ACCESSED = "certificate.accessed"
CERTIFICATE_VALIDATED = "certificate.validated"
CERTIFICATE_EXPIRY_ALERT = "certificate.expiry.alert"

# Guide events
FISCAL_GUIDE_GENERATED = "fiscal_guide.generated"
FISCAL_GUIDE_SENT = "fiscal_guide.sent"
FISCAL_GUIDE_MARKED_PAID = "fiscal_guide.marked_paid"
FISCAL_GUIDE_PAYMENT_PROOF_UPLOADED = "fiscal_guide.payment_proof.uploaded"

# Monthly closing events
MONTHLY_CLOSING_BOOTSTRAPPED = "monthly_closing.bootstrapped"
MONTHLY_CLOSING_COMPLETED = "monthly_closing.completed"
MONTHLY_CLOSING_REOPENED = "monthly_closing.reopened"
MONTHLY_CLOSING_DOSSIER_GENERATED = "monthly_closing.dossier.generated"

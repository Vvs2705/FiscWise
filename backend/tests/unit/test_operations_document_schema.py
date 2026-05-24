import uuid
from datetime import datetime, timezone

from app.models.operations import ClientDocument
from app.schemas.operations import DocumentResponse


def test_document_response_exposes_parse_metadata_and_ai_classification() -> None:
    document = ClientDocument(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        name="das-maio.pdf",
        document_type="das",
        status="available",
        parse_status="completed",
        parsed_data={
            "type": "pdf",
            "ai_classification": {
                "document_type": "das",
                "summary": "DAS de maio identificado",
                "confidence": 0.92,
            },
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = DocumentResponse.model_validate(document)

    assert response.parse_status == "completed"
    assert response.parsed_data["type"] == "pdf"
    assert response.ai_classification == {
        "document_type": "das",
        "summary": "DAS de maio identificado",
        "confidence": 0.92,
    }

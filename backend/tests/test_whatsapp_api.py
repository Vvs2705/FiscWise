"""Integration tests for WhatsApp Business API endpoints, service, and isolation."""

import uuid
from datetime import date, timedelta
import pytest
from sqlalchemy import select

from app.models.whatsapp import WhatsAppInbox, WhatsAppMessage
from app.models.operations import DeadlineItem, ClientDocument
from app.schemas.whatsapp import SendWhatsAppRequest, LinkInboxRequest, ConvertTaskRequest


class TestWhatsAppAPI:
    """Tests for the WhatsApp unified messaging endpoints."""

    @pytest.mark.asyncio
    async def test_list_inboxes_success(self, client_with_auth_a, test_db):
        """GET /api/v1/whatsapp/inboxes lists messaging threads successfully."""
        client, user_a, client_a, _ = client_with_auth_a

        # Create inbox under user_a's tenant
        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            phone_number="+5511999999999",
            customer_name="John Doe",
            unread_count=2,
            status="active"
        )
        test_db.add(inbox)
        await test_db.commit()

        response = client.get("/api/v1/whatsapp/inboxes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["phone_number"] == "+5511999999999"
        assert data[0]["customer_name"] == "John Doe"
        assert data[0]["unread_count"] == 2
        assert data[0]["client_id"] == str(client_a.id)

    @pytest.mark.asyncio
    async def test_list_messages_success(self, client_with_auth_a, test_db):
        """GET /api/v1/whatsapp/inboxes/{inbox_id}/messages returns message thread history and clears unread count."""
        client, user_a, client_a, _ = client_with_auth_a

        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            phone_number="+5511999999999",
            customer_name="John Doe",
            unread_count=3,
            status="active"
        )
        test_db.add(inbox)
        await test_db.flush()

        from datetime import datetime, timezone

        msg1 = WhatsAppMessage(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            inbox_id=inbox.id,
            direction="inbound",
            body="Olá, preciso de ajuda com o DAS",
            message_type="text",
            status="delivered",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        msg2 = WhatsAppMessage(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            inbox_id=inbox.id,
            direction="outbound",
            body="Olá! Como posso ajudar?",
            message_type="text",
            status="sent",
            created_at=datetime.now(timezone.utc)
        )
        test_db.add_all([msg1, msg2])
        await test_db.commit()

        # Query messages
        response = client.get(f"/api/v1/whatsapp/inboxes/{inbox.id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["body"] == "Olá, preciso de ajuda com o DAS"
        assert data[0]["direction"] == "inbound"
        assert data[1]["body"] == "Olá! Como posso ajudar?"
        assert data[1]["direction"] == "outbound"

        # Verify unread count is cleared
        await test_db.refresh(inbox)
        assert inbox.unread_count == 0

    @pytest.mark.asyncio
    async def test_send_whatsapp_message(self, client_with_auth_a, test_db):
        """POST /api/v1/whatsapp/inboxes/{inbox_id}/send registers outbound message and updates inbox preview."""
        client, user_a, client_a, _ = client_with_auth_a

        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            phone_number="+5511999999999",
            customer_name="John Doe",
            unread_count=0,
            status="active"
        )
        test_db.add(inbox)
        await test_db.commit()

        response = client.post(
            f"/api/v1/whatsapp/inboxes/{inbox.id}/send",
            json={"body": "Mensagem de teste de envio"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "Mensagem de teste de envio"
        assert data["direction"] == "outbound"

        # Check DB updates on inbox
        await test_db.refresh(inbox)
        assert inbox.last_message_preview == "Mensagem de teste de envio"

    @pytest.mark.asyncio
    async def test_link_inbox_client(self, client_with_auth_a, test_db):
        """POST /api/v1/whatsapp/inboxes/{inbox_id}/link changes client association."""
        client, user_a, client_a, _ = client_with_auth_a

        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=None,  # unlinked initially
            phone_number="+5511999999999",
            customer_name="Contato +5511999999999",
            unread_count=0,
            status="active"
        )
        test_db.add(inbox)
        await test_db.commit()

        # Link to client_a
        response = client.post(
            f"/api/v1/whatsapp/inboxes/{inbox.id}/link",
            json={"client_id": str(client_a.id)}
        )
        assert response.status_code == 200
        assert response.json()["client_id"] == str(client_a.id)

        # Verify in DB
        await test_db.refresh(inbox)
        assert inbox.client_id == client_a.id
        assert inbox.customer_name == client_a.name

    @pytest.mark.asyncio
    async def test_convert_task(self, client_with_auth_a, test_db):
        """POST /api/v1/whatsapp/messages/{message_id}/convert-task creates a DeadlineItem successfully."""
        client, user_a, client_a, _ = client_with_auth_a

        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            phone_number="+5511999999999",
            customer_name="John Doe",
            unread_count=0,
            status="active"
        )
        test_db.add(inbox)
        await test_db.flush()

        message = WhatsAppMessage(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            inbox_id=inbox.id,
            direction="inbound",
            body="Favor enviar a folha de pagamento deste mês.",
            message_type="text",
            status="delivered"
        )
        test_db.add(message)
        await test_db.commit()

        # Convert to task
        payload = {
            "title": "Enviar folha de pagamento",
            "due_date": str(date.today() + timedelta(days=2)),
            "priority": "high"
        }
        response = client.post(
            f"/api/v1/whatsapp/messages/{message.id}/convert-task",
            json=payload
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify DeadlineItem created in DB
        stmt = select(DeadlineItem).where(DeadlineItem.client_id == client_a.id)
        res_tasks = await test_db.execute(stmt)
        tasks = res_tasks.scalars().all()
        assert len(tasks) == 1
        assert tasks[0].title == "Enviar folha de pagamento"
        assert tasks[0].priority == "high"
        assert "folha de pagamento" in tasks[0].description

    @pytest.mark.asyncio
    async def test_webhook_ingest_and_auto_collection(self, client, test_db, tenant_a, client_a):
        """POST /api/v1/whatsapp/webhooks/{tenant_id} creates inbox, message, and auto-collects document if it is a media file."""
        # Update client phone in DB to match webhook sender phone
        client_a.phone = "+5511888888888"
        test_db.add(client_a)
        await test_db.commit()

        payload = {
            "sender_phone": "+5511888888888",
            "sender_name": "John Webhook",
            "body": "Comprovante DAS",
            "message_type": "document",
            "media_url": "https://supabase.com/storage/v1/object/public/documents/comprovante.pdf",
            "external_message_id": "ext-id-123"
        }

        response = client.post(
            f"/api/v1/whatsapp/webhooks/{tenant_a.id}",
            json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

        # Check WhatsAppInbox created and linked to client_a
        stmt_inbox = select(WhatsAppInbox).where(WhatsAppInbox.tenant_id == tenant_a.id)
        res_inbox = await test_db.execute(stmt_inbox)
        inbox = res_inbox.scalar_one()
        assert inbox.client_id == client_a.id
        assert inbox.phone_number == "+5511888888888"

        # Check ClientDocument was automatically created (auto document collection)
        stmt_doc = select(ClientDocument).where(ClientDocument.client_id == client_a.id)
        res_doc = await test_db.execute(stmt_doc)
        docs = res_doc.scalars().all()
        assert len(docs) == 1
        assert docs[0].file_url == "https://supabase.com/storage/v1/object/public/documents/comprovante.pdf"
        assert docs[0].name == "Comprovante DAS.pdf"  # Webhook processor adds .pdf extension if document_type document and missing
        assert docs[0].status == "available"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, client_with_auth_b, client_with_auth_a, test_db):
        """User B cannot access or send messages in User A's WhatsApp inboxes."""
        _, user_a, client_a, _ = client_with_auth_a

        # Create inbox under User A's tenant
        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            phone_number="+5511999999999",
            customer_name="John Doe",
            unread_count=0,
            status="active"
        )
        test_db.add(inbox)
        await test_db.commit()

        # Try to query this inbox using client B (User B)
        client_b_http, _, _, _ = client_with_auth_b

        # Retrieve messages for inbox A should fail with 404
        response = client_b_http.get(f"/api/v1/whatsapp/inboxes/{inbox.id}/messages")
        assert response.status_code == 404

        # Sending message to inbox A should fail with 404
        response = client_b_http.post(
            f"/api/v1/whatsapp/inboxes/{inbox.id}/send",
            json={"body": "Invasão de conversa"}
        )
        assert response.status_code == 404

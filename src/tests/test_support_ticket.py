from unittest import TestCase
from unittest.mock import patch, Mock
from datetime import datetime
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from entities.SupportTicket import SupportTicket
from entities.SupportTicketLog import SupportTicketLog
from entities.SupportTicketAttachment import SupportTicketAttachment
from controllers.support import (
    get_support_tickets,
    get_support_ticket,
    add_support_ticket,
    reply_support_ticket,
    update_reply_support_ticket,
    delete_reply_support_ticket,
    auto_close_tickets,
    download_file_from_ticket_by_id,
    delete_file_from_ticket_by_id,
)
from schemas.Support import SupportTicketSchema, SupportTicketReplySchema

class TestSupportTicket(TestCase):
    def setUp(self):
        # Given
        self.mock_db = Mock(spec=Session)

        self.current_time = datetime.now().isoformat()

        self.mock_user = Mock()
        self.mock_user.id = 1
        self.mock_user.email = "test@example.com"
        self.mock_user.is_admin = False

        self.sample_ticket = Mock(spec=SupportTicket)
        self.sample_ticket.id = 123
        self.sample_ticket.user_id = 1
        self.sample_ticket.severity = "medium"
        self.sample_ticket.status = "await agent"
        self.sample_ticket.selected_product = "test product"
        self.sample_ticket.subject = "Test Issue"
        self.sample_ticket.message = "Test message"
        self.sample_ticket.created_at = self.current_time
        self.sample_ticket.last_update = self.current_time
        self.sample_ticket.gitlab_issue_id = 456
        self.sample_ticket.user = self.mock_user

        self.sample_ticket.save = Mock()
        self.sample_ticket.getUserSupportTickets = Mock()
        self.sample_ticket.getUserSupportTicket = Mock()
        self.sample_ticket.getAllSupportTickets = Mock()
        self.sample_ticket.getSupportTicket = Mock()
        self.sample_ticket.updateTicketStatus = Mock()
        self.sample_ticket.updateTicketTime = Mock()
        self.sample_ticket.updateTicket = Mock()
        self.sample_ticket.attach_gitlab_issue = Mock()
        self.sample_ticket.deleteOne = Mock()
        self.sample_ticket.getInactiveSupportTickets = Mock()

        self.sample_reply = Mock(spec=SupportTicketLog)
        self.sample_reply.id = 789
        self.sample_reply.status = "await agent"
        self.sample_reply.is_admin = False
        self.sample_reply.ticket_id = 123
        self.sample_reply.user_id = 1
        self.sample_reply.message = "Test reply"
        self.sample_reply.creation_date = self.current_time
        self.sample_reply.change_date = self.current_time
        self.sample_reply.user = self.mock_user

        self.sample_reply.save = Mock()
        self.sample_reply.getTicketLogs = Mock()
        self.sample_reply.getTicketLog = Mock()
        self.sample_reply.updateTicketLog = Mock()
        self.sample_reply.deleteTicketLog = Mock()
        self.sample_reply.deleteTicketReplies = Mock()

        self.sample_attachment = Mock(spec=SupportTicketAttachment)
        self.sample_attachment.id = 1
        self.sample_attachment.name = "test.txt"
        self.sample_attachment.mime_type = "text/plain"
        self.sample_attachment.storage_key = "storage/key/test.txt"
        self.sample_attachment.support_ticket_id = 123
        self.sample_attachment.user_id = 1

    @patch("controllers.support.SupportTicket.getUserSupportTickets")
    def test_get_support_tickets_success(self, mock_get_tickets):
        # Given
        ticket_mock = Mock(spec=SupportTicket)

        ticket_mock.__class__ = Mock(spec=DeclarativeMeta)
        ticket_mock.__class__.registry = Mock()

        attributes = {
            "id": 123,
            "user_id": 1,
            "severity": "medium",
            "status": "await agent",
            "selected_product": "test product",
            "subject": "Test Issue",
            "message": "Test message",
            "created_at": self.current_time,
            "last_update": self.current_time,
            "gitlab_issue_id": 456,
            "user": self.mock_user,
            "metadata": Mock(),
            "query": Mock(),
        }

        for attr, value in attributes.items():
            setattr(ticket_mock, attr, value)

        ticket_mock.__dir__ = lambda self: [k for k in attributes.keys()]
        mock_get_tickets.return_value = [ticket_mock]

        # When
        result = get_support_tickets(self.mock_user, self.mock_db)
        
        # Then
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 200)

    @patch("controllers.support.SupportTicket.getUserSupportTicket")
    @patch("entities.SupportTicketLog.SupportTicketLog.getTicketLogs")
    @patch("entities.SupportTicketAttachment.SupportTicketAttachment.getAttachmentsByTicketId")
    def test_get_support_ticket_success(self, mock_get_attachments, mock_get_logs, mock_get_ticket):
        # Given
        user_mock = Mock()
        user_mock.__class__ = Mock(spec=DeclarativeMeta)
        user_mock.__class__.registry = Mock()

        user_attributes = {
            "id": 1,
            "email": "test@example.com",
            "is_admin": False,
            "firstname": "Test",
            "lastname": "User",
        }

        for attr, value in user_attributes.items():
            setattr(user_mock, attr, value)

        user_mock.__dir__ = lambda self: [k for k in user_attributes.keys()]

        ticket_mock = Mock(spec=SupportTicket)
        ticket_mock.__class__ = Mock(spec=DeclarativeMeta)
        ticket_mock.__class__.registry = Mock()

        ticket_attributes = {
            "id": 123,
            "user_id": 1,
            "severity": "medium",
            "status": "await agent",
            "selected_product": "test product",
            "subject": "Test Issue",
            "message": "Test message",
            "created_at": self.current_time,
            "last_update": self.current_time,
            "gitlab_issue_id": 456,
            "user": user_mock,
            "metadata": None,
            "query": None,
        }

        for attr, value in ticket_attributes.items():
            setattr(ticket_mock, attr, value)

        ticket_mock.__dir__ = lambda self: [k for k in ticket_attributes.keys()]

        reply_mock = Mock(spec=SupportTicketLog)
        reply_mock.__class__ = Mock(spec=DeclarativeMeta)
        reply_mock.__class__.registry = Mock()

        reply_attributes = {
            "id": 789,
            "status": "await agent",
            "is_admin": False,
            "ticket_id": 123,
            "user_id": 1,
            "message": "Test reply",
            "creation_date": self.current_time,
            "change_date": self.current_time,
            "user": user_mock,
        }

        for attr, value in reply_attributes.items():
            setattr(reply_mock, attr, value)

        reply_mock.__dir__ = lambda self: [k for k in reply_attributes.keys()]

        attachment_mock = Mock(spec=SupportTicketAttachment)
        attachment_attributes = {
            "id": 1,
            "name": "test.txt",
            "user_id": 1,
            "storage_key": "test/path/test.txt",
            "mime_type": "text/plain",
        }

        for attr, value in attachment_attributes.items():
            setattr(attachment_mock, attr, value)

        attachment_mock.__dir__ = lambda self: [k for k in attachment_attributes.keys()]

        mock_get_ticket.return_value = ticket_mock
        mock_get_logs.return_value = [reply_mock]
        mock_get_attachments.return_value = [attachment_mock]
        
        # When
        result = get_support_ticket(self.mock_user, "123", self.mock_db)
        
        # Then
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.status_code, 200)

    @patch("controllers.support.add_gitlab_issue")
    @patch("controllers.support.SupportTicket.attach_gitlab_issue")
    def test_add_support_ticket_success(self, mock_attach_gitlab, mock_add_gitlab):
        # Given
        mock_add_gitlab.return_value = 456
        payload = SupportTicketSchema(
            severity="medium",
            product="test product",
            subject="Test Issue",
            message="Test message",
        )
        
        # When
        result = add_support_ticket(self.mock_user, payload, self.mock_db)
        
        # Then
        self.assertEqual(result.status_code, 201)

    @patch("controllers.support.SupportTicket.getUserSupportTicket")
    @patch("controllers.support.add_gitlab_issue_comment")
    def test_reply_support_ticket_success(self, mock_gitlab_comment, mock_get_ticket):
        # Given
        mock_get_ticket.return_value = self.sample_ticket
        payload = SupportTicketReplySchema(
            message="Test reply",
            status="await agent"
        )
        
        # When
        result = reply_support_ticket(self.mock_user, payload, "123", self.mock_db)
        
        # Then
        self.assertEqual(result.status_code, 200)

    @patch("controllers.support.SupportTicket.getUserSupportTicket")
    @patch("controllers.support.SupportTicketLog.getTicketLog")
    @patch("controllers.support.add_gitlab_issue_comment")
    def test_update_reply_success(self, mock_gitlab_comment, mock_get_log, mock_get_ticket):
        # Given
        mock_get_ticket.return_value = self.sample_ticket
        mock_get_log.return_value = self.sample_reply

        payload = SupportTicketReplySchema(
            message="Updated reply",
            status="await agent"
        )
        
        # When
        result = update_reply_support_ticket(
            self.mock_user, "123", "789", payload, self.mock_db
        )
        
        # Then
        self.assertEqual(result.status_code, 200)

    @patch("controllers.support.SupportTicket.getUserSupportTicket")
    @patch("controllers.support.SupportTicketLog.getTicketLog")
    @patch("controllers.support.add_gitlab_issue_comment")
    def test_delete_reply_success(self, mock_gitlab_comment, mock_get_log, mock_get_ticket):
        # Given
        mock_get_ticket.return_value = self.sample_ticket
        mock_get_log.return_value = self.sample_reply

        # When
        result = delete_reply_support_ticket(self.mock_user, "123", "789", self.mock_db)
        
        # Then
        self.assertEqual(result.status_code, 200)

    def test_delete_reply_unauthorized(self):
        # Given
        unauthorized_reply = Mock(spec=SupportTicketLog)
        unauthorized_reply.user_id = 999

        with (
            patch(
                "controllers.support.SupportTicket.getUserSupportTicket"
            ) as mock_get_ticket,
            patch(
                "controllers.support.SupportTicketLog.getTicketLog"
            ) as mock_get_log,
        ):
            mock_get_ticket.return_value = self.sample_ticket
            mock_get_log.return_value = unauthorized_reply

            # When
            result = delete_reply_support_ticket(
                self.mock_user, "123", "789", self.mock_db
            )
            
            # Then
            self.assertEqual(result.status_code, 403)

    @patch("controllers.support.SupportTicket.getInactiveSupportTickets")
    def test_auto_close_tickets_success(self, mock_get_inactive):
        # Given
        mock_get_inactive.return_value = [self.sample_ticket]
        
        # When
        result = auto_close_tickets(self.mock_user, self.mock_db)
        
        # Then
        self.assertEqual(result.status_code, 200)

    @patch("controllers.support.SupportTicket.getUserSupportTicket")
    @patch("controllers.support.SupportTicketAttachment.getAttachmentByTicketId")
    @patch("controllers.support.download_from_attachment_bucket")
    def test_download_file_success(
        self, mock_download, mock_get_attachment, mock_get_ticket
    ):
        # Given
        mock_get_ticket.return_value = self.sample_ticket
        mock_get_attachment.return_value = self.sample_attachment

        # When
        result = download_file_from_ticket_by_id(
            self.mock_user, "123", "1", self.mock_db
        )
        
        # Then
        self.assertIsInstance(result, FileResponse)

    @patch("controllers.support.SupportTicketAttachment.getAttachmentByTicketId")
    @patch("controllers.support.delete_from_attachment_bucket")
    def test_delete_file_success(self, mock_delete_bucket, mock_get_attachment):
        # Given
        mock_get_attachment.return_value = self.sample_attachment

        # When
        result = delete_file_from_ticket_by_id(self.mock_user, "123", "1", self.mock_db)
        
        # Then
        self.assertEqual(result.status_code, 200)

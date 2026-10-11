from django.test import TestCase, RequestFactory
from accounts.models import CustomUser
from audit.models import AuditLog
from audit.services import log_action

class AuditModuleTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='audit_actor', role=CustomUser.Role.HR_ADMIN)
        self.factory = RequestFactory()

    def test_log_action_creates_record(self):
        request = self.factory.get('/')
        request.user = self.user

        log = log_action(
            actor=self.user,
            action='UPDATE',
            object_type='Employee',
            object_id='EMP-001',
            change_summary='Updated designation to Principal Engineer',
            request=request
        )

        self.assertIsNotNone(log.pk)
        self.assertEqual(log.actor, self.user)
        self.assertEqual(log.action, 'UPDATE')
        self.assertEqual(log.object_type, 'Employee')
        self.assertEqual(log.object_id, 'EMP-001')
        self.assertIn('Principal Engineer', log.change_summary)

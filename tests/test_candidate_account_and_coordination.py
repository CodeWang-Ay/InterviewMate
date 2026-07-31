import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.controllers.plan_controller import InterviewCoordinationAction, coordinate_my_interview, handle_interview_coordination
from backend.repositories import application_repo, auth_session_repo, candidate_repo, favorite_repo, plan_repo, resume_repo


class CandidateAccountAndCoordinationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "candidate-account.db")
        modules = [application_repo, auth_session_repo, candidate_repo, favorite_repo, plan_repo, resume_repo]
        self.patches = [patch.object(module, "DB_PATH", self.db_path) for module in modules]
        for item in self.patches:
            item.start()
        candidate_repo.init_db()
        resume_repo.init_db()
        application_repo.init_db()
        plan_repo.init_db()
        favorite_repo.init_db()

    def tearDown(self):
        candidate_repo.tokens.clear()
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_candidate_can_update_profile_and_change_password(self):
        candidate_repo.register("candidate-a", "password123", "候选人A", "13800138000")
        self.assertTrue(candidate_repo.update_profile("candidate-a", {
            "candidate_name": "新姓名",
            "phone": "13900139000",
            "email": "candidate@example.com",
        }))
        self.assertTrue(candidate_repo.change_password("candidate-a", "password123", "new-password"))
        self.assertIsNone(candidate_repo.login("candidate-a", "password123"))
        login = candidate_repo.login("candidate-a", "new-password")
        self.assertEqual(login["nickname"], "新姓名")
        self.assertEqual(login["phone"], "13900139000")
        self.assertEqual(login["email"], "candidate@example.com")

    def test_candidate_can_reset_password_with_registered_phone(self):
        candidate_repo.register("candidate-b", "password123", "候选人B", "13800138001")
        self.assertFalse(candidate_repo.reset_password_by_phone("candidate-b", "13800138002", "new-password"))
        self.assertTrue(candidate_repo.reset_password_by_phone("candidate-b", "13800138001", "new-password"))
        self.assertIsNotNone(candidate_repo.login("candidate-b", "new-password"))

    def test_candidate_confirmation_and_reschedule_are_persisted(self):
        candidate_repo.register("candidate-c", "password123", "候选人C", "13800138003")
        plan = plan_repo.create({
            "candidate_name": "候选人C",
            "candidate_username": "candidate-c",
            "jd_name": "测试工程师",
            "workflow_id": "workflow-c",
            "workflow_name": "标准流程",
            "interview_round": "综合面试",
            "status": "wait",
            "scheduled_at": "2026-08-10T10:00",
        })

        confirmed = asyncio.run(coordinate_my_interview(
            plan["id"], InterviewCoordinationAction(action="confirm"), "candidate-c"
        ))
        self.assertEqual(confirmed["attendance_status"], "confirmed")

        requested = asyncio.run(coordinate_my_interview(
            plan["id"],
            InterviewCoordinationAction(action="reschedule", reason="时间冲突", preferred_at="2026-08-11T14:00"),
            "candidate-c",
        ))
        self.assertEqual(requested["reschedule_status"], "pending")
        self.assertEqual(requested["reschedule_reason"], "时间冲突")

        approved = asyncio.run(handle_interview_coordination(
            plan["id"],
            InterviewCoordinationAction(action="approve", scheduled_at="2026-08-11T14:00", note="同意"),
            {},
        ))
        self.assertEqual(approved["reschedule_status"], "approved")
        self.assertEqual(approved["scheduled_at"], "2026-08-11T14:00")


if __name__ == "__main__":
    unittest.main()

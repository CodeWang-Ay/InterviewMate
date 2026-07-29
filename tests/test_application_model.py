import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.repositories import application_repo, plan_repo, resume_repo
from backend.services.job_match_service import calculate_resume_jd_match


class ApplicationModelTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "application-model.db")
        self.patches = [
            patch.object(resume_repo, "DB_PATH", self.db_path),
            patch.object(plan_repo, "DB_PATH", self.db_path),
            patch.object(application_repo, "DB_PATH", self.db_path),
        ]
        for item in self.patches:
            item.start()
        resume_repo.init_db()
        plan_repo.init_db()
        application_repo.init_db()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_resume_application_and_plan_use_stable_ids(self):
        resume = resume_repo.create({
            "name": "候选人",
            "file_path": "candidate.pdf",
            "candidate_username": "candidate-user",
            "source": "candidate",
        })
        application = application_repo.create({
            "candidate_username": "candidate-user",
            "candidate_name": "候选人",
            "jd_id": 9,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "source": "candidate",
            "workflow_id": "apply-test",
        })
        plan = plan_repo.create({
            "candidate_username": "candidate-user",
            "candidate_name": "候选人",
            "jd_id": 9,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "resume_filename": resume["file_path"],
            "application_id": application["id"],
            "workflow_id": "apply-test",
        })

        self.assertEqual(plan["resume_id"], resume["id"])
        self.assertEqual(plan["application_id"], application["id"])
        self.assertEqual(application_repo.find_by_candidate_and_jd("candidate-user", 9)["id"], application["id"])
        self.assertEqual(len(application_repo.list_by_resume_id(resume["id"])), 1)
        self.assertEqual(application_repo.cancel(application["id"])["status"], "cancel")

    def test_resumes_can_be_owned_and_filtered_by_source(self):
        resume_repo.create({
            "name": "自主投递",
            "file_path": "self.pdf",
            "candidate_username": "self-user",
            "source": "candidate",
        })
        resume_repo.create({
            "name": "后台推荐",
            "file_path": "admin.pdf",
            "source": "admin",
        })

        self.assertEqual(
            [item["name"] for item in resume_repo.list_by_candidate_username("self-user")],
            ["自主投递"],
        )
        self.assertTrue(any(item["name"] == "自主投递" for item in resume_repo.list_all(source="candidate")))
        self.assertTrue(any(item["name"] == "后台推荐" for item in resume_repo.list_all(source="admin")))

    def test_resume_management_expands_one_resume_into_each_active_application(self):
        resume = resume_repo.create({
            "name": "多岗位候选人",
            "file_path": "multi-job.pdf",
            "candidate_username": "multi-job-user",
            "source": "candidate",
        })
        first = application_repo.create({
            "candidate_username": "multi-job-user",
            "candidate_name": "多岗位候选人",
            "jd_id": 11,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "source": "candidate",
            "workflow_id": "apply-11",
        })
        second = application_repo.create({
            "candidate_username": "multi-job-user",
            "candidate_name": "多岗位候选人",
            "jd_id": 12,
            "jd_name": "平台工程师",
            "resume_id": resume["id"],
            "source": "candidate",
            "workflow_id": "apply-12",
        })
        first_plan = plan_repo.create({
            "candidate_username": "multi-job-user",
            "candidate_name": "多岗位候选人",
            "jd_id": 11,
            "jd_name": "算法工程师",
            "resume_id": resume["id"],
            "application_id": first["id"],
            "workflow_id": "apply-11",
            "status": "pending",
        })
        second_plan = plan_repo.create({
            "candidate_username": "multi-job-user",
            "candidate_name": "多岗位候选人",
            "jd_id": 12,
            "jd_name": "平台工程师",
            "resume_id": resume["id"],
            "application_id": second["id"],
            "workflow_id": "apply-12",
            "status": "pending",
        })

        application_repo.update_screening(first["id"], "不合适")

        items, total = resume_repo.list_management_paged(source="candidate", page=1, page_size=10)

        self.assertEqual(total, 2)
        self.assertEqual({item["application_id"] for item in items}, {first["id"], second["id"]})
        self.assertEqual({item["jd_name"] for item in items}, {"算法工程师", "平台工程师"})
        self.assertEqual({item["id"] for item in items}, {resume["id"]})
        self.assertEqual(len({item["record_key"] for item in items}), 2)
        self.assertTrue(all(item["record_created_at"] for item in items))
        status_by_application = {item["application_id"]: item["candidate_status"] for item in items}
        self.assertEqual(status_by_application[first["id"]], "不合适")
        self.assertEqual(status_by_application[second["id"]], "待筛选")
        self.assertEqual(plan_repo.get_by_id(first_plan["id"])["status"], "cancel")
        self.assertEqual(plan_repo.get_by_id(second_plan["id"])["status"], "pending")

    def test_formal_workflow_backfill_preserves_candidate_application_source(self):
        resume = resume_repo.create({
            "name": "来源测试",
            "file_path": "source-test.pdf",
            "candidate_username": "source-user",
            "source": "candidate",
        })
        application = application_repo.create({
            "candidate_username": "source-user",
            "candidate_name": "来源测试",
            "jd_id": 20,
            "jd_name": "测试岗位",
            "resume_id": resume["id"],
            "source": "candidate",
            "workflow_id": "wf_source_test",
        })
        plan_repo.create({
            "candidate_username": "source-user",
            "candidate_name": "来源测试",
            "jd_id": 20,
            "jd_name": "测试岗位",
            "resume_id": resume["id"],
            "resume_filename": resume["file_path"],
            "application_id": application["id"],
            "workflow_id": "wf_source_test",
            "status": "wait",
        })

        application_repo.init_db()

        self.assertEqual(application_repo.get_by_id(application["id"])["source"], "candidate")

    def test_job_match_is_explainable_and_changes_with_jd(self):
        resume = {
            "id": 1,
            "target_position": "大模型算法工程师",
            "education": "硕士",
            "experience_years": "3年",
            "skills": "Python, PyTorch, LLM, RAG, NLP, Docker",
            "structured_data": json.dumps({
                "基础信息": {"意向岗位": "大模型算法工程师"},
                "项目经历": [{"项目名称": "RAG 知识库"}, {"项目名称": "模型微调"}],
                "工作经历": [{"公司": "科技公司", "职位": "算法工程师"}],
            }, ensure_ascii=False),
        }
        matching_jd = {
            "id": 9,
            "name": "大模型算法工程师",
            "category": "算法",
            "requirements": "硕士，熟悉 Python、PyTorch、LLM、RAG 和 Docker",
            "responsibilities": "负责大模型应用和 NLP 算法研发",
            "experience_required": "1-3年",
        }
        unrelated_jd = {
            "id": 10,
            "name": "Java 后端开发工程师",
            "category": "后端",
            "requirements": "本科，熟悉 Java、SpringBoot、MySQL、Redis",
            "responsibilities": "负责微服务后端开发",
            "experience_required": "5-10年",
        }

        matched = calculate_resume_jd_match(resume, matching_jd)
        unrelated = calculate_resume_jd_match(resume, unrelated_jd)

        self.assertGreater(matched["total_score"], unrelated["total_score"])
        self.assertEqual(sum(item["weight"] for item in matched["dimensions"]), 100)
        self.assertIn("python", matched["matched_skills"])
        self.assertIn("java", unrelated["missing_skills"])

    def test_six_month_quota_is_separate_for_each_recruitment_type(self):
        for jd_id in range(1, 4):
            application_repo.create({
                "candidate_username": "quota-user",
                "candidate_name": "额度测试",
                "jd_id": jd_id,
                "recruitment_type": "社招",
                "source": "candidate",
                "status": "cancel" if jd_id == 1 else "pending",
                "workflow_id": f"quota-{jd_id}",
            })
        application_repo.create({
            "candidate_username": "quota-user",
            "candidate_name": "额度测试",
            "jd_id": 4,
            "recruitment_type": "校招",
            "source": "candidate",
            "workflow_id": "campus-1",
        })
        application_repo.create({
            "candidate_username": "quota-user",
            "candidate_name": "额度测试",
            "jd_id": 99,
            "source": "admin",
            "workflow_id": "admin-invitation",
        })

        quota = application_repo.get_candidate_quota("quota-user")
        self.assertEqual(quota["buckets"]["社招"]["used"], 2)
        self.assertEqual(quota["buckets"]["社招"]["remaining"], 1)
        self.assertFalse(quota["buckets"]["社招"]["available_at"])
        self.assertEqual(quota["buckets"]["校招"]["remaining"], 2)
        self.assertEqual(quota["buckets"]["实习生"]["remaining"], 3)
        self.assertNotIn(1, [item["jd_id"] for item in quota["applications"]])

    def test_candidate_application_placeholder_never_opens_interview(self):
        resume = resume_repo.create({
            "name": "待筛选候选人",
            "file_path": "pending.pdf",
            "candidate_username": "pending-user",
            "candidate_status": "待筛选",
            "source": "candidate",
        })
        plan = plan_repo.create({
            "candidate_name": "待筛选候选人",
            "candidate_username": "pending-user",
            "workflow_id": "apply_7_pending-user_test",
            "workflow_name": "投递：后端工程师",
            "resume_id": resume["id"],
            "resume_filename": resume["file_path"],
            "status": "pending",
        })

        listed = plan_repo.list_by_candidate_username("pending-user")
        refreshed = next(item for item in listed if item["id"] == plan["id"])
        ready, reason = plan_repo.candidate_interview_readiness(refreshed)

        self.assertEqual(refreshed["status"], "pending")
        self.assertFalse(ready)
        self.assertIn("尚未开放", reason)

    def test_formal_workflow_requires_resume_screening_pass(self):
        resume = resume_repo.create({
            "name": "流程候选人",
            "file_path": "workflow.pdf",
            "candidate_username": "workflow-user",
            "candidate_status": "待筛选",
            "source": "candidate",
        })
        plan = plan_repo.create({
            "candidate_name": "流程候选人",
            "candidate_username": "workflow-user",
            "workflow_id": "wf_formal_test",
            "workflow_name": "标准技术岗流程",
            "resume_id": resume["id"],
            "resume_filename": resume["file_path"],
            "status": "wait",
        })

        ready, reason = plan_repo.candidate_interview_readiness(plan)
        self.assertFalse(ready)
        self.assertEqual(reason, "简历尚未通过初筛")

        resume_repo.update(resume["id"], {"candidate_status": "初筛通过"})
        ready, reason = plan_repo.candidate_interview_readiness(plan)
        self.assertTrue(ready)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()

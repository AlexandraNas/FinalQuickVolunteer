"""Tests for the Sprint 3 changes: notifications both ways, withdrawing an
offer, profile editing with admin checks, member summaries, skills with
levels and importance, reports about something else, ID verification and
the admin member list."""

import unittest
from pathlib import Path

from tests import test_backend
from db import get_db_connection
from werkzeug.security import generate_password_hash





class Sprint3Tests(unittest.TestCase):
    # Reuse the shared set up and helpers without running the other tests again.
    setUpClass = test_backend.QuickVolunteerTests.setUpClass
    setUp = test_backend.QuickVolunteerTests.setUp
    csrf_headers = test_backend.QuickVolunteerTests.csrf_headers
    post = test_backend.QuickVolunteerTests.post
    patch = test_backend.QuickVolunteerTests.patch
    put = test_backend.QuickVolunteerTests.put
    upload_id = test_backend.QuickVolunteerTests.upload_id
    register_user = test_backend.QuickVolunteerTests.register_user
    login_user = test_backend.QuickVolunteerTests.login_user
    create_task = test_backend.QuickVolunteerTests.create_task

    # ---------- helpers ----------

    def sql(self, query, params=(), fetch=False):
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall() if fetch else None
            connection.commit()
            return rows
        finally:
            cursor.close()
            connection.close()

    def make_admin(self, email="admin@test.com"):
        self.sql("""
            INSERT INTO users (first_name, last_name, email, password_hash,
                               account_type, account_status)
            VALUES ('Test', 'Admin', %s, %s, 'admin', 'active')
        """, (email, generate_password_hash("TestingPassword123!")))

    def notifications_for(self, email):
        return self.sql("""
            SELECT n.title, n.content
            FROM notifications AS n JOIN users AS u ON u.user_id = n.user_id
            WHERE u.email = %s ORDER BY n.notification_id
        """, (email,), fetch=True)

    def user_id(self, email):
        return self.sql("SELECT user_id FROM users WHERE email = %s",
                        (email,), fetch=True)[0]["user_id"]

    def seeker_task_and_offer(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.register_user("volunteer@test.com", "volunteer")
        self.login_user("seeker@test.com")
        task_id = self.create_task().get_json()["task_id"]
        self.login_user("volunteer@test.com")
        response = self.post(f"/api/tasks/{task_id}/apply")
        self.assertEqual(response.status_code, 201)
        return task_id, response.get_json()["application_id"]

    # ---------- notifications ----------

    def test_s01_offer_notifies_help_seeker(self):
        self.seeker_task_and_offer()
        notes = self.notifications_for("seeker@test.com")
        self.assertEqual(notes[-1]["title"], "New offer to help")
        self.assertIn("Test U.", notes[-1]["content"])

    def test_s02_closing_request_notifies_volunteers(self):
        task_id, _ = self.seeker_task_and_offer()
        self.login_user("seeker@test.com")
        self.assertEqual(self.patch(f"/api/tasks/{task_id}/cancel").status_code, 200)
        notes = self.notifications_for("volunteer@test.com")
        self.assertEqual(notes[-1]["title"], "Request closed")

    def test_s03_first_confirmation_asks_other_person(self):
        task_id, application_id = self.seeker_task_and_offer()
        self.login_user("seeker@test.com")
        self.patch(f"/api/applications/{application_id}/decision",
                   json={"decision": "accepted"})
        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")
        notes = self.notifications_for("seeker@test.com")
        self.assertEqual(notes[-1]["title"], "Please confirm the task")
        self.login_user("seeker@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")
        self.assertEqual(
            self.notifications_for("volunteer@test.com")[-1]["title"],
            "Task completed"
        )

    # ---------- withdrawing an offer ----------

    def test_s04_withdrawn_offer_is_deleted_and_seeker_notified(self):
        task_id, application_id = self.seeker_task_and_offer()
        response = self.client.delete(f"/api/applications/{application_id}",
                                      headers=self.csrf_headers())
        self.assertEqual(response.status_code, 200)
        rows = self.sql("SELECT * FROM task_applications WHERE task_id = %s",
                        (task_id,), fetch=True)
        self.assertEqual(rows, [])
        self.assertEqual(self.notifications_for("seeker@test.com")[-1]["title"],
                         "Offer withdrawn")
        # Not shown in the volunteer's own list either.
        self.assertEqual(
            self.client.get("/api/my-applications").get_json()["applications"], []
        )

    def test_s05_withdrawing_accepted_offer_reopens_task(self):
        task_id, application_id = self.seeker_task_and_offer()
        self.login_user("seeker@test.com")
        self.patch(f"/api/applications/{application_id}/decision",
                   json={"decision": "accepted"})
        self.login_user("volunteer@test.com")
        response = self.client.delete(f"/api/applications/{application_id}",
                                      headers=self.csrf_headers())
        self.assertEqual(response.status_code, 200)
        status = self.sql("SELECT status FROM tasks WHERE task_id = %s",
                          (task_id,), fetch=True)[0]["status"]
        self.assertEqual(status, "open")

    def test_s06_cannot_withdraw_someone_elses_offer(self):
        _, application_id = self.seeker_task_and_offer()
        self.register_user("other@test.com", "volunteer")
        self.login_user("other@test.com")
        response = self.client.delete(f"/api/applications/{application_id}",
                                      headers=self.csrf_headers())
        self.assertEqual(response.status_code, 403)

    # ---------- profiles ----------

    def test_s07_member_can_edit_profile_and_admin_is_notified(self):
        self.make_admin()
        self.register_user("member@test.com", "both")
        self.login_user("member@test.com")
        response = self.patch("/api/users/me", json={
            "about_me": "I enjoy gardening and a chat.",
            "postcode": "e8 1aa",
            "neighbourhood": "Hackney",
            "preferred_mode": "in_person",
            "max_distance_miles": 3,
        })
        self.assertEqual(response.status_code, 200)

        profile = self.client.get("/api/users/me/profile").get_json()["profile"]
        self.assertEqual(profile["postcode"], "E8 1AA")
        self.assertEqual(profile["about_me"], "I enjoy gardening and a chat.")
        self.assertEqual(profile["max_distance_miles"], 3)

        notes = self.notifications_for("admin@test.com")
        self.assertEqual(notes[-1]["title"], "Profile changes to check")
        self.assertIn("about me", notes[-1]["content"])

    def test_s08_profile_validation(self):
        self.register_user("member@test.com", "both")
        self.login_user("member@test.com")
        for bad in ({"account_type": "admin"}, {"postcode": "123"},
                    {"preferred_mode": "car"}, {"max_distance_miles": 0},
                    {"first_name": ""}, {"about_me": "x" * 1001}):
            self.assertEqual(self.patch("/api/users/me", json=bad).status_code, 400)

    def test_s09_member_summary_shows_agreed_details_only(self):
        task_id, application_id = self.seeker_task_and_offer()
        self.login_user("seeker@test.com")
        offers = self.client.get(f"/api/tasks/{task_id}/applications").get_json()
        volunteer = offers["applications"][0]["volunteer"]
        self.assertEqual(set(volunteer), {
            "user_id", "display_name", "member_since", "verified", "about_me",
            "skills", "completed_tasks", "completed_as_volunteer",
            "completed_as_requester"
        })
        self.assertEqual(volunteer["display_name"], "Test U.")
        self.assertNotIn("email", volunteer)

        # Logged out visitors cannot see members.
        self.post("/api/logout")
        response = self.client.get(f"/api/users/{volunteer['user_id']}/summary")
        self.assertEqual(response.status_code, 401)

    def test_s10_admin_summary_is_hidden(self):
        self.make_admin()
        self.register_user("member@test.com", "both")
        self.login_user("member@test.com")
        admin_id = self.user_id("admin@test.com")
        self.assertEqual(
            self.client.get(f"/api/users/{admin_id}/summary").status_code, 404
        )

    # ---------- skills ----------

    def test_s11_at_least_one_skill_with_optional_level(self):
        self.register_user("member@test.com", "volunteer")
        self.login_user("member@test.com")
        self.assertEqual(self.put("/api/users/me/skills",
                                  {"skill_ids": []}).status_code, 400)
        response = self.put("/api/users/me/skills", {
            "skills": [{"skill_id": 1, "skill_level": "advanced"},
                       {"skill_id": 2}]
        })
        self.assertEqual(response.status_code, 200)
        skills = self.client.get("/api/users/me/skills").get_json()["skills"]
        levels = {s["skill_id"]: s["skill_level"] for s in skills}
        self.assertEqual(levels, {1: "advanced", 2: None})
        self.assertEqual(self.client.get("/api/me").get_json()["user"]["skill_count"], 2)

    def test_s12_task_skills_store_importance(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")
        task_id = self.create_task().get_json()["task_id"]
        response = self.put(f"/api/tasks/{task_id}/skills",
                            {"skill_ids": [1, 2], "required_skill_ids": [2]})
        self.assertEqual(response.status_code, 200)
        skills = self.client.get(f"/api/tasks/{task_id}/skills").get_json()["skills"]
        self.assertEqual(skills[0]["skill_id"], 2)
        self.assertEqual(skills[0]["importance"], "required")
        self.assertEqual(skills[1]["importance"], "helpful")

    # ---------- reports ----------

    def test_s13_report_something_else(self):
        self.make_admin()
        self.register_user("member@test.com", "both")
        self.login_user("member@test.com")
        missing = self.post("/api/reports", {"target_type": "other",
                                             "reason": "Odd behaviour"})
        self.assertEqual(missing.status_code, 400)
        response = self.post("/api/reports", {
            "target_type": "other",
            "other_details": "A message I received outside the website",
            "reason": "Someone asked for my bank details",
            "contact_allowed": False,
        })
        self.assertEqual(response.status_code, 201)

        self.login_user("admin@test.com")
        report = self.client.get("/api/admin/reports").get_json()["reports"][0]
        self.assertEqual(report["target_type"], "other")
        self.assertFalse(report["contact_allowed"])
        self.assertIsNone(report["reporter_email"])

    def test_s14_admin_sees_email_when_contact_allowed(self):
        self.make_admin()
        task_id, _ = self.seeker_task_and_offer()
        self.post("/api/reports", {"task_id": task_id, "reason": "Unsafe task",
                                   "contact_allowed": True})
        self.login_user("admin@test.com")
        report = self.client.get("/api/admin/reports").get_json()["reports"][0]
        self.assertEqual(report["target_type"], "task")
        self.assertEqual(report["reporter_email"], "volunteer@test.com")
        self.assertEqual(report["task_title"], "Help with shopping")

    # ---------- verification ----------

    def test_s15_document_only_for_admin_and_deleted_after_decision(self):
        self.make_admin()
        self.register_user("member@test.com", "both")
        self.login_user("member@test.com")
        verification_id = self.upload_id().get_json()["verification_id"]
        self.assertEqual(
            self.client.get(f"/api/admin/verifications/{verification_id}/document").status_code,
            403
        )
        self.assertFalse(self.client.get("/api/me").get_json()["user"]["verified"])

        self.login_user("admin@test.com")
        listing = self.client.get("/api/admin/verifications?status=pending").get_json()
        self.assertTrue(listing["verifications"][0]["has_document"])
        self.assertEqual(listing["verifications"][0]["email"], "member@test.com")
        document = self.client.get(f"/api/admin/verifications/{verification_id}/document")
        self.assertEqual(document.status_code, 200)
        self.assertEqual(document.mimetype, "image/png")
        self.assertEqual(document.headers["Cache-Control"], "no-store")
        document.close()

        reference = self.sql("SELECT evidence_reference FROM user_verifications "
                             "WHERE verification_id = %s", (verification_id,),
                             fetch=True)[0]["evidence_reference"]
        from verification_routes import UPLOAD_DIR
        self.assertTrue((Path(UPLOAD_DIR) / reference).is_file())

        self.patch(f"/api/admin/verifications/{verification_id}/decision",
                   json={"status": "approved", "admin_notes": "Clear photo"})
        self.assertFalse((Path(UPLOAD_DIR) / reference).exists())
        self.assertEqual(
            self.client.get(f"/api/admin/verifications/{verification_id}/document").status_code,
            404
        )
        self.assertEqual(self.notifications_for("member@test.com")[-1]["title"],
                         "Profile verified")

        self.login_user("member@test.com")
        self.assertTrue(self.client.get("/api/me").get_json()["user"]["verified"])

    def test_s16_task_list_shows_if_creator_is_verified(self):
        self.register_user("seeker@test.com", "help_seeker")
        self.login_user("seeker@test.com")
        self.create_task()
        self.assertFalse(self.client.get("/api/tasks").get_json()[0]["creator_verified"])
        self.sql("""INSERT INTO user_verifications (user_id, status)
                    VALUES (%s, 'approved')""", (self.user_id("seeker@test.com"),))
        self.assertTrue(self.client.get("/api/tasks").get_json()[0]["creator_verified"])

    # ---------- admin member list ----------

    def test_s17_admin_sees_completed_counts_and_can_suspend(self):
        self.make_admin()
        task_id, application_id = self.seeker_task_and_offer()
        self.login_user("seeker@test.com")
        self.patch(f"/api/applications/{application_id}/decision",
                   json={"decision": "accepted"})
        self.patch(f"/api/tasks/{task_id}/complete")
        self.login_user("volunteer@test.com")
        self.patch(f"/api/tasks/{task_id}/complete")

        # Members cannot use the admin list.
        self.assertEqual(self.client.get("/api/admin/members").status_code, 403)

        self.login_user("admin@test.com")
        members = {m["email"]: m for m in
                   self.client.get("/api/admin/members").get_json()["members"]}
        self.assertEqual(members["volunteer@test.com"]["completed_as_volunteer"], 1)
        self.assertEqual(members["seeker@test.com"]["completed_as_requester"], 1)
        self.assertNotIn("admin@test.com", members)

        volunteer_id = members["volunteer@test.com"]["user_id"]
        response = self.patch(f"/api/admin/users/{volunteer_id}/status",
                              json={"status": "suspended"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.login_user("volunteer@test.com").status_code, 403)

        self.login_user("admin@test.com")
        self.patch(f"/api/admin/users/{volunteer_id}/status", json={"status": "active"})
        self.assertEqual(self.login_user("volunteer@test.com").status_code, 200)

    def test_s19_admin_can_delete_a_task(self):
        self.make_admin()
        task_id, application_id = self.seeker_task_and_offer()

        # Members cannot delete tasks, not even their own.
        self.login_user("seeker@test.com")
        self.assertEqual(self.client.delete(f"/api/admin/tasks/{task_id}",
                                            headers=self.csrf_headers()).status_code, 403)

        self.login_user("admin@test.com")
        response = self.client.delete(f"/api/admin/tasks/{task_id}", headers=self.csrf_headers())
        self.assertEqual(response.status_code, 200)

        row = self.sql("SELECT status FROM tasks WHERE task_id = %s", (task_id,), fetch=True)[0]
        self.assertEqual(row["status"], "closed")
        offer = self.sql("SELECT status FROM task_applications WHERE application_id = %s",
                         (application_id,), fetch=True)[0]
        self.assertEqual(offer["status"], "rejected")
        ids = [t["task_id"] for t in self.client.get("/api/tasks").get_json()]
        self.assertNotIn(task_id, ids)
        self.assertTrue(any(n["title"] == "Request removed"
                            for n in self.notifications_for("seeker@test.com")))
        self.assertTrue(any(n["title"] == "Request removed"
                            for n in self.notifications_for("volunteer@test.com")))

        # A closed task cannot be deleted again, and a missing one is not found.
        self.assertEqual(self.client.delete(f"/api/admin/tasks/{task_id}",
                                            headers=self.csrf_headers()).status_code, 409)
        self.assertEqual(self.client.delete("/api/admin/tasks/999999",
                                            headers=self.csrf_headers()).status_code, 404)

    def test_s18_admin_can_list_reviews(self):
        self.make_admin()
        self.login_user("admin@test.com")
        response = self.client.get("/api/admin/reviews")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 0)


if __name__ == "__main__":
    unittest.main()

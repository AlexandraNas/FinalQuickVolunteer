
# QuickVolunteer: Backend API Documentation

## 1. Overview

QuickVolunteer is a volunteering platform for small tasks lasting
15–60 minutes.

Backend: Python, Flask
Database: MySQL 8.0
API format: JSON
Authentication: Flask sessions (cookies)
CSRF protection: Flask-WTF

The frontend should communicate with the Flask backend using
the endpoints documented below.

## 2. Authentication and CSRF

Before sending POST or PATCH requests, obtain a CSRF token:

GET /api/csrf-token

Expected JSON field:

{
  "csrf_token": "TOKEN_VALUE"
}

Include the token in the request header:

X-CSRFToken: TOKEN_VALUE

For JSON requests, also use:

Content-Type: application/json

Authentication uses Flask session cookies.

When frontend and backend are on different origins,
the browser must be configured to send credentials,
and the backend must explicitly support the required
cross-origin requests.

## 3. Register

POST /api/register

Request:

{
  "first_name": "Alex",
  "last_name": "Smith",
  "email": "alex@example.com",
  "password": "SecurePassword123!",
  "account_type": "volunteer"
}

Allowed account types:
- volunteer
- help_seeker
- both

Password: minimum 12 characters.

Success: HTTP 201

{
  "message": "Account created successfully",
  "user_id": 1,
  "account_type": "volunteer"
}

Possible errors:
- 400: Invalid or missing fields
- 409: Email already registered or invalid account details

Public administrator registration is not permitted.

Current development behaviour: new accounts are immediately
activated. Users can request account verification, and administrators
can approve or reject verification requests.

DBS verification is separate from account activation. Volunteers
must have an approved DBS verification record before applying
for tasks that require DBS.

## 4. Login

POST /api/login

Request:

{
  "email": "alex@example.com",
  "password": "SecurePassword123!"
}

Success: HTTP 200

{
  "message": "Login successful",
  "user": {
    "user_id": 1,
    "first_name": "Alex",
    "email": "alex@example.com",
    "account_type": "volunteer"
  }
}

Possible errors:
- 400: Missing email or password
- 401: Invalid credentials
- 403: Account not active

Login creates a Flask session cookie.

## 5. Current User

GET /api/me

Requires authentication.

Success: HTTP 200

{
  "user": {
    "user_id": 1,
    "first_name": "Alex",
    "last_name": "Smith",
    "email": "alex@example.com",
    "account_type": "volunteer"
  }
}

Error:
- 401: Not logged in or invalid session

## 6. Logout

POST /api/logout

Requires authentication and CSRF token.

Success: HTTP 200

{
  "message": "Logged out successfully"
}

## 7. Task Permissions

GET /api/tasks/permissions

Available to help_seeker and both accounts.

Success: HTTP 200

{
  "message": "You have permission to create tasks",
  "user_id": 1
}

## 8. Volunteer Permissions

GET /api/volunteer/permissions

Available to volunteer and both accounts.

Success: HTTP 200

{
  "message": "You have permission to apply for tasks",
  "user_id": 2
}

## 9. Browse Open Tasks

GET /api/tasks

Returns the list of open tasks.

The exact response fields should be checked against
backend/app.py before implementing frontend parsing.



## My Tasks — Help Seeker Dashboard

GET /api/my-tasks

Requires authentication and a help_seeker or both account.

Returns only tasks created by the logged-in user.

Success: HTTP 200

Example response:

{
  "tasks": [
    {
      "task_id": 1,
      "title": "Help with shopping",
      "description": "Collect groceries from a local shop.",
      "location_text": "Stratford",
      "delivery_mode": "in_person",
      "estimated_minutes": 30,
      "deadline_at": "2030-12-01T15:00:00",
      "status": "open",
      "created_at": "2026-10-16T13:30:00",
      "category_name": "Community Support"
    }
  ]
}

Possible errors:
- 401: Not logged in
- 403: Insufficient permissions

Tasks may have these statuses:
- open
- filled
- completed
- closed

## My Applications — Volunteer Dashboard

GET /api/my-applications

Requires authentication and a volunteer or both account.

Returns only applications submitted by the logged-in user.

Success: HTTP 200

Example response:

{
  "applications": [
    {
      "application_id": 5,
      "task_id": 1,
      "application_status": "pending",
      "applied_at": "2026-10-16T14:00:00",
      "accepted_at": null,
      "volunteer_completed_at": null,
      "help_seeker_completed_at": null,
      "title": "Help with shopping",
      "description": "Collect groceries from a local shop.",
      "delivery_mode": "in_person",
      "location_text": "Stratford",
      "estimated_minutes": 30,
      "deadline_at": "2030-12-01T15:00:00",
      "task_status": "open",
      "category_name": "Community Support"
    }
  ]
}

Possible errors:
- 401: Not logged in
- 403: Insufficient permissions

Application statuses:
- pending
- accepted
- rejected
- completed

An empty list is returned when the user has no
tasks or applications.


## 10. Create a Task

POST /api/tasks

Requires help_seeker or both account.

Request:

{
  "title": "Help with shopping",
  "description": "Collect groceries from a local shop.",
  "category_id": 1,
  "delivery_mode": "in_person",
  "location_text": "Stratford",
  "postcode": "E15 1AA",
  "estimated_minutes": 30,
  "deadline_at": "2030-12-01T23:59:00"
}

Required:
- title
- description
- category_id
- delivery_mode
- estimated_minutes
- deadline_at (always required; created_at is saved automatically)

For in_person tasks, location_text (neighbourhood) and postcode are
also required. The postcode is checked as a UK postcode and saved in
upper case, for example "E15 1AA". Remote tasks store no postcode or
location, even if they are sent.

delivery_mode:
- in_person
- remote

estimated_minutes:
- Integer between 15 and 60

deadline_at:
- Required
- Must be in the future
- ISO-format datetime without timezone information

category_id:
- Must reference an existing category in the database

DBS checks and home or public visit types are a later feature and are
not part of this version.

Success: HTTP 201

{
  "message": "Task created successfully",
  "task_id": 1
}

Possible errors:
- 400: Invalid task details or category
- 401: Not logged in
- 403: Insufficient permissions

## 11. Apply for a Task

POST /api/tasks/{task_id}/apply

Requires volunteer or both account.

No JSON body required.

The help seeker receives an in-app notification ("New offer to help").

Success: HTTP 201

{
  "message": "Application submitted successfully",
  "application_id": 1,
  "task_id": 1,
  "status": "pending"
}

Possible errors:
- 401: Not logged in
- 403: Insufficient permissions or own task
- 404: Task not found
- 409: Duplicate application, unavailable task,
       or expired deadline



## View Applications for a Task

GET /api/tasks/{task_id}/applications

Requires authentication.

Only the help seeker who created the task can view
its volunteer applications.

Success: HTTP 200

Example response:

{
  "task_id": 1,
  "applications": [
    {
      "application_id": 5,
      "task_id": 1,
      "volunteer_id": 2,
      "first_name": "Alex",
      "last_name": "Smith",
      "status": "pending",
      "applied_at": "2026-10-16T13:30:00"
    }
  ]
}

If nobody has applied:

{
  "task_id": 1,
  "applications": []
}

Possible errors:
- 401: Not logged in
- 403: Not authorised to view this task
- 404: Task not found

The frontend can use application_id to accept or
reject an application through:

PATCH /api/applications/{application_id}/decision

Volunteer passwords and contact details are not
included in the response.


## 12. Accept or Reject an Application

PATCH /api/applications/{application_id}/decision

Requires the help seeker who created the task.

Accept:

{
  "decision": "accepted"
}

Reject:

{
  "decision": "rejected"
}

Success: HTTP 200

{
  "message": "Application reviewed successfully",
  "application_id": 1,
  "status": "accepted"
}

When an application is accepted:
- Task status changes from open to filled
- The selected application becomes accepted
- Other pending applications are rejected

Only one volunteer can be accepted per task.

Possible errors:
- 400: Invalid decision
- 401: Not logged in
- 403: Not authorised
- 404: Application or task not found
- 409: Already reviewed or invalid task status

## 13. Confirm Task Completion

PATCH /api/tasks/{task_id}/complete

Requires the task creator or accepted volunteer.

No JSON body required.

The task must be filled before confirmation.

First confirmation:

{
  "message": "Completion confirmed; waiting for the other person",
  "task_id": 1,
  "status": "filled",
  "volunteer_confirmed": true,
  "help_seeker_confirmed": false
}

After both confirm:

{
  "message": "Task completed successfully",
  "task_id": 1,
  "status": "completed",
  "volunteer_confirmed": true,
  "help_seeker_confirmed": true
}

The order of confirmation can be reversed.

Possible errors:
- 401: Not logged in
- 403: Not authorised
- 404: Task not found
- 409: Invalid task status, duplicate confirmation,
       or already completed

## 14. Task Status Workflow

open
  |
  | Volunteer applies
  v
Application: pending
  |
  | Help seeker accepts
  v
Task: filled
Application: accepted
  |
  | Volunteer and help seeker both confirm
  v
Task: completed
Application: completed

## 15. Frontend Integration Notes

- Use account_type rather than role.
- Preserve the Flask session cookie after login.
- Include CSRF tokens for modifying requests.
- Handle HTTP errors using the JSON error field.
- Display task status based on API responses.
- Do not store MySQL credentials in frontend code.
- Do not assume a task is completed after only one
  confirmation.
- Use category IDs that exist in the MySQL database.

## 16. Later features (not in this version)

- DBS checks and home visit rules
- Messages between members (tables exist for the future version)
- Email or text message notifications (in-app notifications work now)
- Profile photos
- Preferred connections (choosing favourite members)
- Volunteer levels based on completed tasks
- A message to the requester when offering to help

## GET /api/categories

Returns all task categories.

Authentication: Not required.

Success: HTTP 200

Response: JSON array containing:
- category_id
- category_name

Categories are ordered alphabetically by category_name.

Used by the frontend when displaying the
category dropdown for task creation.


## PATCH /api/tasks/<task_id>/cancel

Cancels an existing task.

Authentication: Required.
Allowed account types: help_seeker or both.
Only the task creator can cancel the task.

CSRF: Required. Include the X-CSRFToken header
and the authenticated Flask session cookie.

Request body: Not required.

Allowed task statuses:
- open
- filled

Successful cancellation:
- Changes task status to closed.
- Rejects pending volunteer applications.
- Removes the task from the public GET /api/tasks list.
- Preserves the task in the creator's task history.
- Preserves accepted applications for historical purposes.

Success: HTTP 200

Example response:
{
  "message": "Task cancelled successfully",
  "task_id": 4,
  "status": "closed"
}

Possible errors:
- 401: Not authenticated
- 403: Insufficient permissions or not the task creator
- 404: Task not found
- 409: Task cannot be cancelled in its current status
- 400: Missing or invalid CSRF token

Note: For a filled task, the accepted application
remains accepted, but the task status becomes closed.
The volunteer dashboard should check task_status
before displaying completion actions.


## Sprint 3 additions

### Notifications (in-app)
Sent automatically:
- Volunteer offers to help: the help seeker gets "New offer to help".
- Help seeker accepts or declines: the volunteer gets "Offer accepted" or "Offer declined".
- Help seeker closes a request: volunteers who offered get "Request closed".
- Volunteer withdraws an offer: the help seeker gets "Offer withdrawn".
- One person confirms completion: the other gets "Please confirm the task";
  when both confirm, both get "Task completed".
- Profile changes, ID documents and new reports: administrators are notified.

### Withdraw an offer
DELETE /api/applications/{application_id} (volunteer, own offer only)
The offer is deleted, so it is not recorded anywhere. Withdrawing an
accepted offer opens the task again. 409 once the volunteer has confirmed.

### My profile
GET /api/users/me/profile
PATCH /api/users/me with any of: first_name, last_name, postcode,
neighbourhood, about_me (max 1000), availability_notes, preferred_mode
(in_person, remote, any), max_distance_miles (1 to 50), account_type
(help_seeker, volunteer, both), phone, preferred_language.
Every change notifies the administrators ("Profile changes to check").

### Member summary
GET /api/users/{user_id}/summary (logged in only)
Returns only: display_name (first name and initial), member_since,
verified, about_me, skills, completed_tasks (also split into
completed_as_volunteer and completed_as_requester). Offers listed by
GET /api/tasks/{task_id}/applications include the same summary as
"volunteer". Administrator accounts are never shown.

### Skills
- GET /api/skills includes category.
- PUT /api/users/me/skills: {"skill_ids": [...]} or
  {"skills": [{"skill_id": 1, "skill_level": "beginner"}]}.
  At least one skill is required.
- PUT /api/tasks/{task_id}/skills: {"skill_ids": [...],
  "required_skill_ids": [...]} or {"skills": [{"skill_id": 1,
  "importance": "required"}]}. Default importance is helpful.

### Reports
POST /api/reports: {"target_type": "user" | "task" | "other",
"reported_user_id" or "task_id" or "other_details", "reason",
"contact_allowed": true}. Exactly one target. GET /api/admin/reports
includes names, the task title and the reporter's email only when
contact_allowed is true.

### Profile verification (optional, ID document only)
POST /api/verifications as multipart/form-data with a "document" file:
JPG, PNG or PDF, up to 5 MB, checked by its content. The file is saved
with a random name in a private folder (QV_PRIVATE_UPLOAD_DIR, default
private_uploads/) that the website never serves.
GET /api/admin/verifications lists requests with member details.
GET /api/admin/verifications/{id}/document lets an administrator view
the file. PATCH .../decision {"status": "approved" | "rejected",
"admin_notes": "..."} deletes the file and notifies the member.
GET /api/me includes "verified" and "skill_count"; GET /api/tasks
includes "creator_verified" and "postcode".

### Administrator
- GET /api/admin/members: members with completed task counts (the
  dashboard for members shows no hours or totals).
- PATCH /api/admin/users/{user_id}/status {"status": "active" | "suspended"}
- GET /api/admin/reviews: reviews with names and task title; hide or
  restore with PATCH /api/admin/reviews/{review_id}/moderation.

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Body, FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from mock_bodys import (
    csp_body,
    markov_decision_process_body,
    naermestenabo_body,
    naiv_bayes_body,
    nevralenettverk_body,
    reinforcement_learning_body,
)
from pydantic import BaseModel

app = FastAPI(title="Mock Canvas Server", version="1.0.0")

mock_quizzes = []
mock_quiz_items = []

# Mock data storage
mock_users = {
    "12345": {
        "id": 12345,
        "name": "Marius Solaas",
        "email": "marius.solaas@example.com",
        "login_id": "jteacher",
        "avatar_url": "https://example.com/avatar.jpg",
    }
}

mock_courses = [
    {
        "id": 37823,
        "name": "INF-2600 AI Methods and applications",
        "account_id": 27925,
        "uuid": "hfv2nToY5ae1MbmNWTfNhTpzVbwq9ENcT00yTEiK",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:18Z",
        "course_code": "INF-2600",
        "default_view": "wiki",
        "root_account_id": 1,
        "enrollment_term_id": 3,
        "license": "private",
        "grade_passback_setting": None,
        "end_at": None,
        "public_syllabus": False,
        "public_syllabus_to_auth": True,
        "storage_quota_mb": 3145,
        "is_public_to_auth_users": True,
        "homeroom_course": False,
        "course_color": None,
        "friendly_name": None,
        "apply_assignment_group_weights": False,
        "calendar": {
            "ics": "https://uit.instructure.com/feeds/calendars/course_hfv2nToY5ae1MbmNWTfNhTpzVbwq9ENcT00yTEiK.ics"
        },
        "time_zone": "Europe/Copenhagen",
        "blueprint": False,
        "template": False,
        "sis_course_id": None,
        "integration_id": None,
        "enrollments": [
            {
                "type": "teacher",
                "role": "TeacherEnrollment",
                "role_id": 4,
                "user_id": 71202,
                "enrollment_state": "active",
                "limit_privileges_to_course_section": False,
            }
        ],
        "hide_final_grades": False,
        "workflow_state": "unpublished",
        "restrict_enrollments_to_course_dates": False,
    },
    {
        "id": 37824,
        "name": "ALI-1111 Episk diktning fra ca 1800 til i dag",
        "account_id": 27925,
        "uuid": "Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:29Z",
        "course_code": "ALI-1111",
        "default_view": "wiki",
        "root_account_id": 1,
        "enrollment_term_id": 3,
        "license": "private",
        "grade_passback_setting": None,
        "end_at": None,
        "public_syllabus": False,
        "public_syllabus_to_auth": True,
        "storage_quota_mb": 3145,
        "is_public_to_auth_users": True,
        "homeroom_course": False,
        "course_color": None,
        "friendly_name": None,
        "apply_assignment_group_weights": False,
        "calendar": {
            "ics": "https://uit.instructure.com/feeds/calendars/course_Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3.ics"
        },
        "time_zone": "Europe/Copenhagen",
        "blueprint": False,
        "template": False,
        "sis_course_id": None,
        "integration_id": None,
        "enrollments": [
            {
                "type": "teacher",
                "role": "TeacherEnrollment",
                "role_id": 4,
                "user_id": 71202,
                "enrollment_state": "active",
                "limit_privileges_to_course_section": False,
            }
        ],
        "hide_final_grades": False,
        "workflow_state": "unpublished",
        "restrict_enrollments_to_course_dates": False,
    },
    {
        "id": 37825,
        "name": "INF-1600 Intro til KI",
        "account_id": 27925,
        "uuid": "Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:29Z",
        "course_code": "ALI-1111",
        "default_view": "wiki",
        "root_account_id": 1,
        "enrollment_term_id": 3,
        "license": "private",
        "grade_passback_setting": None,
        "end_at": None,
        "public_syllabus": False,
        "public_syllabus_to_auth": True,
        "storage_quota_mb": 3145,
        "is_public_to_auth_users": True,
        "homeroom_course": False,
        "course_color": None,
        "friendly_name": None,
        "apply_assignment_group_weights": False,
        "calendar": {
            "ics": "https://uit.instructure.com/feeds/calendars/course_Z7bzNStMko53AmlPm6R7qYPbBlLUWkGobbpBqlJ3.ics"
        },
        "time_zone": "Europe/Copenhagen",
        "blueprint": False,
        "template": False,
        "sis_course_id": None,
        "integration_id": None,
        "enrollments": [
            {
                "type": "teacher",
                "role": "TeacherEnrollment",
                "role_id": 4,
                "user_id": 71202,
                "enrollment_state": "active",
                "limit_privileges_to_course_section": False,
            }
        ],
        "hide_final_grades": False,
        "workflow_state": "unpublished",
        "restrict_enrollments_to_course_dates": False,
    },
]

mock_modules = {
    37823: [
        {
            "id": 173467,
            "name": "Admin infomation",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
        {
            "id": 173574,
            "name": "Search",
            "position": 2,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": False,
            "items_count": 5,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173574/items",
        },
        {
            "id": 173468,
            "name": "Constraint Satisfaction Problems",
            "position": 3,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 2,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173468/items",
        },
        {
            "id": 173469,
            "name": "Sheduling and Adversarial Search",
            "position": 4,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": False,
            "items_count": 1,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173469/items",
        },
        {
            "id": 173579,
            "name": "Markov Decision Processes",
            "position": 5,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": False,
            "items_count": 1,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173579/items",
        },
        {
            "id": 173577,
            "name": "Reinforcement Learning",
            "position": 6,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 3,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173577/items",
        },
    ],
    37825: [
        {
            "id": 183467,
            "name": "Admin infomation",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
        {
            "id": 183468,
            "name": "Søk og problemløsning",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
        {
            "id": 183469,
            "name": "Sannsynlighetsregning",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
        {
            "id": 183470,
            "name": "Maskinlæring",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
        {
            "id": 183471,
            "name": "Nevrale nettverk",
            "position": 1,
            "unlock_at": None,
            "require_sequential_progress": False,
            "requirement_type": "all",
            "publish_final_grade": False,
            "prerequisite_module_ids": [],
            "published": True,
            "items_count": 0,
            "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173467/items",
        },
    ],
}

mock_items = {
    173574: [
        {
            "id": 1189103,
            "title": "2 Lecture - Search - INF-2600.pdf",
            "position": 7,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189103",
            "content_id": 3615155,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3615155",
            "published": True,
            "unpublishable": False,
        },
    ],
    173468: [
        {
            "id": 1189102,
            "title": "3 Lecture - Planning and CSP - INF-2600.pdf",
            "position": 6,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189102",
            "content_id": 3615154,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3615154",
            "published": True,
            "unpublishable": False,
        },
    ],
    173469: [
        {
            "id": 1189104,
            "title": "CSP",
            "position": 8,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189104",
            "page_url": "csp",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/csp",
            "published": True,
            "unpublishable": True,
        },
    ],
    173579: [
        {
            "id": 1189100,
            "title": "5 MDP - INF-2600.pdf",
            "position": 4,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189100",
            "content_id": 3615152,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3615152",
            "published": True,
            "unpublishable": False,
        },
        {
            "id": 1189105,
            "title": "Markov Decision Process",
            "position": 9,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189105",
            "page_url": "markov-decision-process",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/markov-decision-process",
            "published": True,
            "unpublishable": True,
        },
    ],
    173577: [
        {
            "id": 1189140,
            "title": "Reinforcement Learning",
            "position": 10,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189140",
            "page_url": "reinforcement-learning",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/reinforcement-learning",
            "published": True,
            "unpublishable": True,
        },
        {
            "id": 1189099,
            "title": "6 Reinforcement Learning - INF-2600.pdf",
            "position": 3,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 182386,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1189099",
            "content_id": 3615151,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3615151",
            "published": True,
            "unpublishable": False,
        },
    ],
    183468: [
        {
            "id": 1195254,
            "title": "Søk og problemløsing - Elements of AI.pdf",
            "position": 6,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195254",
            "content_id": 3639896,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639896",
            "published": True,
            "unpublishable": False,
        },
        {
            "id": 1195255,
            "title": "Søk og spill - Elements of AI.pdf",
            "position": 7,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195255",
            "content_id": 3639897,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639897",
            "published": True,
            "unpublishable": False,
        },
    ],
    183469: [
        {
            "id": 1195248,
            "title": "Naiv Bayes",
            "position": 1,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195248",
            "page_url": "naiv-bayes",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/naiv-bayes",
            "published": True,
            "unpublishable": True,
        },
        {
            "id": 1195251,
            "title": "Bayes teorem - Elements of AI.pdf",
            "position": 3,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195251",
            "content_id": 3639893,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639893",
            "published": True,
            "unpublishable": False,
        },
        {
            "id": 1195253,
            "title": "Odds og sannsynligheter - Elements of AI.pdf",
            "position": 5,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195253",
            "content_id": 3639895,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639895",
            "published": True,
            "unpublishable": False,
        },
    ],
    183470: [
        {
            "id": 1195249,
            "title": "Nærmeste nabo klassifisering",
            "position": 2,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195249",
            "page_url": "naermeste-nabo-klassifisering",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/naermeste-nabo-klassifisering",
            "published": True,
            "unpublishable": True,
        },
        {
            "id": 1195252,
            "title": "Forskjellige typer maskinlæring - Elements of AI.pdf",
            "position": 4,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195252",
            "content_id": 3639894,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639894",
            "published": True,
            "unpublishable": False,
        },
    ],
    183471: [
        {
            "id": 1195256,
            "title": "Hvordan bygge nevrale nettverk",
            "position": 8,
            "indent": 0,
            "quiz_lti": False,
            "type": "Page",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195256",
            "page_url": "hvordan-bygge-nevrale-nettverk",
            "publish_at": None,
            "url": "https://uit.instructure.com/api/v1/courses/37823/pages/hvordan-bygge-nevrale-nettverk",
            "published": True,
            "unpublishable": True,
        },
        {
            "id": 1195258,
            "title": "Prinsippene for nevrale nettverk - Elements of AI.pdf",
            "position": 9,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 183670,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1195258",
            "content_id": 3639898,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3639898",
            "published": True,
            "unpublishable": False,
        },
    ],
}

mock_pages = {
    "markov-decision-process": {
        "title": "Markov Decision Process",
        "created_at": "2025-06-26T09:41:10Z",
        "url": "markov-decision-process",
        "editing_roles": "teachers",
        "page_id": 424240,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/markov-decision-process",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-06-26T10:18:42Z",
        "locked_for_user": False,
        "body": markov_decision_process_body,
    },
    "csp": {
        "title": "CSP",
        "created_at": "2025-06-26T09:40:10Z",
        "url": "csp",
        "editing_roles": "teachers",
        "page_id": 424239,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/csp",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-06-26T09:40:39Z",
        "locked_for_user": False,
        "body": csp_body,
    },
    "reinforcement-learning": {
        "title": "Reinforcement Learning",
        "created_at": "2025-06-26T10:19:13Z",
        "url": "reinforcement-learning",
        "editing_roles": "teachers",
        "page_id": 424341,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/reinforcement-learning",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-06-26T10:19:37Z",
        "locked_for_user": False,
        "body": reinforcement_learning_body,
    },
    "naiv-bayes": {
        "title": "Naiv Bayes",
        "created_at": "2025-07-17T06:58:30Z",
        "url": "naiv-bayes",
        "editing_roles": "teachers",
        "page_id": 428214,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/naiv-bayes",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-07-17T06:58:47Z",
        "locked_for_user": False,
        "body": naiv_bayes_body,
    },
    "naermeste-nabo-klassifisering": {
        "title": "Nærmeste nabo klassifisering",
        "created_at": "2025-07-17T06:59:29Z",
        "url": "naermeste-nabo-klassifisering",
        "editing_roles": "teachers",
        "page_id": 428215,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/naermeste-nabo-klassifisering",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-07-17T06:59:42Z",
        "locked_for_user": False,
        "body": naermestenabo_body,
    },
    "hvordan-bygge-nevrale-nettverk": {
        "title": "Hvordan bygge nevrale nettverk",
        "created_at": "2025-07-17T07:04:33Z",
        "url": "hvordan-bygge-nevrale-nettverk",
        "editing_roles": "teachers",
        "page_id": 428217,
        "last_edited_by": {
            "id": 71202,
            "anonymous_id": "1ixu",
            "display_name": "Marius Rungmanee Solaas",
            "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
            "html_url": "https://uit.instructure.com/courses/37823/users/71202",
            "pronouns": None,
        },
        "published": True,
        "hide_from_students": False,
        "front_page": False,
        "html_url": "https://uit.instructure.com/courses/37823/pages/hvordan-bygge-nevrale-nettverk",
        "todo_date": None,
        "publish_at": None,
        "updated_at": "2025-07-17T07:04:45Z",
        "locked_for_user": False,
        "body": nevralenettverk_body,
    },
}

mock_files = {
    3639898: {
        "id": 3639898,
        "folder_id": 708060,
        "display_name": "Prinsippene for nevrale nettverk - Elements of AI.pdf",
        "filename": "Prinsippene+for+nevrale+nettverk+-+Elements+of+AI.pdf",
        "uuid": "Vzh7svEjilTXwa3bKsqJTE7YSJO5LajwYS85LWeU",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639898/download?download_frd=1&verifier=Vzh7svEjilTXwa3bKsqJTE7YSJO5LajwYS85LWeU",
        "size": 543717,
        "created_at": "2025-07-17T07:05:26Z",
        "updated_at": "2025-07-17T07:05:26Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:05:26Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639898,%22type%22:%22canvadoc%22%7D&hmac=92a304e7e92d04043ed2da5bf52036aad31bfe70",
        "crocodoc_session_url": None,
    },
    3639894: {
        "id": 3639894,
        "folder_id": 708060,
        "display_name": "Forskjellige typer maskinlæring - Elements of AI.pdf",
        "filename": "Forskjellige+typer+maskinl%C3%A6ring+-+Elements+of+AI.pdf",
        "uuid": "HTAQe9YRmsU69iLng0w2vCbpie0I9yUP8WgokGwc",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639894/download?download_frd=1&verifier=HTAQe9YRmsU69iLng0w2vCbpie0I9yUP8WgokGwc",
        "size": 628999,
        "created_at": "2025-07-17T07:00:15Z",
        "updated_at": "2025-07-17T07:00:15Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:00:15Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639894,%22type%22:%22canvadoc%22%7D&hmac=6413ca90a4867fabe4ac91fee2ad35fda968f175",
        "crocodoc_session_url": None,
    },
    3639895: {
        "id": 3639895,
        "folder_id": 708060,
        "display_name": "Odds og sannsynligheter - Elements of AI.pdf",
        "filename": "Odds+og+sannsynligheter+-+Elements+of+AI.pdf",
        "uuid": "3iVT4ynMHDuZyFIjZpQpNXYUdNdfD49v1HFfgaki",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639895/download?download_frd=1&verifier=3iVT4ynMHDuZyFIjZpQpNXYUdNdfD49v1HFfgaki",
        "size": 527535,
        "created_at": "2025-07-17T07:00:16Z",
        "updated_at": "2025-07-17T07:00:16Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:00:16Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639895,%22type%22:%22canvadoc%22%7D&hmac=d492800be1998a51f517743e9d83a7afa201ef12",
        "crocodoc_session_url": None,
    },
    3639893: {
        "id": 3639893,
        "folder_id": 708060,
        "display_name": "Bayes’ teorem - Elements of AI.pdf",
        "filename": "Bayes%E2%80%99+teorem+-+Elements+of+AI.pdf",
        "uuid": "SbOJf7xbad99WCARrXbc9elj8fd3mmzzlC5rHBmB",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639893/download?download_frd=1&verifier=SbOJf7xbad99WCARrXbc9elj8fd3mmzzlC5rHBmB",
        "size": 658092,
        "created_at": "2025-07-17T07:00:14Z",
        "updated_at": "2025-07-17T07:00:14Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:00:14Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639893,%22type%22:%22canvadoc%22%7D&hmac=376a156d40c7a61329d032dac26a0d2c8afd36cc",
        "crocodoc_session_url": None,
    },
    3639897: {
        "id": 3639897,
        "folder_id": 708060,
        "display_name": "Søk og spill - Elements of AI.pdf",
        "filename": "S%C3%B8k+og+spill+-+Elements+of+AI.pdf",
        "uuid": "1M3y7D5Z3YnGkItRAWAQcTUFQonDomHUrDhPCPCf",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639897/download?download_frd=1&verifier=1M3y7D5Z3YnGkItRAWAQcTUFQonDomHUrDhPCPCf",
        "size": 900745,
        "created_at": "2025-07-17T07:00:18Z",
        "updated_at": "2025-07-17T07:00:18Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:00:18Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639897,%22type%22:%22canvadoc%22%7D&hmac=6af0bacfbb717842db03a25553c97e44fa00fd90",
        "crocodoc_session_url": None,
    },
    3639896: {
        "id": 3639896,
        "folder_id": 708060,
        "display_name": "Søk og problemløsing - Elements of AI.pdf",
        "filename": "S%C3%B8k+og+probleml%C3%B8sing+-+Elements+of+AI.pdf",
        "uuid": "N7dINwwdMPjSY8WQECAqhL5NHKotJty8oFv0xAkJ",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3639896/download?download_frd=1&verifier=N7dINwwdMPjSY8WQECAqhL5NHKotJty8oFv0xAkJ",
        "size": 748822,
        "created_at": "2025-07-17T07:00:17Z",
        "updated_at": "2025-07-17T07:00:17Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-07-17T07:00:17Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3639896,%22type%22:%22canvadoc%22%7D&hmac=6ab86324fa9a2fcada08c576867afc488f3717dd",
        "crocodoc_session_url": None,
    },
    3615155: {
        "id": 3615155,
        "folder_id": 708060,
        "display_name": "2 Lecture - Search - INF-2600.pdf",
        "filename": "2+Lecture+-+Search+-+INF-2600.pdf",
        "uuid": "dEadZTvKyJqMIhhsw8af72M2Aj17rs8GkbWl8Vav",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3615155/download?download_frd=1&verifier=dEadZTvKyJqMIhhsw8af72M2Aj17rs8GkbWl8Vav",
        "size": 1102432,
        "created_at": "2025-06-26T09:39:37Z",
        "updated_at": "2025-06-26T09:39:37Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-26T09:39:37Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3615155,%22type%22:%22canvadoc%22%7D&hmac=4a270db294b97efa87552b8a068b99fac25c991e",
        "crocodoc_session_url": None,
    },
    3615154: {
        "id": 3615154,
        "folder_id": 708060,
        "display_name": "3 Lecture - Planning and CSP - INF-2600.pdf",
        "filename": "3+Lecture+-+Planning+and+CSP+-+INF-2600.pdf",
        "uuid": "FB9XRUbHRuM6EqroJYXnueoyOHmeMZe0jfbKriBK",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3615154/download?download_frd=1&verifier=FB9XRUbHRuM6EqroJYXnueoyOHmeMZe0jfbKriBK",
        "size": 1201660,
        "created_at": "2025-06-26T09:39:36Z",
        "updated_at": "2025-06-26T09:39:36Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-26T09:39:36Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3615154,%22type%22:%22canvadoc%22%7D&hmac=0e0d035f8a2b8fdbc3bc32c45fe2d7449aefe0e8",
        "crocodoc_session_url": None,
    },
    3615152: {
        "id": 3615152,
        "folder_id": 708060,
        "display_name": "5 MDP - INF-2600.pdf",
        "filename": "5+MDP+-+INF-2600.pdf",
        "uuid": "JqNRNiepvkDpEjU1WTvTE0mxdra70JDMOc0KqeWC",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3615152/download?download_frd=1&verifier=JqNRNiepvkDpEjU1WTvTE0mxdra70JDMOc0KqeWC",
        "size": 1429439,
        "created_at": "2025-06-26T09:39:34Z",
        "updated_at": "2025-06-26T09:39:34Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-26T09:39:34Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3615152,%22type%22:%22canvadoc%22%7D&hmac=a406e7436f6df2bd35df913f38c856a28fe0c669",
        "crocodoc_session_url": None,
    },
    3615151: {
        "id": 3615151,
        "folder_id": 708060,
        "display_name": "6 Reinforcement Learning - INF-2600.pdf",
        "filename": "6+Reinforcement+Learning+-+INF-2600.pdf",
        "uuid": "M2dfGnJiFvXvyOdosaDt06CRWkEbTxZkZOcjhrj5",
        "upload_status": "success",
        "content-type": "application/pdf",
        "url": "https://uit.instructure.com/files/3615151/download?download_frd=1&verifier=M2dfGnJiFvXvyOdosaDt06CRWkEbTxZkZOcjhrj5",
        "size": 2989874,
        "created_at": "2025-06-26T09:39:33Z",
        "updated_at": "2025-06-26T09:39:33Z",
        "unlock_at": None,
        "locked": False,
        "hidden": False,
        "lock_at": None,
        "hidden_for_user": False,
        "thumbnail_url": None,
        "modified_at": "2025-06-26T09:39:33Z",
        "mime_class": "pdf",
        "media_entry_id": None,
        "category": "uncategorized",
        "locked_for_user": False,
        "visibility_level": "inherit",
        "canvadoc_session_url": "/api/v1/canvadoc_session?blob=%7B%22user_id%22:107380000000071202,%22attachment_id%22:3615151,%22type%22:%22canvadoc%22%7D&hmac=4af7e1bcbae50a160d36cb89e344359ce5a332de",
        "crocodoc_session_url": None,
    },
}


# Store authorization codes and tokens
auth_codes = {}
access_tokens = {}
refresh_tokens = {}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: dict
    expires_in: Optional[int] = 3600


@app.get("/")
async def root():
    return {"message": "Mock Canvas LMS Server", "version": "1.0.0"}


# OAuth2 Authorization endpoint
@app.get("/login/oauth2/auth")
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    """Mock Canvas authorization endpoint"""

    # Validate basic OAuth2 parameters
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid response_type")

    # Return a simple HTML page that simulates Canvas login
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mock Canvas - Authorize Application</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            .button {{ background: #008EE2; color: white; padding: 10px 20px; border: None; border-radius: 4px; cursor: pointer; text-decoration: None; display: inline-block; }}
            .button:hover {{ background: #0078c7; }}
            .deny-button {{ background: #d93025; color: white; padding: 10px 20px; border: None; border-radius: 4px; cursor: pointer; text-decoration: None; display: inline-block; margin-left: 10px; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mock Canvas LMS</h1>
            <h2>Authorize Application</h2>

            <div class="info">
                <strong>Application Details:</strong><br>
                Client ID: {client_id}<br>
                Redirect URI: {redirect_uri}<br>
                Requested Scope: {scope or 'default'}<br>
                State: {state or 'None'}
            </div>

            <p>This application is requesting access to your Canvas account.</p>
            <p><strong>Mock User:</strong> Marius Solaas (mso270@uit.com)</p>

            <div>
                <a href="/login/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope or ''}&state={state or ''}&action=authorize" class="button">Authorize</a>
                <a href="/login/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type={response_type}&scope={scope or ''}&state={state or ''}&action=deny" class="deny-button">Deny</a>
            </div>

            <p><small>This is a mock Canvas server for development purposes.</small></p>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# OAuth2 Authorization action handler
@app.get("/login/oauth2/authorize")
async def handle_authorization(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    action: str = Query(...),
    state: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    """Handle the authorization decision (approve/deny)"""

    if action == "deny":
        # User denied authorization
        error_url = f"{redirect_uri}?error=access_denied&error_description=The+user+denied+the+request"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url)

    elif action == "authorize":
        # User approved authorization - generate auth code and redirect
        auth_code = f"mock_auth_code_{uuid.uuid4().hex[:16]}"

        # Store the auth code with associated data
        auth_codes[auth_code] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "user_id": "12345",  # Mock user ID
            "expires_at": datetime.now() + timedelta(minutes=10),
        }

        # Create the redirect URL with auth code
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"

        return RedirectResponse(url=redirect_url)

    else:
        raise HTTPException(status_code=400, detail="Invalid action")


# OAuth2 Token endpoint
@app.post("/login/oauth2/token")
async def get_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(None),
    code: str = Form(None),
    refresh_token: str = Form(None),
):
    """Mock Canvas token exchange endpoint"""

    print(
        f"Token exchange request: grant_type={grant_type}, client_id={client_id}, code={code}, refresh_token={refresh_token}"
    )

    if grant_type == "authorization_code":
        # Original authorization code flow
        if not code or not redirect_uri:
            raise HTTPException(status_code=400, detail="Missing code or redirect_uri")

        # Validate authorization code
        if code not in auth_codes:
            print(f"Available auth codes: {list(auth_codes.keys())}")
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        auth_data = auth_codes[code]

        # Check if code is expired
        if datetime.now() > auth_data["expires_at"]:
            raise HTTPException(status_code=400, detail="Authorization code expired")

        # Validate client_id matches
        if auth_data["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="Invalid client_id")

        # Generate access token and refresh token
        access_token = f"mock_access_token_{uuid.uuid4().hex}"
        new_refresh_token = f"mock_refresh_token_{uuid.uuid4().hex}"
        user_id = auth_data["user_id"]

        # Store access token
        access_tokens[access_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": datetime.now() + timedelta(hours=1),
            "refresh_token": new_refresh_token,
        }

        # Store refresh token
        refresh_tokens[new_refresh_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": auth_data["scope"],
            "expires_at": datetime.now()
            + timedelta(days=30),  # Refresh tokens last longer
        }

        # Clean up authorization code
        del auth_codes[code]

        print(f"Generated access token: {access_token}")
        print(f"Generated refresh token: {new_refresh_token}")

        return TokenResponse(
            access_token=access_token,
            user=mock_users[user_id],
            refresh_token=new_refresh_token,
            expires_in=3600,
        )

    elif grant_type == "refresh_token":
        # Refresh token flow
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Missing refresh_token")

        # Validate refresh token
        if refresh_token not in refresh_tokens:
            print(f"Available refresh tokens: {list(refresh_tokens.keys())}")
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        refresh_data = refresh_tokens[refresh_token]

        # Check if refresh token is expired
        if datetime.now() > refresh_data["expires_at"]:
            raise HTTPException(status_code=400, detail="Refresh token expired")

        # Validate client_id matches
        if refresh_data["client_id"] != client_id:
            raise HTTPException(status_code=400, detail="Invalid client_id")

        # Generate new access token and refresh token
        new_access_token = f"mock_access_token_{uuid.uuid4().hex}"
        new_refresh_token = f"mock_refresh_token_{uuid.uuid4().hex}"
        user_id = refresh_data["user_id"]

        # Store new access token
        access_tokens[new_access_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": datetime.now() + timedelta(hours=1),
            "refresh_token": new_refresh_token,
        }

        # Store new refresh token
        refresh_tokens[new_refresh_token] = {
            "user_id": user_id,
            "client_id": client_id,
            "scope": refresh_data["scope"],
            "expires_at": datetime.now() + timedelta(days=30),
        }

        # Clean up old refresh token
        del refresh_tokens[refresh_token]

        print(f"Refreshed access token: {new_access_token}")
        print(f"Generated new refresh token: {new_refresh_token}")

        return TokenResponse(
            access_token=new_access_token,
            user=mock_users[user_id],
            refresh_token=new_refresh_token,
            expires_in=3600,
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid grant_type")


# OAuth2 Token revocation endpoint
@app.delete("/login/oauth2/token")
async def revoke_token(
    authorization: str = Header(None),
    access_token: str = Form(None),
):
    """Mock Canvas token revocation endpoint"""

    token_to_revoke = None

    # Check if token is provided in Authorization header
    if authorization and authorization.startswith("Bearer "):
        token_to_revoke = authorization.replace("Bearer ", "")
    # Check if token is provided as form parameter
    elif access_token:
        token_to_revoke = access_token
    else:
        raise HTTPException(
            status_code=400,
            detail="Access token required in Authorization header or as access_token parameter",
        )

    print(f"Token revocation request for token: {token_to_revoke}")

    # Validate that the token exists
    if token_to_revoke not in access_tokens:
        print(f"Available tokens: {list(access_tokens.keys())}")
        raise HTTPException(status_code=401, detail="Invalid access token")

    token_data = access_tokens[token_to_revoke]

    # Remove the access token
    del access_tokens[token_to_revoke]

    # Also revoke the associated refresh token if it exists
    refresh_token_to_remove = token_data.get("refresh_token")
    if refresh_token_to_remove and refresh_token_to_remove in refresh_tokens:
        del refresh_tokens[refresh_token_to_remove]
        print(f"Also revoked associated refresh token: {refresh_token_to_remove}")

    print(f"Successfully revoked access token: {token_to_revoke}")

    # Return 200 OK with empty response body (Canvas behavior)
    return {}


# Helper function to validate access token
def validate_token(authorization: str) -> str:
    print(f"Validating token: {authorization}")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    if token not in access_tokens:
        print(f"Available tokens: {list(access_tokens.keys())}")
        raise HTTPException(status_code=401, detail="Invalid access token")

    token_data = access_tokens[token]

    if datetime.now() > token_data["expires_at"]:
        raise HTTPException(status_code=401, detail="Access token expired")

    return token_data["user_id"]


@app.get("/api/v1/courses")
async def get_courses(authorization: str = Header(None)):
    """Mock Canvas courses endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Return mock courses for the authenticated user
    return mock_courses


@app.get("/api/v1/courses/{course_id}/modules")
async def get_course_modules(course_id: int, authorization: str = Header(None)):
    """Mock Canvas course modules endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    return mock_modules.get(course_id, [])


@app.get("/api/v1/courses/{course_id}/modules/{module_id}/items")
async def get_module_items(
    course_id: int, module_id: int, authorization: str = Header(None)
):
    """Mock Canvas module items endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return items for course ID 37823, otherwise return unauthorized
    if course_id != 37823 and course_id != 37825:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course module items"
        )

    # Return items for the specified module_id from the mock_items dictionary
    if module_id in mock_items:
        return mock_items[module_id]
    else:
        # If no items found for this module, return empty list (not an error)
        return []


@app.get("/api/v1/courses/{course_id}/pages/{page_url}")
async def get_page(course_id: int, page_url: str, authorization: str = Header(None)):
    """Mock Canvas page endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return pages for course ID 37823, otherwise return unauthorized
    if course_id != 37823 and course_id != 37825:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course pages"
        )

    # Return items for the specified module_id from the mock_items dictionary
    if page_url in mock_pages:
        return mock_pages[page_url]
    else:
        raise HTTPException(status_code=404, detail="Page not found")


@app.get("/api/v1/courses/{course_id}/files/{file_id}")
async def get_file(course_id: int, file_id: int, authorization: str = Header(None)):
    """Mock Canvas file endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return files for course ID 37823, otherwise return unauthorized
    if course_id != 37823 and course_id != 37825:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course files"
        )

    # Check if the requested file_id exists in mock_files
    if file_id in mock_files:
        return mock_files[file_id]
    else:
        raise HTTPException(status_code=404, detail="File not found")


@app.post("/api/quiz/v1/courses/{course_id}/quizzes")
async def create_quiz(
    course_id: int, authorization: str = Header(None), quiz_data: dict = Body(None)
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Validate course access
    if course_id != 37823 and course_id != 37825:
        raise HTTPException(status_code=403, detail="Unauthorized access to course")

    # Create quiz object
    new_quiz = {
        "id": str(len(mock_quizzes) + 10000),  # 5-digit int starting from 10000
        "course_id": course_id,
        "title": quiz_data.get("title", "Untitled Quiz"),
        "points_possible": quiz_data.get("points_possible", 0),
        "due_at": quiz_data.get("due_at"),
        "lock_at": quiz_data.get("lock_at"),
        "unlock_at": quiz_data.get("unlock_at"),
        "published": False,
        "quiz_type": "assignment",
        "quiz_settings": quiz_data.get(
            "quiz_settings",
            {
                "shuffle_questions": True,
                "shuffle_answers": True,
                "time_limit": None,
                "multiple_attempts": False,
                "scoring_policy": "keep_highest",
            },
        ),
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
    }

    # Store quiz
    mock_quizzes.append(new_quiz)

    return new_quiz


@app.post("/api/quiz/v1/courses/{course_id}/quizzes/{quiz_id}/items")
async def create_quiz_item(
    course_id: int,
    quiz_id: int,
    authorization: str = Header(None),
    item_data: dict = Body(None),
):
    """Create a quiz item in a quiz"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Validate course access
    if course_id != 37823 and course_id != 37825:
        raise HTTPException(status_code=403, detail="Unauthorized access to course")

    # Validate required fields
    if not item_data:
        raise HTTPException(status_code=400, detail="Item data is required")

    item = item_data.get("item", {})
    entry = item.get("entry", {})

    # Validate required fields
    if not item.get("entry_type"):
        raise HTTPException(status_code=400, detail="item[entry_type] is required")

    if not entry.get("item_body"):
        raise HTTPException(
            status_code=400, detail="item[entry][item_body] is required"
        )

    if not entry.get("interaction_type_slug"):
        raise HTTPException(
            status_code=400, detail="item[entry][interaction_type_slug] is required"
        )

    if not entry.get("interaction_data"):
        raise HTTPException(
            status_code=400, detail="item[entry][interaction_data] is required"
        )

    if not entry.get("scoring_data"):
        raise HTTPException(
            status_code=400, detail="item[entry][scoring_data] is required"
        )

    if not entry.get("scoring_algorithm"):
        raise HTTPException(
            status_code=400, detail="item[entry][scoring_algorithm] is required"
        )

    # Validate interaction_type_slug
    valid_interaction_types = [
        "multi-answer",
        "matching",
        "categorization",
        "file-upload",
        "formula",
        "ordering",
        "rich-fill-blank",
        "hot-spot",
        "choice",
        "numeric",
        "True-False",
        "essay",
    ]

    if entry.get("interaction_type_slug") not in valid_interaction_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid interaction_type_slug. Must be one of: {', '.join(valid_interaction_types)}",
        )

    # Validate calculator_type if provided
    if entry.get("calculator_type") and entry.get("calculator_type") not in [
        "none",
        "basic",
        "scientific",
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid calculator_type. Must be one of: none, basic, scientific",
        )

    # Validate points_possible if provided
    points_possible = item.get("points_possible")
    if points_possible is not None and points_possible <= 0:
        raise HTTPException(status_code=400, detail="points_possible must be positive")

    # Create the quiz item
    new_quiz_item = {
        "id": str(len(mock_quiz_items) + 20000),  # 5-digit int starting from 20000
        "quiz_id": quiz_id,
        "position": item.get("position", len(mock_quiz_items) + 1),
        "points_possible": points_possible or 1,
        "entry_type": item.get("entry_type"),
        "entry": {
            "title": entry.get("title", "Question"),
            "item_body": entry.get("item_body"),
            "calculator_type": entry.get("calculator_type", "none"),
            "feedback": entry.get("feedback", {}),
            "interaction_type_slug": entry.get("interaction_type_slug"),
            "interaction_data": entry.get("interaction_data"),
            "properties": entry.get("properties", {}),
            "scoring_data": entry.get("scoring_data"),
            "answer_feedback": entry.get("answer_feedback", {}),
            "scoring_algorithm": entry.get("scoring_algorithm"),
        },
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
    }

    # Store the quiz item
    mock_quiz_items.append(new_quiz_item)

    return new_quiz_item


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tokens": len(access_tokens),
        "pending_auth_codes": len(auth_codes),
    }


# Debug endpoint to see current state
@app.get("/debug")
async def debug_state():
    return {
        "auth_codes": list(auth_codes.keys()),
        "access_tokens": list(access_tokens.keys()),
        "refresh_tokens": list(refresh_tokens.keys()),
        "mock_users": list(mock_users.keys()),
        "mock_quiz_items": mock_quiz_items,
        "mock_quizzes": mock_quizzes,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)

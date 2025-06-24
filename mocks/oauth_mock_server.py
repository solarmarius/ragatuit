import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Form, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Canvas Server", version="1.0.0")

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
        "name": "AUT-2600 Ølbrygging",
        "account_id": 27925,
        "uuid": "hfv2nToY5ae1MbmNWTfNhTpzVbwq9ENcT00yTEiK",
        "start_at": None,
        "grading_standard_id": None,
        "is_public": False,
        "created_at": "2025-03-06T16:18:18Z",
        "course_code": "AUT-2600",
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
]

mock_modules = [
    {
        "id": 173467,
        "name": "Administrativ informasjon",
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
        "name": "Mesking og vørterbehandling",
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
        "name": "Humle og bitterhet, smak og aroma",
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
        "name": "Stivelse, enzymer, sukkertyper og fermenterbarhet",
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
        "name": "Gjær og pitching av gjær, oksygenering",
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
        "name": "Fermentering (de ulike fasene)",
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
    {
        "id": 173682,
        "name": "Vask og desinfisering",
        "position": 7,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 5,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173682/items",
    },
    {
        "id": 173685,
        "name": "Vann og vannbehandling",
        "position": 8,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 5,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173685/items",
    },
    {
        "id": 173688,
        "name": "Tapping og karbonisering",
        "position": 9,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 5,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173688/items",
    },
    {
        "id": 173690,
        "name": "Smak, lukt, farge, klarhet",
        "position": 10,
        "unlock_at": None,
        "require_sequential_progress": False,
        "requirement_type": "all",
        "publish_final_grade": False,
        "prerequisite_module_ids": [],
        "published": False,
        "items_count": 6,
        "items_url": "https://uit.instructure.com/api/v1/courses/37823/modules/173690/items",
    },
]

mock_items = [
    # Items for module 173690 (Smak, lukt, farge, klarhet)
    {
        "id": 1149209,
        "title": "Module_X: Introduksjon",
        "position": 1,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149209",
        "page_url": "module-x-introduksjon-4",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/module-x-introduksjon-4",
        "published": False,
        "unpublishable": True,
    },
    {
        "id": 1149210,
        "title": "X.X_Unit title 1",
        "position": 2,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149210",
        "page_url": "x-dot-x-unit-title-1-4",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/x-dot-x-unit-title-1-4",
        "published": False,
        "unpublishable": True,
    },
    {
        "id": 1149211,
        "title": "X.X_Unit title 2",
        "position": 3,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149211",
        "page_url": "x-dot-x-unit-title-2-4",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/x-dot-x-unit-title-2-4",
        "published": False,
        "unpublishable": True,
    },
    {
        "id": 1149212,
        "title": "X.X_Unit title 3",
        "position": 4,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149212",
        "page_url": "x-dot-x-unit-title-3-4",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/x-dot-x-unit-title-3-4",
        "published": False,
        "unpublishable": True,
    },
    {
        "id": 1149213,
        "title": "X.X_Quiz",
        "position": 5,
        "indent": 0,
        "quiz_lti": False,
        "type": "Quiz",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149213",
        "content_id": 28763,
        "url": "https://uit.instructure.com/api/v1/courses/37823/quizzes/28763",
        "published": False,
        "unpublishable": True,
    },
    {
        "id": 1180833,
        "title": "Testpage",
        "position": 6,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173690,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1180833",
        "page_url": "testpage",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/testpage",
        "published": False,
        "unpublishable": True,
    },
    # Items for module 173579 (Gjær og pitching av gjær, oksygenering)
    {
        "id": 1149300,
        "title": "Introduksjon til gjær",
        "position": 1,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173579,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149300",
        "page_url": "introduksjon-til-gjaer",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/introduksjon-til-gjaer",
        "published": True,
        "unpublishable": True,
    },
    {
        "id": 1149301,
        "title": "Pitching av gjær",
        "position": 2,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173579,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149301",
        "page_url": "pitching-av-gjaer",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/pitching-av-gjaer",
        "published": True,
        "unpublishable": True,
    },
    # Items for module 173574 (Mesking og vørterbehandling)
    {
        "id": 1149400,
        "title": "Mesking prosess",
        "position": 1,
        "indent": 0,
        "quiz_lti": False,
        "type": "Page",
        "module_id": 173574,
        "html_url": "https://uit.instructure.com/courses/37823/modules/items/1149400",
        "page_url": "mesking-prosess",
        "publish_at": None,
        "url": "https://uit.instructure.com/api/v1/courses/37823/pages/mesking-prosess",
        "published": True,
        "unpublishable": True,
    },
]

mock_page = {
    "title": "Testpage",
    "created_at": "2025-06-12T10:12:51Z",
    "url": "testpage",
    "editing_roles": "teachers",
    "page_id": 418595,
    "last_edited_by": {
        "id": 71202,
        "anonymous_id": "1ixu",
        "display_name": "Marius Rungmanee Solaas",
        "avatar_image_url": "https://uit.instructure.com/images/thumbnails/1711458/KP9GqxzKd0VQzE400AHhImiJtv8fzGV1cR5gfYW2",
        "html_url": "https://uit.instructure.com/courses/37823/users/71202",
        "pronouns": None,
    },
    "published": False,
    "hide_from_students": True,
    "front_page": False,
    "html_url": "https://uit.instructure.com/courses/37823/pages/testpage",
    "todo_date": None,
    "publish_at": None,
    "updated_at": "2025-06-12T10:13:19Z",
    "locked_for_user": False,
    "body": '<link rel="stylesheet" href="https://instructure-uploads-eu.s3.eu-west-1.amazonaws.com/account_107380000000000001/attachments/3563198/dp_colors_uit_blue.css"><p>The<span>&nbsp;</span><strong>North Pole</strong>, also known as the<span>&nbsp;</span><strong>Geographic North Pole</strong><span>&nbsp;</span>or<span>&nbsp;</span><strong>Terrestrial North Pole</strong>, is the point in the<span>&nbsp;</span><a title="Northern Hemisphere" href="https://en.wikipedia.org/wiki/Northern_Hemisphere">Northern Hemisphere</a><span>&nbsp;</span>where the<span>&nbsp;</span><a title="Earth\'s rotation" href="https://en.wikipedia.org/wiki/Earth%27s_rotation">Earth\'s axis of rotation</a><span>&nbsp;</span>meets its surface. It is called the<span>&nbsp;</span><strong>True North Pole</strong><span>&nbsp;</span>to distinguish from the<span>&nbsp;</span><a title="North magnetic pole" href="https://en.wikipedia.org/wiki/North_magnetic_pole">Magnetic North Pole</a>.</p>\n<p>The North Pole is by definition the northernmost point on the Earth, lying<span>&nbsp;</span><a class="mw-redirect" title="Antipode (geography)" href="https://en.wikipedia.org/wiki/Antipode_(geography)">antipodally</a><span>&nbsp;</span>to the<span>&nbsp;</span><a title="South Pole" href="https://en.wikipedia.org/wiki/South_Pole">South Pole</a>. It defines geodetic<span>&nbsp;</span><a title="Latitude" href="https://en.wikipedia.org/wiki/Latitude">latitude</a><span>&nbsp;</span>90° North, as well as the direction of<span>&nbsp;</span><a title="True north" href="https://en.wikipedia.org/wiki/True_north">True north</a>. At the North Pole all directions point south; all lines of<span>&nbsp;</span><a title="Longitude" href="https://en.wikipedia.org/wiki/Longitude">longitude</a><span>&nbsp;</span>converge there, so its longitude can be defined as any degree value. No time zone has been assigned to the North Pole, so any time can be used as the local time. Along tight latitude circles, counterclockwise is east and clockwise is west. The North Pole is at the center of the Northern Hemisphere. The nearest land is usually said to be<span>&nbsp;</span><a title="Kaffeklubben Island" href="https://en.wikipedia.org/wiki/Kaffeklubben_Island">Kaffeklubben Island</a>, off the northern coast of<span>&nbsp;</span><a title="Greenland" href="https://en.wikipedia.org/wiki/Greenland">Greenland</a><span>&nbsp;</span>about 700&nbsp;km (430&nbsp;mi) away, though some perhaps semi-permanent gravel banks lie slightly closer. The nearest permanently inhabited place is<span>&nbsp;</span><a title="Alert, Nunavut" href="https://en.wikipedia.org/wiki/Alert,_Nunavut">Alert</a><span>&nbsp;</span>on<span>&nbsp;</span><a title="Ellesmere Island" href="https://en.wikipedia.org/wiki/Ellesmere_Island">Ellesmere Island</a>, Canada, which is located 817&nbsp;km (508&nbsp;mi) from the Pole.</p>\n<p>While the South Pole lies on a continental<span>&nbsp;</span><a title="Antarctica" href="https://en.wikipedia.org/wiki/Antarctica">land mass</a>, the North Pole is located in the middle of the<span>&nbsp;</span><a title="Arctic Ocean" href="https://en.wikipedia.org/wiki/Arctic_Ocean">Arctic Ocean</a><span>&nbsp;</span>amid waters that are almost permanently covered with constantly shifting<span>&nbsp;</span><a title="Sea ice" href="https://en.wikipedia.org/wiki/Sea_ice">sea ice</a>. The sea depth at the North Pole has been measured at 4,261&nbsp;m (13,980&nbsp;ft) by the Russian<span>&nbsp;</span><a class="mw-redirect" title="MIR (submersible)" href="https://en.wikipedia.org/wiki/MIR_(submersible)">Mir submersible</a><span>&nbsp;</span>in<span>&nbsp;</span><a title="Arktika 2007" href="https://en.wikipedia.org/wiki/Arktika_2007">2007</a><sup id="cite_ref-1" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-1"><span class="cite-bracket">[</span>1<span class="cite-bracket">]</span></a></sup><span>&nbsp;</span>and at 4,087&nbsp;m (13,409&nbsp;ft) by<span>&nbsp;</span><a title="USS Nautilus (SSN-571)" href="https://en.wikipedia.org/wiki/USS_Nautilus_(SSN-571)">USS<span>&nbsp;</span><i>Nautilus</i></a><span>&nbsp;</span>in 1958.<sup id="cite_ref-2" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-2"><span class="cite-bracket">[</span>2<span class="cite-bracket">]</span></a></sup><sup id="cite_ref-3" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-3"><span class="cite-bracket">[</span>3<span class="cite-bracket">]</span></a></sup><span>&nbsp;</span>This makes it impractical to construct a permanent station at the North Pole (<a title="Amundsen–Scott South Pole Station" href="https://en.wikipedia.org/wiki/Amundsen%E2%80%93Scott_South_Pole_Station">unlike the South Pole</a>). However, the<span>&nbsp;</span><a title="Soviet Union" href="https://en.wikipedia.org/wiki/Soviet_Union">Soviet Union</a>, and later Russia, constructed a number of<span>&nbsp;</span><a title="Drifting ice station" href="https://en.wikipedia.org/wiki/Drifting_ice_station">manned drifting stations</a><span>&nbsp;</span>on a generally annual basis since 1937, some of which have passed over or very close to the Pole. Since 2002, a group of Russians have also annually established a private base,<span>&nbsp;</span><a title="Barneo" href="https://en.wikipedia.org/wiki/Barneo">Barneo</a>, close to the Pole. This operates for a few weeks during early spring. Studies in the 2000s predicted that the North Pole may become seasonally ice-free because of<span>&nbsp;</span><a title="Climate change in the Arctic" href="https://en.wikipedia.org/wiki/Climate_change_in_the_Arctic">Arctic ice shrinkage</a>, with timescales varying from 2016<sup id="cite_ref-4" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-4"><span class="cite-bracket">[</span>4<span class="cite-bracket">]</span></a></sup><sup id="cite_ref-5" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-5"><span class="cite-bracket">[</span>5<span class="cite-bracket">]</span></a></sup><span>&nbsp;</span>to the late 21st century or later.</p>\n<p>Attempts to reach the North Pole began in the late 19th century, with the record for "<a title="Farthest North" href="https://en.wikipedia.org/wiki/Farthest_North">Farthest North</a>" being surpassed on numerous occasions. The first undisputed expedition to reach the North Pole was that of the airship<span>&nbsp;</span><i><a title="Norge (airship)" href="https://en.wikipedia.org/wiki/Norge_(airship)">Norge</a></i>, which overflew the area in 1926 with 16 men on board, including expedition leader<span>&nbsp;</span><a title="Roald Amundsen" href="https://en.wikipedia.org/wiki/Roald_Amundsen">Roald Amundsen</a>. Three prior expeditions – led by<span>&nbsp;</span><a title="Frederick Cook" href="https://en.wikipedia.org/wiki/Frederick_Cook">Frederick Cook</a><span>&nbsp;</span>(1908, land),<span>&nbsp;</span><a title="Robert Peary" href="https://en.wikipedia.org/wiki/Robert_Peary">Robert Peary</a><span>&nbsp;</span>(1909, land) and<span>&nbsp;</span><a title="Richard E. Byrd" href="https://en.wikipedia.org/wiki/Richard_E._Byrd">Richard E. Byrd</a><span>&nbsp;</span>(1926, aerial) – were once also accepted as having reached the Pole. However, in each case later analysis of expedition data has cast doubt upon the accuracy of their claims.</p>\n<p>The first verified individuals to reach the North Pole on foot was in 1948 by a 24-man Soviet party, part of<span>&nbsp;</span><a title="Aleksandr Kuznetsov (explorer)" href="https://en.wikipedia.org/wiki/Aleksandr_Kuznetsov_(explorer)">Aleksandr Kuznetsov</a>\'s<span>&nbsp;</span><i>Sever-2</i><span>&nbsp;</span>expedition to the Arctic, who flew near to the Pole first before making the final trek to the Pole on foot. The first complete land expedition to reach the North Pole was in 1968 by<span>&nbsp;</span><a title="Ralph Plaisted" href="https://en.wikipedia.org/wiki/Ralph_Plaisted">Ralph Plaisted</a>, Walt Pederson, Gerry Pitzl and Jean-Luc Bombardier, using snowmobiles and with air support.<sup id="cite_ref-6" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-6"><span class="cite-bracket">[</span>6<span class="cite-bracket">]</span></a></sup></p>\n<div class="mw-heading mw-heading2">\n<h2 id="Precise_definition">Precise definition</h2>\n</div>\n<div class="hatnote navigation-not-searchable" role="note">See also:<span>&nbsp;</span><a title="Polar motion" href="https://en.wikipedia.org/wiki/Polar_motion">Polar motion</a></div>\n<p>The Earth\'s axis of rotation&nbsp;– and hence the position of the North Pole&nbsp;– was commonly believed to be fixed (relative to the surface of the Earth) until, in the 18th century, the mathematician<span>&nbsp;</span><a title="Leonhard Euler" href="https://en.wikipedia.org/wiki/Leonhard_Euler">Leonhard Euler</a><span>&nbsp;</span>predicted that the axis might "wobble" slightly. Around the beginning of the 20th century astronomers noticed a small apparent "variation of latitude", as determined for a fixed point on Earth from the observation of stars. Part of this variation could be attributed to a wandering of the Pole across the Earth\'s surface, by a range of a few metres. The wandering has several periodic components and an irregular component. The component with a period of about 435 days is identified with the eight-month wandering predicted by Euler and is now called the<span>&nbsp;</span><a title="Chandler wobble" href="https://en.wikipedia.org/wiki/Chandler_wobble">Chandler wobble</a><span>&nbsp;</span>after its discoverer. The exact point of intersection of the Earth\'s axis and the Earth\'s surface, at any given moment, is called the "instantaneous pole", but because of the "wobble" this cannot be used as a definition of a fixed North Pole (or South Pole) when metre-scale precision is required.</p>\n<p>It is desirable to tie the system of Earth coordinates (latitude, longitude, and elevations or<span>&nbsp;</span><a title="Orography" href="https://en.wikipedia.org/wiki/Orography">orography</a>) to fixed landforms. However, given<span>&nbsp;</span><a title="Plate tectonics" href="https://en.wikipedia.org/wiki/Plate_tectonics">plate tectonics</a><span>&nbsp;</span>and<span>&nbsp;</span><a title="Isostasy" href="https://en.wikipedia.org/wiki/Isostasy">isostasy</a>, there is no system in which all geographic features are fixed. Yet the<span>&nbsp;</span><a title="International Earth Rotation and Reference Systems Service" href="https://en.wikipedia.org/wiki/International_Earth_Rotation_and_Reference_Systems_Service">International Earth Rotation and Reference Systems Service</a><span>&nbsp;</span>and the<span>&nbsp;</span><a title="International Astronomical Union" href="https://en.wikipedia.org/wiki/International_Astronomical_Union">International Astronomical Union</a><span>&nbsp;</span>have defined a framework called the<span>&nbsp;</span><a class="mw-redirect" title="International Terrestrial Reference System" href="https://en.wikipedia.org/wiki/International_Terrestrial_Reference_System">International Terrestrial Reference System</a>.</p>\n<div class="mw-heading mw-heading2">\n<h2 id="Exploration">Exploration</h2>\n</div>\n<div class="hatnote navigation-not-searchable" role="note">See also:<span>&nbsp;</span><a title="Arctic exploration" href="https://en.wikipedia.org/wiki/Arctic_exploration">Arctic exploration</a>,<span>&nbsp;</span><a title="Farthest North" href="https://en.wikipedia.org/wiki/Farthest_North">Farthest North</a>,<span>&nbsp;</span><a title="List of Arctic expeditions" href="https://en.wikipedia.org/wiki/List_of_Arctic_expeditions">List of Arctic expeditions</a>, and<span>&nbsp;</span><a class="mw-redirect" title="List of firsts in the Geographic North Pole" href="https://en.wikipedia.org/wiki/List_of_firsts_in_the_Geographic_North_Pole">List of firsts in the Geographic North Pole</a></div>\n<div class="mw-heading mw-heading3">\n<h3 id="Pre-1900">Pre-1900</h3>\n</div>\n<figure><a class="mw-file-description" href="https://en.wikipedia.org/wiki/File:Mercator_north_pole_1595.jpg"><img class="mw-file-element" src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Mercator_north_pole_1595.jpg/330px-Mercator_north_pole_1595.jpg" width="300" height="283" data-file-width="1700" data-file-height="1606" loading="lazy"></a>\n<figcaption><a title="Gerardus Mercator" href="https://en.wikipedia.org/wiki/Gerardus_Mercator">Gerardus Mercator</a>\'s map of the North Pole from 1595</figcaption>\n</figure>\n<figure class="mw-default-size"><a class="mw-file-description" href="https://en.wikipedia.org/wiki/File:C.G._Zorgdragers_Bloeyende_opkomst_der_aloude_en_hedendaagsche_Groenlandsche_visschery_-_no-nb_digibok_2014010724007-V1.jpg"><img class="mw-file-element" src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/af/C.G._Zorgdragers_Bloeyende_opkomst_der_aloude_en_hedendaagsche_Groenlandsche_visschery_-_no-nb_digibok_2014010724007-V1.jpg/250px-C.G._Zorgdragers_Bloeyende_opkomst_der_aloude_en_hedendaagsche_Groenlandsche_visschery_-_no-nb_digibok_2014010724007-V1.jpg" width="250" height="187" data-file-width="3721" data-file-height="2779" loading="lazy"></a>\n<figcaption>C.G. Zorgdragers map of the North Pole from 1720</figcaption>\n</figure>\n<p>As early as the 16th century, many prominent people correctly believed that the North Pole was in a sea, which in the 19th century was called the<span>&nbsp;</span><a title="Polynya" href="https://en.wikipedia.org/wiki/Polynya">Polynya</a><span>&nbsp;</span>or<span>&nbsp;</span><a title="Open Polar Sea" href="https://en.wikipedia.org/wiki/Open_Polar_Sea">Open Polar Sea</a>.<sup id="cite_ref-7" class="reference"><a href="https://en.wikipedia.org/wiki/North_Pole#cite_note-7"><span class="cite-bracket">[</span>7<span class="cite-bracket">]</span></a></sup><span>&nbsp;</span>It was therefore hoped that passage could be found through ice floes at favorable times of the year. Several expeditions set out to find the way, generally with whaling ships, already commonly used in the cold northern latitudes.</p>\n<p>One of the earliest expeditions to set out with the explicit intention of reaching the North Pole was that of British naval officer<span>&nbsp;</span><a class="mw-redirect" title="William Parry (explorer)" href="https://en.wikipedia.org/wiki/William_Parry_(explorer)">William Edward Parry</a>, who in 1827 reached latitude 82°45′ North. In 1871, the<span>&nbsp;</span><a title="Polaris expedition" href="https://en.wikipedia.org/wiki/Polaris_expedition"><i>Polaris</i><span>&nbsp;</span>expedition</a>, a U.S. attempt on the Pole led by<span>&nbsp;</span><a title="Charles Francis Hall" href="https://en.wikipedia.org/wiki/Charles_Francis_Hall">Charles Francis Hall</a>, ended in disaster. Another British<span>&nbsp;</span><a title="Royal Navy" href="https://en.wikipedia.org/wiki/Royal_Navy">Royal Navy</a><span>&nbsp;</span>attempt to get to the pole, part of the<span>&nbsp;</span><a title="British Arctic Expedition" href="https://en.wikipedia.org/wiki/British_Arctic_Expedition">British Arctic Expedition</a>, by Commander<span>&nbsp;</span><a title="Albert Hastings Markham" href="https://en.wikipedia.org/wiki/Albert_Hastings_Markham">Albert H. Markham</a><span>&nbsp;</span>reached a then-record 83°20\'26" North in May 1876 before turning back. An 1879–1881 expedition commanded by<span>&nbsp;</span><a title="United States Navy" href="https://en.wikipedia.org/wiki/United_States_Navy">U.S. Navy</a><span>&nbsp;</span>officer<span>&nbsp;</span><a title="George W. De Long" href="https://en.wikipedia.org/wiki/George_W._De_Long">George W. De Long</a><span>&nbsp;</span>ended tragically when their ship, the<span>&nbsp;</span><a title="USS Jeannette (1878)" href="https://en.wikipedia.org/wiki/USS_Jeannette_(1878)">USS&nbsp;<i>Jeannette</i></a>, was crushed by ice. Over half the crew, including De&nbsp;Long, were lost.</p>\n<figure class="mw-default-size mw-halign-left"><a class="mw-file-description" href="https://en.wikipedia.org/wiki/File:Nansen-fram.jpg"><img class="mw-file-element" src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Nansen-fram.jpg/250px-Nansen-fram.jpg" width="250" height="164" data-file-width="415" data-file-height="273" loading="lazy"></a>\n<figcaption>Nansen\'s ship<span>&nbsp;</span><i>Fram</i><span>&nbsp;</span>in the Arctic ice</figcaption>\n</figure>\n<p>In April 1895, the Norwegian explorers<span>&nbsp;</span><a title="Fridtjof Nansen" href="https://en.wikipedia.org/wiki/Fridtjof_Nansen">Fridtjof Nansen</a><span>&nbsp;</span>and<span>&nbsp;</span><a title="Hjalmar Johansen" href="https://en.wikipedia.org/wiki/Hjalmar_Johansen">Hjalmar Johansen</a><span>&nbsp;</span>struck out for the Pole on skis after leaving Nansen\'s icebound ship<span>&nbsp;</span><i><a title="Fram (ship)" href="https://en.wikipedia.org/wiki/Fram_(ship)">Fram</a></i>. The pair reached latitude 86°14′ North before they abandoned the attempt and turned southwards, eventually reaching<span>&nbsp;</span><a title="Franz Josef Land" href="https://en.wikipedia.org/wiki/Franz_Josef_Land">Franz Josef Land</a>.</p>\n<p>In 1897, Swedish engineer<span>&nbsp;</span><a title="Salomon August Andrée" href="https://en.wikipedia.org/wiki/Salomon_August_Andr%C3%A9e">Salomon August Andrée</a><span>&nbsp;</span>and two companions tried to reach the North Pole in the hydrogen balloon<span>&nbsp;</span><i>Örnen</i><span>&nbsp;</span>("Eagle"), but came down 300&nbsp;km (190&nbsp;mi) north of<span>&nbsp;</span><a title="Kvitøya" href="https://en.wikipedia.org/wiki/Kvit%C3%B8ya">Kvitøya</a>, the northeasternmost part of the<span>&nbsp;</span><a title="Svalbard" href="https://en.wikipedia.org/wiki/Svalbard">Svalbard</a><span>&nbsp;</span>archipelago. They trekked to Kvitøya but died there three months after their crash. In 1930 the remains of<span>&nbsp;</span><a class="mw-redirect" title="S. A. Andrée\'s Arctic Balloon Expedition of 1897" href="https://en.wikipedia.org/wiki/S._A._Andr%C3%A9e%27s_Arctic_Balloon_Expedition_of_1897">this expedition</a><span>&nbsp;</span>were found by the Norwegian<span>&nbsp;</span><a title="Bratvaag Expedition" href="https://en.wikipedia.org/wiki/Bratvaag_Expedition">Bratvaag Expedition</a>.</p>\n<p>The Italian explorer<span>&nbsp;</span><a title="Prince Luigi Amedeo, Duke of the Abruzzi" href="https://en.wikipedia.org/wiki/Prince_Luigi_Amedeo,_Duke_of_the_Abruzzi">Luigi Amedeo, Duke of the Abruzzi</a><span>&nbsp;</span>and Captain<span>&nbsp;</span><a title="Umberto Cagni" href="https://en.wikipedia.org/wiki/Umberto_Cagni">Umberto Cagni</a><span>&nbsp;</span>of the<span>&nbsp;</span><a title="Regia Marina" href="https://en.wikipedia.org/wiki/Regia_Marina">Italian Royal Navy</a><span>&nbsp;</span>(<span title="Italian-language text"><i lang="it">Regia Marina</i></span>) sailed the converted whaler<span>&nbsp;</span><i><a class="mw-redirect" title="Jason (ship)" href="https://en.wikipedia.org/wiki/Jason_(ship)">Stella Polare</a></i><span>&nbsp;</span>("Pole Star") from Norway in 1899. On 11 March 1900, Cagni led a party over the ice and reached latitude 86° 34’ on 25 April, setting a new record by beating Nansen\'s result of 1895 by 35 to 40&nbsp;km (22 to 25&nbsp;mi). Cagni barely managed to return to the camp, remaining there until 23 June. On 16 August, the<span>&nbsp;</span><i>Stella Polare</i><span>&nbsp;</span>left<span>&nbsp;</span><a title="Rudolf Island" href="https://en.wikipedia.org/wiki/Rudolf_Island">Rudolf Island</a><span>&nbsp;</span>heading south and the expedition returned to Norway.</p><script src="https://instructure-uploads-eu.s3.eu-west-1.amazonaws.com/account_107380000000000001/attachments/3521935/dp_app.js"></script>',
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
            <p><strong>Mock User:</strong> John Teacher (john.teacher@example.com)</p>

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


# Canvas API endpoints - Fixed to use proper HTTP headers
@app.get("/api/v1/users/self/profile")
async def get_user_profile(authorization: str = Header(None)):
    """Mock Canvas user profile endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    user_id = validate_token(authorization)

    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")

    return mock_users[user_id]


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

    # Only return modules for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course modules"
        )

    return mock_modules


@app.get("/api/v1/courses/{course_id}/modules/{module_id}/items")
async def get_module_items(
    course_id: int, module_id: int, authorization: str = Header(None)
):
    """Mock Canvas module items endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return items for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course module items"
        )

    # Filter items by module_id - return items that belong to the requested module
    module_items = [item for item in mock_items if item.get("module_id") == module_id]

    # If no items found, return empty list (not an error)
    return module_items


@app.get("/api/v1/courses/{course_id}/pages/{page_url}")
async def get_page(course_id: int, page_url: str, authorization: str = Header(None)):
    """Mock Canvas page endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Only return pages for course ID 37823, otherwise return unauthorized
    if course_id != 37823:
        raise HTTPException(
            status_code=403, detail="Unauthorized access to course pages"
        )

    # For this mock, we'll return the mock_page regardless of the page_url
    # In a real implementation, you'd look up the specific page by URL
    return mock_page


@app.get("/api/v1/users/{user_id}/profile")
async def get_user_by_id(user_id: str, authorization: str = Header(None)):
    """Mock Canvas user by ID endpoint"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    if user_id not in mock_users:
        raise HTTPException(status_code=404, detail="User not found")

    return mock_users[user_id]


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
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)

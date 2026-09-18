# Copyright 2023 Arian Shariat <arian.shariat@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Holiday Highlighter",
    "summary": "Public holidays color changes in datepicker and in calendar.",
    "version": "17.0.1.0.0",
    "license": "LGPL-3",
    "category": "Human Resources/Time Off",
    "author": "Arian Shariat",
    "website": "https://github.com/Arianshh",
    "depends": ["calendar", "hr_holidays"],
    "images": ["static/description/header.jpeg"],
    "data": [
        "data/data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "holiday_calendar_datepicker/static/src/js/holiday_calendar_datepicker.js",
            "holiday_calendar_datepicker/static/src/css/style.css",
        ],
    },
    "installable": True,
    "application": True,
}

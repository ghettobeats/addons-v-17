/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

const HOLIDAY_CLASS = "o_public_holiday";
const CALENDAR_HOLIDAY_CLASS = "o_calendar_holiday";
const HOLIDAY_ROUTE = "/publicholiday_calendar_datepicker/get_holidays";

let holidayDates = new Set();
let holidayLoadPromise;

async function loadHolidayDates() {
    if (!holidayLoadPromise) {
        holidayLoadPromise = fetch(HOLIDAY_ROUTE, {
            credentials: "same-origin",
        })
            .then((response) => (response.ok ? response.json() : []))
            .then((holidays) => {
                holidayDates = new Set(
                    (holidays || [])
                        .map((holiday) => String(holiday.date || "").split(" ")[0])
                        .filter(Boolean)
                );
                return holidayDates;
            })
            .catch(() => holidayDates);
    }
    return holidayLoadPromise;
}

function getHolidayClass(date) {
    return date && holidayDates.has(date.toISODate()) ? HOLIDAY_CLASS : "";
}

function addHolidayClass(info) {
    const date = luxon.DateTime.fromJSDate(info.date).toISODate();
    if (holidayDates.has(date)) {
        info.el.classList.add(CALENDAR_HOLIDAY_CLASS);
    }
}

patch(DateTimePicker.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            await loadHolidayDates();
        });
    },
});

patch(DateTimePicker, {
    defaultProps: {
        ...DateTimePicker.defaultProps,
        dayCellClass: getHolidayClass,
    },
});

patch(CalendarCommonRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            await loadHolidayDates();
        });
    },

    onDayRender(info) {
        super.onDayRender(info);
        addHolidayClass(info);
    },
});

patch(CalendarYearRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(async () => {
            await loadHolidayDates();
        });
    },

    onDayRender(info) {
        super.onDayRender(info);
        addHolidayClass(info);
    },
});

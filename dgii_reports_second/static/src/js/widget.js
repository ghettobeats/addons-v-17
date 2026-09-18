odoo.define('dgii_report.dgii_report_widget', function (require) {
    "use strict";

    var fieldregistry = require('web.field_registry');
    var FieldChar = require('web.basic_fields').UrlWidget;

    var UrlDgiiReportsWidget = FieldChar.extend({
	_renderReadonly: function () {
            this.$el.text(this.attrs.text || this.value)
                .addClass('o_form_uri o_text_overflow')
                .attr('target', '_blank')
                .attr('href', "dgii_reports_second/"+this.value);
        },
    });

    fieldregistry.add('dgii_reports_url', UrlDgiiReportsWidget);

    return {
        UrlDgiiReportsWidget: UrlDgiiReportsWidget,
    };




});



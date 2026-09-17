/** @odoo-module **/
const { Component, hooks } = owl;
import { useService } from "@web/core/utils/hooks";

export class SysAdminPanel extends Component {
    constructor() {
        super(...arguments);
        this.subscription = useService("enterprise");
    }

    get adminMessage() {
        return this.subscription.sysadmin.message;
    }

    get showMessage() {
        if (!this.subscription.warning || !(this.subscription.sysadmin || {}).warning_type){
            return false;
        } else if ((this.subscription.sysadmin || {}).warning_type === 'user'){
            return true;
        } else if (this.subscription.warning === 'admin' && (this.subscription.sysadmin || {}).warning_type === 'admin'){
            return true;
        }
        return false;
    }
}

SysAdminPanel.template = "web_enterprise.SysAdminPanel";

#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

import json
import logging
import requests
import datetime
import time
import pytz
import os
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import subprocess
_logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))

try:
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoSuchElementException, WebDriverException
    from odoo import api, fields, models, modules, tools
    # from selenium.webdriver import DesiredCapabilities
    _silenium_lib_imported = True
except ImportError:
    _silenium_lib_imported = False
    _logger.info(
        "The `selenium` Python module is not available. "
        "Currency updater Automation will not work. "
        "Try `pip3 install selenium` to install it."
    )


driver = {}
wait={}
wait5={}
is_session_open = {}
options = {}
msg_sent = False


from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

CURRENCY_MAPPING = {
    'euro': 'EUR',
    'cdol': 'CAD',
    'doll': 'USD',
    'poun': 'GBP',
    'swis': 'CHF',
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_do_currency_interval_unit = fields.Selection([
        ('manually', 'Manually'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly')],
        default='daily', string='Currency Interval')
    l10n_do_currency_provider = fields.Selection([
        ('bpd', 'Banco Popular Dominicano'),
        ('bnr', 'Banco de Reservas'),
        ('bpr', 'Banco del Progreso'),
        ('bsc', 'Banco Santa Cruz'),
        ('bdi', 'Banco BDI'),
        ('bpm', 'Banco Promerica'),
        ('bvm', 'Banco Vimenca'),
        ('bcd', 'Banco Central Dominicano'),
    ], default='bpd', string='Bank')
    currency_base = fields.Selection([('buyrate', 'Buy rate'), ('sellrate', 'Sell rate')], default='sellrate')
    rate_offset = fields.Float('Offset', default=0)
    l10n_do_currency_next_execution_date = fields.Date(string="Following Execution Date")
    last_currency_sync_date = fields.Date(string="Last Sync Date", readonly=True)

    # def get_currency_rates(self, params, token):
    #     api_url = self.env['ir.config_parameter'].sudo().get_param('indexa.api.url')
    #
    #     try:
    #         response = requests.get(api_url, params, headers={'x-access-token': token})
    #     except requests.exceptions.ConnectionError as e:
    #         _logger.warning(_('API requests return the following error %s' % e))
    #         return {}
    #     return response.text

    def l10n_do_update_currency_rates(self):

        all_good = True
        res = True
        companies = self.env['res.company'].search([])
        for company in companies:
            if company.l10n_do_currency_provider:
                _logger.info("Browsing rates resource.")


                bank = company.l10n_do_currency_provider

                rates_dict = self.get_currency_do(bank)

                d = {}
                try:
                    d = rates_dict
                except TypeError:
                    _logger.warning(_('No serializable data from web response'))

                Rate = self.env['res.currency.rate']

                if 'data' in d:
                    for currency in d['data']:
                        if str(currency['name']).endswith(company.currency_base or 'x') and currency['rate']:
                            inverse_rate = 1 / (float(currency['rate']) + company.rate_offset)

                            currency_id = self.env.ref('base.' + CURRENCY_MAPPING[str(currency['name'])[:4]])
                            if currency_id and currency_id.active:
                                rate_id = Rate.search([('name', '=', fields.Date.today()),
                                                       ('currency_id', '=', currency_id.id),
                                                       ('company_id', '=', company.id)])
                                if rate_id:
                                    rate_id.write({'rate': inverse_rate})
                                else:
                                    Rate.create({'currency_id': currency_id.id,
                                                 'rate': inverse_rate,
                                                 'company_id': company.id})
                    company.last_currency_sync_date = fields.Date.today()
                else:
                    res = False
            else:
                res = False
            if not res:
                all_good = False
                _logger.warning(_('Unable to fetch new rates records from web'))
        return all_good

    @api.model
    def l10n_do_run_update_currency(self):

        records = self.env['res.company'].search([])
        if records:
            to_update = self.env['res.company']
            for record in records:
                if record.l10n_do_currency_interval_unit == 'daily':
                    next_update = relativedelta(days=+1)
                elif record.l10n_do_currency_interval_unit == 'weekly':
                    next_update = relativedelta(weeks=+1)
                elif record.l10n_do_currency_interval_unit == 'monthly':
                    next_update = relativedelta(months=+1)
                else:
                    record.l10n_do_currency_interval_unit = False
                    continue
                record.l10n_do_currency_next_execution_date = datetime.date.today() + next_update
                to_update += record
            to_update.l10n_do_update_currency_rates()


    def get_currency_do(self,bank):
        unique_user = 'currency_updater'
        global is_session_open
        global options
        global dir_path
        options[unique_user] = webdriver.ChromeOptions()
        options[unique_user].add_argument('--user-data-dir=' + '/tmp/.user_data_uid_' + str(unique_user))
        options[unique_user].add_argument('--headless')
        options[unique_user].add_argument('--no-sandbox')
        options[unique_user].add_argument('--window-size=1366,768')
        options[unique_user].add_argument('--enable-logging=stderr')
        options[unique_user].add_argument('--disable-gpu')
        # user_agent = '"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"'
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3312.0 Safari/537.36'
        options[unique_user].add_argument('user-agent='+user_agent)
        global driver
        global wait
        global wait5
        capabilities = webdriver.DesiredCapabilities.CHROME.copy()
        capabilities['acceptSslCerts'] = True
        capabilities['acceptInsecureCerts'] = True
        try:
            e_path = dir_path + '/chromedriver_79'
            chromium_version = subprocess.check_output(['chromium-browser', '--version'], stderr=subprocess.STDOUT)
            chromium_version = chromium_version and chromium_version.split()[1]
            if chromium_version.startswith(b'79.'):
                e_path = dir_path + '/chromedriver_79'
            elif chromium_version.startswith(b'84.'):
                e_path = dir_path + '/chromedriver_84'

        except (subprocess.CalledProcessError, Exception):
            e_path = dir_path + '/chromedriver_79'
            chrome_version = subprocess.check_output(['google-chrome', '--version'], stderr=subprocess.STDOUT)
            chrome_version = chrome_version and chrome_version.split()[2]
            if chrome_version.startswith(b'79.'):
                e_path = dir_path + '/chromedriver_79'
            elif chrome_version.startswith(b'84.'):
                e_path = dir_path + '/chromedriver_84'

        tz = pytz.timezone('America/Santo_Domingo')
        today = datetime.datetime.now(tz)

        if bank == 'bpd':

            driver[unique_user] = webdriver.Chrome(executable_path=e_path, options=options.get(unique_user),
                                                   desired_capabilities=capabilities)
            wait[unique_user] = WebDriverWait(driver.get(self.unique_user), 10)
            wait5[unique_user] = WebDriverWait(driver.get(self.unique_user), 5)
            driver.get(unique_user).get("https://www.popularenlinea.com/")
            is_session_open[self.unique_user] = True

            compra_usd = driver.get(unique_user).find_element_by_xpath('.//input[@id="compra_peso_dolar_desktop"]').get_attribute('value')
            venta_usd = driver.get(unique_user).find_element_by_xpath('.//input[@id="venta_peso_dolar_desktop"]').get_attribute('value')

            compra_eur = driver.get(unique_user).find_element_by_xpath('.//input[@id="compra_peso_euro_desktop"]').get_attribute('value')
            venta_eur = driver.get(unique_user).find_element_by_xpath('.//input[@id="venta_peso_euro_desktop"]').get_attribute('value')
            driver.get(unique_user).quit()

            dict = {
                    "status": "success",
                    "data": [
                        {
                            "bank": "bpd",
                            "rate": compra_usd,
                            "date": today,
                            "name": "dollarbuyrate"
                        },
                         {
                            "bank": "bpd",
                            "rate": venta_usd,
                            "date": today,
                            "name": "dollarsellrate"
                         },
                         {
                            "bank": "bpd",
                            "rate": compra_eur,
                            "date": today,
                            "name": "eurobuyrate"
                         },
                         {
                            "bank": "bpd",
                            "rate": venta_eur,
                            "date": today,
                            "name": "eurosellrate"
                         }

                        ]
                    }

        if bank == 'bcd':
            driver[unique_user] = webdriver.Chrome(executable_path=e_path, options=options.get(unique_user),
                                                   desired_capabilities=capabilities)
            wait[unique_user] = WebDriverWait(driver.get(self.unique_user), 10)
            wait5[unique_user] = WebDriverWait(driver.get(self.unique_user), 5)
            driver.get(unique_user).get("https://www.bancentral.gov.do/")
            is_session_open[self.unique_user] = True

            compra_usd = driver.get(unique_user).find_element_by_xpath(
                "//*[text()='Compra']/following-sibling::h5").get_attribute("innerText")
            venta_usd = driver.get(unique_user).find_element_by_xpath(
                "//*[text()='Venta']/following-sibling::h5").get_attribute("innerText")


            driver.get(unique_user).quit()

            dict = {
                "status": "success",
                "data": [
                    {
                        "bank": "bcd",
                        "rate": compra_usd,
                        "date": today,
                        "name": "dollarbuyrate"
                    },
                    {
                        "bank": "bcd",
                        "rate": venta_usd,
                        "date": today,
                        "name": "dollarsellrate"
                    },

                ]
            }


        return dict

    def _default_unique_user(self):
        return 'currency_updater' + '_' + 'user'

    unique_user = fields.Char(default=_default_unique_user)




    def _cron_kill_chromedriver(self):
        global driver
        for w in self.search([]):
            try:
                driver.get(w.unique_user).close()
                driver.get(w.unique_user).quit()
                driver[w.unique_user] = None
                is_session_open[w.unique_user] = None
            except Exception as e:
                pass
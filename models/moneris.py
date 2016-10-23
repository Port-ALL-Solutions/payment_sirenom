# -*- coding: utf-'8' "-*-"

import base64
try:
    import simplejson as json
except ImportError:
    import json
import logging
import urlparse
import werkzeug.urls
import urllib2
import openerp

from openerp.addons.payment.models.payment_acquirer import ValidationError
from openerp.addons.payment_moneris.controllers.main import MonerisController
from openerp.osv import osv, fields
from openerp.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
handler = logging.FileHandler('/var/log/odoo/drozdyuk.logger1.log', mode='a')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
_logger.addHandler(handler)


class AcquirerMoneris(osv.Model):
    _inherit = 'payment.acquirer'
    
    def _get_moneris_urls(self, cr, uid, environment, context=None):
        """ Moneris URLS """
        if environment == 'prod':
            return {
                'moneris_form_url': 'https://www3.moneris.com/HPPDP/index.php',
                'moneris_auth_url': 'https://www3.moneris.com/HPPDP/verifyTxn.php',
            }
        else:
            return {
                'moneris_form_url': 'https://esqa.moneris.com/HPPDP/index.php',
                'moneris_auth_url': 'https://esqa.moneris.com/HPPDP/verifyTxn.php',
            }

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerMoneris, self)._get_providers(cr, uid, context=context)
        providers.append(['moneris', 'Moneris'])
        return providers

    _columns = {
        'moneris_email_account': fields.char('Moneris ps_store_id', required_if_provider='moneris'),
        'moneris_seller_account': fields.char(
            'Moneris hpp_key',
            help='The Merchant ID is used to ensure communications coming from Moneris are valid and secured.'),
        'moneris_use_ipn': fields.boolean('Use IPN', help='Moneris Instant Payment Notification'),
    }

    _defaults = {
        'moneris_use_ipn': True,
        'fees_active': False,
        'fees_dom_fixed': 0.35,
        'fees_dom_var': 3.4,
        'fees_int_fixed': 0.35,
        'fees_int_var': 3.9,
        'moneris_api_enabled': False,
    }

    def moneris_compute_fees(self, cr, uid, id, amount, currency_id, country_id, context=None):
        """ Compute moneris fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        acquirer = self.browse(cr, uid, id, context=context)
        if not acquirer.fees_active:
            return 0.0
        country = self.pool['res.country'].browse(cr, uid, country_id, context=context)
        if country and acquirer.company_id.country_id.id == country.id:
            percentage = acquirer.fees_dom_var
            fixed = acquirer.fees_dom_fixed
        else:
            percentage = acquirer.fees_int_var
            fixed = acquirer.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed ) / (1 - percentage / 100.0)
        return fees

    def moneris_form_generate_values(self, cr, uid, id, partner_values, tx_values, context=None):
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        acquirer = self.browse(cr, uid, id, context=context)

        moneris_tx_values = dict(tx_values)
        moneris_tx_values.update({
            'cmd': '_xclick',
            'business': acquirer.moneris_email_account,
            'item_name': tx_values['reference'],
            'item_number': tx_values['reference'],
            'amount': tx_values['amount'],
            'currency_code': tx_values['currency'] and tx_values['currency'].name or '',
            'address1': partner_values['address'],
            'city': partner_values['city'],
            'country': partner_values['country'] and partner_values['country'].name or '',
            'state': partner_values['state'] and partner_values['state'].name or '',
            'email': partner_values['email'],
            'zip': partner_values['zip'],
            'first_name': partner_values['first_name'],
            'last_name': partner_values['last_name'],
            'return': '%s' % urlparse.urljoin(base_url, MonerisController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, MonerisController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, MonerisController._cancel_url),
        })
        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', tx_values['reference'])], context=context)
        for tx in tx_ids:
            tx = self.pool['payment.transaction'].browse(cr, uid, tx, context=context)
            tx.write({'amount': tx_values['amount']})
                    
        if acquirer.fees_active:
            moneris_tx_values['handling'] = '%.2f' % moneris_tx_values.pop('fees', 0.0)
        if moneris_tx_values.get('return_url'):
            moneris_tx_values['custom'] = json.dumps({'return_url': '%s' % moneris_tx_values.pop('return_url')})
        return partner_values, moneris_tx_values

    def moneris_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self.browse(cr, uid, id, context=context)
        return self._get_moneris_urls(cr, uid, acquirer.environment, context=context)['moneris_form_url']


class TxMoneris(osv.Model):
    _inherit = 'payment.transaction'

    _columns = {
        'moneris_txn_id': fields.char('Transaction ID'),
        'moneris_txn_type': fields.char('Transaction type'),
        'moneris_txn_oid': fields.char('Order ID'),
        'moneris_txn_response': fields.char('Response Code'),
        'moneris_txn_ISO': fields.char('ISO'),
        'moneris_txn_eci': fields.char('Electronic Commerce Indicator'),
        'moneris_txn_card': fields.char('Card Type'),
        'moneris_txn_cardf4l4': fields.char('First 4 Last 4'),
        'moneris_txn_bankid': fields.char('Bank Transaction ID'),
        'moneris_txn_bankapp': fields.char('Bank Approval Code'),
    }

    def _moneris_form_get_tx_from_data(self, cr, uid, data, context=None):
        reference, txn_id = data.get('rvaroid'), data.get('txn_num')
        if not reference or not txn_id:
            error_msg = 'Moneris: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.pool['payment.transaction'].search(cr, uid, [('reference', '=', reference)], context=context)
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Moneris: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(cr, uid, tx_ids[0], context=context)

    def _moneris_form_get_invalid_parameters(self, cr, uid, tx, data, context=None):
        invalid_parameters = []

        if tx.moneris_txn_id and data.get('txn_num') != tx.moneris_txn_id:
            invalid_parameters.append(('txn_num', data.get('txn_num'), tx.moneris_txn_id))
        if tx.acquirer_reference and data.get('response_order_id') != tx.acquirer_reference:
            invalid_parameters.append(('response_order_id', data.get('response_order_id'), tx.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('charge_total', '0.0')), (tx.amount), 2) != 0:
            invalid_parameters.append(('charge_total', data.get('charge_total'), '%.2f' % tx.amount))

        return invalid_parameters

    def _moneris_form_validate(self, cr, uid, tx, data, context=None):
        status = data.get('result')
        data = {
            'moneris_txn_id': data.get('txn_num'),
            'moneris_txn_type': data.get('trans_name'),
            'moneris_txn_oid': data.get('response_order_id'),
            'moneris_txn_response': data.get('response_code'),
            'moneris_txn_ISO': data.get('iso_code'),
            'moneris_txn_eci': data.get('eci'),
            'moneris_txn_card': data.get('card'),
            'moneris_txn_cardf4l4': data.get('f4l4'),
            'moneris_txn_bankid': data.get('bank_transaction_id'),
            'moneris_txn_bankapp': data.get('bank_approval_code'),
            'partner_reference': data.get('cardholder'),
            'acquirer_reference': data.get('response_order_id')
        }
        if status == '1':
            _logger.info('Validated Moneris paymentssssss for tx %s: set as done' % (tx.reference))
            data.update(state='done', date_validate=data.get('date_stamp', fields.datetime.now()))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for Moneris payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)
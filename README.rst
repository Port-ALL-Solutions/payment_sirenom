# payment_moneris
Module Odoo 8.0 pour le paiement via Moneris
## Instruction

* Go to https://esqa.moneris.com/mpg/admin/hppv3_config/index.php (only for
environment test) and Generate new hpp_key

* Response Method: Sent to your server as a POST

Approval URL: https://sitename/payment/moneris/dpn

Declined URL: https://sitename/payment/moneris/cancel

Use "Enhanced Cancel" Enabled

Use "Response Fallback" Disabled

* Under Configure Response/Receipt Data:

Return ECI value: Enabled

Return the txn_number. This field is used to perform follow-ons: Enabled

* Under security features,

Enable Transaction Verification: Enabled

Displayed as key/value pairs on our server: Enabled

* Install the module payment_moneris

* Go to Settings --> Payment Acquirers --> Moneris

* Configure

Payment method(This journal is used to auto pay invoice when online payment is 
received): create new or select existing journal Visible in Portal/Website: 
Enabled

Environment: Test or Production

Process Method: Automatic

Moneris ps_store_id: ********

Moneris hpp_key: ********

Use IPN: Enabled
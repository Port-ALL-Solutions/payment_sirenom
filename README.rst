1.
Go to
https://esqa.moneris.com/mpg/admin/hppv3_config/index.php
only for environment test

Generate new hpp_key

2.
Response Method: Sent to your server as a POST

Approval URL: https://sitename/payment/moneris/dpn
Declined URL: https://sitename/payment/moneris/cancel

Use "Enhanced Cancel" Enabled
Use "Response Fallback" Disabled

3.
Under Configure Response/Receipt Data:
Return ECI value: Enabled
Return the txn_number. This field is used to perform follow-ons: Enabled

4.
Under security features,
Enable Transaction Verification: Enabled
Displayed as key/value pairs on our server: Enabled


5.
Install the module payment_moneris

6.
Go to
Settings --> Payment Acquirers --> Moneris

7.
Configure
Payment method(This journal is used to auto pay invoice when online payment is received): create new or select existing journal
Visible in Portal/Website: Enabled
Environment: Test or Production
Process Method: Automatic
Moneris ps_store_id: ********
Moneris hpp_key: ********
Use IPN: Enabled



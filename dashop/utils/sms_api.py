"""
短信接口
"""
from ronglian_sms_sdk import SmsSDK
from dashop.settings import (
    SMS_ACCOUNT_SID,
    SMS_TOKEN,
    SMS_APP_ID,
)

accId = SMS_ACCOUNT_SID
accToken = SMS_TOKEN
appId = SMS_APP_ID


def send_sms(tid, mobile, datas):
    sdk = SmsSDK(accId, accToken, appId)
    resp = sdk.sendMessage(tid, mobile, datas)
    return resp

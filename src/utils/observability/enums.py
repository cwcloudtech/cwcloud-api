from enum import Enum

Action = Enum('Action', [
    'ALL',
    'BYURL',
    'BYNAME',
    'BYUSER',
    'BYEMAIL',
    'DOWNLOAD',
    'SYNC',
    'REPLY',
    'REFRESH',
    'REGISTER',
    'VERIFY',
    'USER',
    'OWNER',
    'INVOKER',
    'INSTANCE',
    'REGION',
    'TYPE',
    'PRICING',
    'TECH',
    'FUNC',
    'MOVE',
    'CONFIG',
    'IMPORT',
    'EXPORT',
    'ATTACH',
    'AUTOPAY',
    'AUTOCLOSE',
    'BILLABLE',
    'PAYMETHOD',
    'RESOURCE',
    'REQUESTCONFIRM',
    'MFA',
    'CONFIRM',
    'GRANT',
    'FORGOT',
    'PASSWORD',
    'RESET',
    'EDIT',
    'STAT',
    'INFO',
    'TEMPLATE',
    'SVC',
    'GENSVC',
    'CM',
    'INGRESS',
    'INGRESSCLASS',
    'NS',
    'SECRET',
    'LOGS',
    'POD',
    'ASYNCWORKER',
    'UNKNOWN'
])

Method = Enum('Method', [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH',
    'ASYNCWORKER',
    'UNKNOWN'
])

def is_unknown(enum: Enum):
    return "unknown" == enum.name.lower()

def is_not_unknown(enum: Enum):
    return not is_unknown(enum)

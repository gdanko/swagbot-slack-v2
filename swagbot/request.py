from urllib.parse import urlencode
import inspect
import json
import logging
import os
import re
import requests
import swagbot.logger as logger
import swagbot.utils.core as utils

def get(client, uri=None, qs={}, payload={}, proxy=None, extra_headers={}, debug=False):
    __swagbot_request(client, http_method='GET', uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers, debug=debug)

def post(client, uri=None, qs={}, payload={}, proxy=None, extra_headers={}, debug=False):
    __swagbot_request(client, http_method='POST', uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers, debug=debug)

def put(client, uri=None, qs={}, payload={}, proxy=None, extra_headers={}, debug=False):
   __swagbot_request(client, http_method='PUT', uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers, debug=debug)

def delete(client, uri=None, qs={}, payload={}, proxy=None, extra_headers={}, debug=False):
    __swagbot_request(client, http_method='DELETE', uri=uri, qs=qs, payload=payload, proxy=proxy, extra_headers=extra_headers, debug=debug)

def __get_method(stack):
    valid_scripts = ['auth.py', 'core.py']
    usable_bits = [frame for frame in stack if os.path.basename(frame[1]) in valid_scripts]
    return usable_bits[-1][3] if len(usable_bits) > 0 else 'unknown method'

def __swagbot_request(client, http_method=None, uri=None, qs={}, payload={}, proxy=None, extra_headers={}, debug=False):
    logger.configure(debug=debug)
    method = __get_method(inspect.stack())
    url = None
    req = None
    res = None
    body = None
    json_body = None
    logging.debug('Executing method: {0}'.format(method))
    headers = {}

    headers['Content-Type'] = 'application/json'
    if extra_headers:
        for k, v in extra_headers.items():
            headers[k] = v

    logging.debug('{0} {1}'.format(http_method, url))
    if payload:
        if not 'api_signature' in payload:
            logging.debug('payload: {0}'.format(payload))

    if payload:
        res = requests.request(http_method, uri, proxies=proxy, headers=headers, params=qs, data=json.dumps(payload), verify=True)
    else:
        res = requests.request(http_method, uri, proxies=proxy, headers=headers, params=qs, verify=True)

    body = res.text
    if len(body) <= 0:
        body = ''

    if res.headers.get('content-length'):
        content_length = int(res.headers.get('content-length'))
    else:
        content_length = len(body) if len(body) > 0 else 0

    try:
        if isinstance(body, str):
            json_body = utils.validate_json(body)
        elif isinstance(body, bytes):
            json_body = utils.validate_json(body.decode('utf-8'))
    except:
        json_body = None

    status_code = res.status_code
    content_type = res.headers.get('content-type')
    client.response = {}

    if content_length > 0:
        if 'application/json' in content_type:
            if isinstance(json_body, dict):
                client.response = json_body
            elif isinstance(json_body, list):
                client.response = {'body': json_body}
        elif 'text/html' in content_type:
            client.success = False
            client.response = {'body': body}
    client.response['status_code'] = status_code

    if (status_code >= 200) and (status_code < 400):
        client.response['success'] = True
        if content_length <= 0:
            client.response['body'] = 'The method {0} completed successfully'.format(method)
    else:
        client.response['success'] = False
        if content_length <= 0:
            client.response['body'] = 'The method {0} completed unsuccessfully'.format(method)

    client.success = client.response['success']

import json, csv
import requests
import datetime
import logging
import pitschi.config as config

logger = logging.getLogger('pitschixapi')

def get_ppms_user(login):
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getuser&login={login}&format=json"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            raise Exception('Not found')
        else:
            # logger.debug(f"Response: {response}")
            return response.json(strict=False)
    else:
        raise Exception('Not found')


def get_ppms_user_by_id(uid:int, coreid:int):
    logger.debug(f'@get_ppms_user_by_id: get user by id: {uid}')
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    payload=f"outformat=json&apikey={config.get('ppms', 'api2_key')}&action=GetUserDetailsById&checkUserId={uid}&coreid={coreid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_ppms_users():
    logger.debug("@get_ppms_users: get all ppms users")
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    payload=f"outformat=json&apikey={config.get('ppms', 'api2_key')}&action=Report1335"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_daily_bookings_one_system(coreid: int, systemid: int, date: datetime.date):
    logger.debug("@get_daily_bookings_one_system: get bookings for given date")
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    datestr = f"{date.strftime('%Y-%m-%d')}"
    payload=f"apikey={config.get('ppms', 'api2_key')}&action=GetSessionsList&filter=day&systemid={systemid}&date={datestr}&coreid={coreid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_daily_bookings_by_coreid(coreid:int, date: datetime.date):
    logger.debug("@get_daily_bookings: get bookings for given date")
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    datestr = f"{date.strftime('%Y-%m-%d')}"
    payload=f"dateformat=print&outformat=json&apikey={config.get('ppms', 'api2_key')}&action={config.get('ppms', 'booking_query')}&startdate={datestr}&enddate={datestr}&coreid={coreid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_daily_bookings(date: datetime.date):
    sessions = []
    for coreid in json.loads(config.get('ppms', 'coreids')):
        for session in get_daily_bookings_by_coreid(coreid, date):
            session['coreid'] = coreid
            sessions.append(session)
    return sessions


def get_booking_details(coreid:int , sessionid: int):
    logger.debug(f'get booking id {sessionid} details')
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    payload=f"apikey={config.get('ppms', 'api2_key')}&action=GetSessionDetails&sessionid={sessionid}&coreid={coreid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_daily_training_by_coreid(coreid:int, date: datetime.date):
    logger.debug("@get_daily_training: get training for given date")
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    datestr = f"{date.strftime('%Y-%m-%d')}"
    payload=f"dateformat=print&outformat=json&apikey={config.get('ppms', 'api2_key')}&action={config.get('ppms', 'training_query')}&startdate={datestr}&enddate={datestr}&coreid={coreid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    return []


def get_daily_training(date: datetime.date):
    sessions = []
    for coreid in json.loads(config.get('ppms', 'coreids')):
        for session in get_daily_training_by_coreid(coreid, date):
            session['coreid'] = coreid
            sessions.append(session)
    return sessions


def get_system_pids():
    logger.debug(f'get all system pids')
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    payload=f"outformat=json&apikey={config.get('ppms', 'api2_key')}&action=Report2168"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code != 204:
            pids = response.json(strict=False)
            if type(pids) == list and len(pids) > 0:
                return pids
    logger.warning(f'response status_code={response.status_code}, text="{response.text}"')
    return []


def get_systems():
    logger.debug("get all systems")
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getsystems"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code != 204:
            # format is in csv
            _systems_text = response.text
            _csv_reader = csv.reader(_systems_text.split('\n'), delimiter=',')
            _csv_reader.__next__()
            systems = []
            for row in _csv_reader:
                if(len(row) > 3):
                    _coreid = int(row[0])
                    _systemid = int(row[1])
                    _systemtype = row[2]
                    _systemname = row[3]
                    systems.append({'coreid': _coreid, 'systemid': _systemid, 'systemtype': _systemtype, 'systemname': _systemname})
            return systems
    logger.warning(f'response status_code={response.status_code}, text="{response.text}"')
    return []


def get_system_rights(systemid: int):
    logger.debug("get systems")
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getsysrights&id={systemid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return {}
        else:
            # format is in mode:name\n
            _system_rights_text = response.text.strip()
            _lines = _system_rights_text.split('\n')
            _permissions = { _line.split(":")[1]:_line.split(":")[0] for _line in _lines }
            return _permissions
    return {}


def get_projects():
    logger.debug("get all projects")
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getprojects&active=true&format=json"
    # payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getprojects&format=json"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            return response.json(strict=False)
    else:
        return []


def get_project_user(projectid: int):
    logger.debug(f'get project id {projectid} users')
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getprojectusers&withdeactivated=false&projectid={projectid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            response_txt = response.text
            return response_txt.strip().split("\n")
    else:
        return []

def get_project_members(projectid: int):
    """
    Similar to project_user but with user id as well
    """
    logger.debug(f'get project id {projectid} members')
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getprojectmember&projectid={projectid}"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return []
        else:
            response_txt = response.text
            _csv_reader = csv.reader(response_txt.split('\n'), delimiter=',')
            _csv_reader.__next__()
            members = []
            for row in _csv_reader:
                if (len(row) > 8):
                    _userid = int(row[1])
                    _userlogin = row[8]
                    if _userid > 0 and _userlogin:
                        members.append({'id': _userid, 'login': _userlogin})
            return members
    else:
        return []

def get_rdm_collection(coreid: int, projectid: int):
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    payload=f"apikey={config.get('ppms', 'api2_key')}&action={config.get('ppms', 'qcollection_action')}&projectId={projectid}&coreid={coreid}&outformat=json"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return ""
        qcollection = ""
        if len(response.json()) > 0:
            qcollection = response.json(strict=False)[0].get(config.get('ppms', 'q_collection_field'))
        return qcollection
    return ""

def get_rdm_collections(coreid: int = None):
    logger.debug("@get_rdm_collections: get all rdm collections")
    url = f"{config.get('ppms', 'ppms_url')}API2/"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded' }
    action = config.get('ppms', 'qcollections_action')
    rdm_key = config.get('ppms', 'q_collection_field')
    rdms = []
    if coreid is None:
        coreids = json.loads(config.get('ppms', 'coreids'))
    else:
        coreids = [coreid]
    for coreid in coreids:
        payload = f"apikey={config.get('ppms', 'api2_key')}&action={action}&coreid={coreid}&outformat=json"
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.ok:
            if response.status_code == 204:
                break
            if len(response.json()) > 0:
                rdms.extend([{ 'coreid': r['PlateformID'], 'projectid': r['ProjectRef'], 'rdm': r[rdm_key] } for r in response.json()])
    return rdms

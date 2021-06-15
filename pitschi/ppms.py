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
            return response.json(strict=False)
    else:
        raise Exception('Not found')


def get_daily_bookings_one_system(coreid: int, systemid: int, date: datetime.date):
    logger.debug("Querying booking of a certain date")
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

def get_daily_bookings(coreid:int , date: datetime.date):
    logger.debug("Querying booking of a certain date")
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


def get_systems():
    logger.debug("Querying systems")
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getsystems"
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    if response.ok:
        if response.status_code == 204:
            return {}
        else:
            # format is in csv
            _systems_text = response.text
            _csv_reader = csv.reader(_systems_text.split('\n'), delimiter=',')
            _csv_reader.__next__()
            systems = {}
            for row in _csv_reader:
                if(len(row) > 3):
                    _systemid = int(row[1])
                    _systemtype = row[2]
                    _systemname = row[3]
                    systems[_systemname] = {'systemid': _systemid, 'systemtype': _systemtype, 'systemname': _systemname}
            return systems
    return {}

def get_projects():
    logger.debug("Querying projects")
    url = f"{config.get('ppms', 'ppms_url')}pumapi/"
    payload=f"apikey={config.get('ppms', 'ppms_key')}&action=getprojects&active=true&format=json"
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
    logger.debug("Querying project user")
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
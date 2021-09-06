import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
import os
##################
# This is very similar to pyclowder
# But without any rabbitmq
##################### space ###########################

def update_space_user_roles(key, api_url, space_id, roles_users_json):
    """
    TODO: roles_uses_json --> get this from LDAP
    curl -X POST "https://xxxx/api/spaces/5f3f3812e4b099e94537da99/updateUsers" 
        -H "accept: */*" -H  "Authorization: Basic xxxx=" 
        -H "Content-Type: application/json" 
        -d "{\"rolesandusers\":{\"Viewer\":\"5f3df518d3e25fe7bf35532e\",\"Admin\":\"5f17cd947fb639fd1895038e\"}}"
    """
    url = f"{api_url}/spaces/{space_id}"
    data = {
        "rolesandusers": roles_users_json
    }
    return _post(url, key, data=json.dumps(data))

def extract_roles_users():
    """
    Extract users roles from a certain collection
    Needs to access to LDAP
    """
    pass

def list_spaces(key, api_url, canedit=True):
    """
    list spaces, be careful of limit
    """
    url = f"{api_url}/spaces"
    if canedit:
        url = f"{url}/canEdit"
    return _get(url, key)

def get_spaces(key, api_url, name, canedit=True):
    """
    get spaces with given name
    """
    url = f"{api_url}/spaces"
    if canedit:
        url = f"{url}/canEdit"
    else:
        url = f"{url}?name={name}&limit=100"
    return _get(url, key)

##################### dataset ###########################


def list_dataset_in_space(key, api_url, space_id):
    """
    """
    url = f"{api_url}/spaces/{space_id}/datasets"
    return _get(url, key)


def add_dataset_creators(key, api_url, dataset_id, creator):
    """
    curl -X POST "https://xxxx/api/datasets/5f3f38e2e4b099e94537da9c/creator" 
    -H  "accept: */*" -H  "Authorization: Basic xxxx=" 
    -H  "Content-Type: application/json" -d "{\"creator\":\"Hoang Nguyen\"}"

    """
    url = f"{api_url}/datasets/{dataset_id}/creator"
    data = {
        'creator': creator
    }
    return _post(url, key, data=json.dumps(data))
    
def add_dataset_to_space(key, api_url, space_id, dataset_id):
    """
    curl -X POST "https://xxxx/api/spaces/5f3f3812e4b099e94537da99/addDatasetToSpace/5f3f38e2e4b099e94537da9c" 
    -H  "accept: */*" -H  "Authorization: Basic xxxx="

    """
    url = f"{api_url}/spaces/{space_id}/addDatasetToSpace/{dataset_id}"
    return _post(url, key, content_type=None)

##################### folder ###########################
def list_dataset_folders(key, dataset_id, api_url):
    """
    curl -X GET "https://xxxx/api/datasets/5f2b84f8e4b0b16dc6351be4/folders" 
    -H  "accept: */*" -H  "X-API-Key: 4268f72d-0633-4677-9ecc-487ba071531b"

    Returns
    [{
        "id": "5f45b0a0e4b08350bdff1936",
        "name": "/test1"
        },
        {
            "id": "5f45b0a6e4b08350bdff1938",
            "name": "/test1/test2"
    }]
    """
    url = f"{api_url}/datasets/{dataset_id}/folders"
    return _get(url, key)



def delete_folder(key, api_url, dataset_id, folder_id):
    """
    Delete an existing folder
    """
    url = f"{api_url}/datasets/{dataset_id}/deleteFolder/{folder_id}"
    return _delete(url, key)

def update_folder_name(key, api_url, dataset_id, folder_id, new_folder_name):
    """
    Update folder name
    """
    url = f"{api_url}/datasets/{dataset_id}/updateName/{folder_id}"
    data = {
        "name": new_folder_name
    }
    return _put(url, key, data=json.dumps(data))

##################### files ###########################

def get_file_list(key, api_url, dataset_id):
    """
    Get list of files in a dataset as JSON object.
    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    datasetid -- the dataset to get filelist of
    """
    url = f"{api_url}/datasets/{dataset_id}/files"
    print (url)
    return _get(url, key)

def move_existing_file_to_folder(key, api_url, dataset_id, folder_id, file_id):
    url = f"{api_url}/datasets/{dataset_id}/moveFile/{folder_id}/{file_id}"
    res = _post(url, key, data=json.dumps({}))
    if res.ok:
        return res.json()
    else:
        res.raise_for_status()

def add_server_file(key, api_url, dataset_id, file_path, parent_folderid=None, extract=True, check_duplicate=True):
    """
    Add files already in server side
    curl -X POST "https://xxxx/api/uploadToDataset/5f3f38e2e4b099e94537da9c?extract=true" 
    -H  "accept: */*" 
    -H  "X-API-Key: 4268f72d-0633-4677-9ecc-487ba071531b" 
    -H  "Content-Type: multipart/form-data" 
    -F "file={\"path\":\"/home/globus/39. Hitachi TM4000 Plus/TM4000/B_1.tif\", \"dataset\":\"5f3f3812e4b099e94537da99\"}"
    """
    if check_duplicate:
        ds_files = get_file_list(key, api_url, dataset_id)
        if ds_files.ok:
            for f in ds_files.json():
                if f['filename'] == os.path.basename(file_path):
                    return {'id': f['id']}
    url = f"{api_url}/uploadToDataset/{dataset_id}?extract={'true' if extract else 'false'}"
    data = {
        'path': file_path,
        'dataset': dataset_id
    }
    m = MultipartEncoder({
        'file': json.dumps(data)
    })
    # return _post(url, key, data=m, content_type='multipart/form-data')
    res = _post(url, key, data=m, content_type=m.content_type)
    if res.ok:
        # move file to folder
        res_json = res.json()
        if parent_folderid:
            move_existing_file_to_folder(key, api_url, dataset_id, parent_folderid, res_json['id'])
        return res_json
    else:
        res.raise_for_status()

def upload_client_file(key, api_url, dataset_id, file_path, parent_folderid=None, extract=True, check_duplicate=True):
    """
    Add files not in server side
    Upload flie to a dataset
    """
    if check_duplicate:
        ds_files = get_file_list(key, api_url, dataset_id)
        if ds_files.ok:
            for f in ds_files.json():
                if f['filename'] == os.path.basename(file_path):
                    return {'id': f['id']}
    url = f"{api_url}/uploadToDataset/{dataset_id}?extract={'true' if extract else 'false'}"
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        m = MultipartEncoder(
                fields={'File': (filename, open(file_path, 'rb')) }
            )
        res =  _post(url, key, data=m, content_type=m.content_type)
        if res.ok:
            res_json = res.json()
            if parent_folderid:
                move_existing_file_to_folder(key, api_url, dataset_id, parent_folderid, res_json['id'])
            return res_json
        else:
            res.raise_for_status()
    else:
        raise Exception(f"[@upload_client_file] {file_path} does not exists")

def _get_metadata(content, resource_type, resource_id, server=None):
    """Generate a metadata field.

    This will return a metadata dict that is valid JSON-LD. This will use the results as well as the information
    in extractor_info.json to create the metadata record.

    This does a simple check for validity, and prints to debug any issues it finds (i.e. a key in conent is not
    defined in the context).

    Args:
        content (dict): the data that is in the content
        resource_type (string); type of resource such as file, dataset, etc
        resource_id (string): id of the resource the metadata is associated with
        server (string): clowder url, used for extractor_id, if None it will use
                            https://clowder.ncsa.illinois.edu/extractors
    """
    context_url = 'https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld'
    extrator_name = '4ceed.hyperspy.dm3'
    extractor_version = '1.0'
    extractor_context =  [{}]
    return {
        # '@context': [context_url] + extractor_context,
        '@context': 'http://clowder.ncsa.illinois.edu/contexts/extractors.jsonld',
        'attachedTo': {
            'resourceType': resource_type,
            'id': resource_id
        },
        'agent': {
            '@type': 'cat:extractor',
            'extractor_id': '%sextractors/%s/%s' %
                            (server, extrator_name, extractor_version),
            'version': extrator_name,
            'name': extractor_version
        },
        'content': content
    }


def upload_metadata_jsonld(key, api_url, fileid, metadata):
    """Upload file JSON-LD metadata to Clowder.
    Copy from pyclowder
    Keyword arguments:
    connector -- connector information, used to get missing parameters and send status updates
    host -- the clowder host, including http and port, should end with a /
    key -- the secret key to login to clowder
    fileid -- the file that is currently being processed
    metadata -- the metadata to be uploaded
    --------> NOT WORKING
    """
    url = f"{api_url}/files/{fileid}/metadata.jsonld"
    return _post(url, key, json_data=_get_metadata(metadata, 'file', fileid))

def upload_metadata(key, api_url, fileid, metadata):
    """
    """
    url = f"{api_url}/files/{fileid}/metadata"
    res =  _post(url, key, data=json.dumps(metadata))
    if res.ok:
        return res.json()
    else:
        res.raise_for_status()


def submit_for_extraction(key, api_url, fileid, extractor_name):
    url = f"{api_url}/files/{fileid}/extractions"
    data = {
        "extractor": extractor_name        
    }
    res = _post(url, key, data=json.dumps(data))
    if res.ok:
        return res.json()
    else:
        res.raise_for_status()


### TODO: preview, thumnail, tags -- later look at pyclowder

###########3 high level functions ##############
def create_space(key, api_url, space_name, space_description, check_duplicate=True):
    """
    api_url = https://xxxx/api
    Add a space
    curl -X POST "https://xxxx/api/spaces" -H  "accept: */*" 
    -H  "X-API-Key: 4268f72d-0633-4677-9ecc-487ba071531b"  
    -H  "Content-Type: application/json" -d "{\"name\":\"TIFS\",\"description\":\"TIFS\"}"
    """
    if check_duplicate:
        res = list_spaces(key, api_url)
        if res.ok:
            for _space in res.json():
                if _space.get('name') == space_name:
                    return {'id': _space.get('id')}
    url = f"{api_url}/spaces"
    data = {
        'name': space_name,
        'description': space_description
    }
    res = _post(url, key, data=json.dumps(data))
    if res.ok:
        return res.json()
    else:
        res.raise_for_status()

def create_dataset(key, api_url, space_id, dataset_name, check_duplicate=True):
    """
    curl -X POST "https://xxxx/api/datasets/createempty" 
    -H  "accept: */*" -H  "Authorization: Basic xxxx=" 
    -H  "Content-Type: application/json" -d "{\"name\":\"test\"}"
    """
    if check_duplicate:
        res = list_dataset_in_space(key, api_url, space_id)
        if res.ok:
            for _dataset in res.json():
                if _dataset.get('name') == dataset_name:
                    return {'id': _dataset.get('id')}
    url = f"{api_url}/datasets/createempty"
    data = {
        'name': dataset_name
    }
    res = _post(url, key, data=json.dumps(data))
    if res.ok:
        res_json = res.json()
        res = add_dataset_to_space(key, api_url, space_id, res_json.get('id'))
        if res.ok:
            return res_json
    res.raise_for_status()


def find_folder(key, api_url, dataset_id, path_from_parent_dataset):
    url = f"{api_url}/datasets/{dataset_id}/folders"
    res = _get(url, key)
    if res.ok:
        for _folder in res.json():
            if _folder['name'] == path_from_parent_dataset:
                return _folder
        return None
    else:
        res.raise_for_status()

def get_dataset_folders(key, api_url, dataset_id):
    url = f"{api_url}/datasets/{dataset_id}/folders"
    res = _get(url, key)
    if res.ok:
        return res.json()
    res.raise_for_status()

def add_folder(key, api_url, dataset_id, folder_name, parent_folder_id=None, check_duplicate=True):
    """
    Add a folder
    """
    #TODO: check whether folder_name exists
    url = f"{api_url}/datasets/{dataset_id}/newFolder"
    if parent_folder_id:
        parent_id = parent_folder_id
        parent_type = 'folder'
    else:
        parent_id = dataset_id
        parent_type = 'dataset'
    data = {
        "name": folder_name,
        "parentId": parent_id,
        "parentType": parent_type
    }
    res = _post(url, key, data=json.dumps(data))
    if res.ok:
        return res.json()
    else:
        res.raise_for_status()
########################### miscs ########################################  
def _post(url, key, data=None, json_data = None, content_type='application/json'):
    """
    POST
    """
    #print (f"POST: {url} {data} {content_type}")
    return requests.post(url, headers=_request_header(key, content_type=content_type), json=json_data, data=data)


def _put(url, key, data=None, json_data = None, dump_json = True):
    """
    PUT
    """
    #print (f"PUT: {url}")
    return requests.put(url, headers=_request_header(key), json=json_data, data=data)
    
def _get(url, key):
    """
    GET
    """
    #print (f"GET: {url}")
    return requests.get(url, headers=_request_header(key))
    
def _delete(url, key):
    """
    DELETE
    """
    return requests.delete(url, headers=_request_header(key))
    
def _request_header(key, content_type='application/json'):
    if content_type:
        return {
            'accept': '*/*',
            'Content-Type': content_type,
            'X-API-Key': key
        }
    else:
        return {
            'accept': '*/*',
            'X-API-Key': key
        }


def main():
    key = 'e1b27840-4c06-4949-8864-ec59f49b46a8'
    api_url = 'https://xxxx/api'
    space_id = '606be5cf0cf223cdf333e009'

    result = list_dataset_in_space(key, api_url, space_id)
    print ("1. Results from get folders")
    print (result.json()) 
    

    
    # create a new dataset
    # result = create_dataset(key, api_url, space_id, 'python')
    # print ("1. Results fro mcreating dataset")
    # print (result) 
    
    # dataset_id = result.get('id')
    dataset_id = '5f45db4ae4b08350bdff1a4d'
    # result = add_dataset_to_space(key, api_url, space_id, '5f45d920e4b08350bdff1a39')
    # print (result.ok)
    # print (result.reason)
    # add dataset to space
    # add dataset to space
    # add_dataset_to_space(key, api_url, space_id, dataset_id)
    # test upload file already @ server

    # print ('Adding server file')
    # result = add_server_file(key, api_url, dataset_id, '/data/collections/Hawken/19. JSM 7100F/JSM7100_DemoData/SEM_Images/test_image02.jpg', check_duplicate=True)
    # if result.ok:
    #     print (result.json())
    # else:
    #     result.raise_for_status()
    # test upload file @ local

    # print ('Uploading local file')
    # result = upload_client_file(key, api_url, dataset_id, '/home/hoangnguyen177/Downloads/Hawken/36. SU 3500/Cu grid_SE_1a.tif', check_duplicate=True)
    # if result.ok:
    #     print (result.json())
    # else:
    #     print (result.reason)
    #     result.raise_for_status()
    # fileid = '5f48e9eae4b0835063c720c0'
    # metadata = utils.read_metadata('/data/collections/RDM1/42. Neoscope JCM-5000/Neoscope/Zfish CPD.000004.txt')
    # print (json.dumps(metadata))
    # result = upload_metadata(key, api_url, fileid, metadata)
    # print (result)

if __name__ == "__main__":
    main()


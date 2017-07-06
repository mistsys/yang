from __future__ import print_function

import argparse
import errno
import hashlib
import json
import os
import shutil
import subprocess
import unicodedata
import ConfigParser

import MySQLdb
import requests
from flask import Flask, jsonify, abort, make_response, request
from flask_httpauth import HTTPBasicAuth

import repoutil

#url = 'https://api.github.com/repos/'
url = 'https://github.com/'

auth = HTTPBasicAuth()
app = Flask(__name__)


def unicode_normalize(variable):
    return unicodedata.normalize('NFKD', variable).encode('ascii', 'ignore')


@app.errorhandler(404)
def not_found():
    return make_response(jsonify({'error': 'Not found'}), 404)


def authorize(request, response):
    username = request.authorization['username']
    accessRigths = None
    try:
        db = MySQLdb.connect(host=dbHost, db=dbName, user=dbUser, passwd=dbPass)
        # prepare a cursor object using cursor() method
        cursor = db.cursor()
        # execute SQL query using execute() method.
        cursor.execute("SELECT * FROM `users`")
        data = cursor.fetchall()

        for row in data:
            if row[1] == username:
                accessRigths = row[7]
                break;
        db.close()
    except MySQLdb.MySQLError as err:
        print("Cannot connect to database. MySQL error: " + str(err))

    rights = accessRigths.split('/')
    check_vendor = None
    check_platform = None
    check_software_version = None
    check_software_flavor = None
    if rights[1] is '':
        return 'passed'
    else:
        check_vendor = rights[1]
    if len(rights) > 2:
        check_platform = rights[2]
    if len(rights) > 3:
        check_software_version = rights[3]
    if len(rights) > 4:
        check_software_flavor = rights[4]

    for platform in response['platforms']:
        vendor = platform['vendor']
        platform_name = platform['name']
        software_version = platform['software-version']
        software_flavor = platform['software-flavor']

        if check_platform and platform_name != check_platform:
            return unauthorized()
        if check_software_version and software_version != check_software_version:
            return unauthorized()
        if check_software_flavor and software_flavor != check_software_flavor:
            return unauthorized()
        if vendor != check_vendor:
            return unauthorized()
    return 'passed'


@app.route('/checkComplete', methods=['POST'])
@auth.login_required
def check_local():
    body = request.json
    if body['repository']['owner_name'] == 'yang-catalog':
        if body['result_message'] == 'Passed':
            if body['type'] == 'push':
                # After build was successful only locally
                json_body = jsonify({
                    "title": "Crone job - every day pull of ietf draft yang files.",
                    "body": "ietf extracted yang modules",
                    "head": "yang-catalog:master",
                    "base": "master"
                })
                requests.post('https://api.github.com/repos/YangModels/yang/pulls', json=json_body,
                              headers={'Authorization': 'token ' + token})

            if body['type'] == 'pull_request':
                # If build was successful on pull request
                pull_number = body['pull_request_number']
                log.write('pull request was successful %s' % repr(pull_number))
                #requests.put('https://api.github.com/repos/YangModels/yang/pulls/' + pull_number +
                #             '/merge', headers={'Authorization': 'token ' + token})
                requests.delete('https://api.github.com/repos/yang-catalog/yang',
                                headers={'Authorization': 'token ' + token})


@app.route('/modules', methods=['PUT'])
@auth.login_required
def add_modules():
    if not request.json:
        abort(400)
    body = request.json
    #TODO authorization

    with open('./prepare-sdo.json', "w") as plat:
         json.dump(body, plat)

    repo = {}
    for mod in body['modules']['module']:
        sdo = mod['sdo-file']

        directory = '/'.join(sdo['path'].split('/')[:-1])

        repo_url = url + sdo['owner'] + '/' + sdo['repo']
        if repo_url not in repo:
            repo[repo_url] = repoutil.RepoUtil(repo_url)
            repo[repo_url].clone()

        for submodule in repo[repo_url].repo.submodules:
            submodule.update(init=True)

        save_to = 'temp/' + sdo['owner'] + '/' + sdo['repo'].split('.')[0] + '/' + directory
        try:
            os.makedirs(save_to)
        except OSError as e:
            # be happy if someone already created the path
            if e.errno != errno.EEXIST:
                raise
        shutil.copy(repo[repo_url].localdir + '/' + sdo['path'], save_to)

    #os.system('python populate.py --sdo --port ' + repr(confdPort) + ' --dir temp --api --ip ' + confd_ip + ' --credentials '
    #                + ' '.join(credentials))
    with open("log.txt", "wr") as f:
        try:
            arguments = ["python", "../parseAndPopulate/populate.py", "--sdo", "--port", repr(confdPort), "--dir",
                          "temp", "--api", "--ip", confd_ip, "--credentials", credentials[0], credentials[1]]
            subprocess.check_call(arguments, stderr=f)
            #df = subprocess.Popen(args, stdout=subprocess.PIPE)
            #output, err = df.communicate()
        except subprocess.CalledProcessError as e:
            shutil.rmtree('temp/')
            for key in repo:
                repo[key].remove()
            return jsonify({'error': 'Was not able to write all or partial yang files'})

    try:
        os.makedirs('../../api/sdo/')
    except OSError as e:
        # be happy if someone already created the path
        if e.errno != errno.EEXIST:
            raise
    subprocess.call(["cp", "-r", "temp/.", "../../api/sdo/"])

    shutil.rmtree('temp')
    for item in os.listdir('./'):
        if 'log' in item and '.txt' in item:
            os.remove(item)
    for key in repo:
        repo[key].remove()
    return jsonify({'info': 'success'})


@app.route('/platforms', methods=['PUT'])
@auth.login_required
def add_vendors():
    if not request.json:
        abort(400)
    body = request.json
    resolved_authorization = authorize(request, body)
    if 'passed' != resolved_authorization:
        return resolved_authorization

    repo = {}
    for platform in body['platforms']:
        capability = platform['capabilities-file']
        file_name = capability['path'].split('/')[-1]

        repo_url = url + capability['owner'] + '/' + capability['repo']
        if repo_url not in repo:
            repo[repo_url] = repoutil.RepoUtil(repo_url)
            repo[repo_url].clone()

        for submodule in repo[repo_url].repo.submodules:
            submodule.update(init=True)

        directory = '/'.join(capability['path'].split('/')[:-1])
        save_to = 'temp/' + capability['owner'] + '/' + capability['repo'].split('.')[0] + '/' + directory

        try:
            shutil.copytree(repo[repo_url].localdir + '/' + directory, save_to,
                            ignore=shutil.ignore_patterns('*.json', '*.xml', '*.sh', '*.md', '*.txt', '*.bin'))
        except OSError:
            pass
        with open(save_to + '/' + file_name.split('.')[0] + '.json', "w") as plat:
            json.dump(platform, plat)
        shutil.copy(repo[repo_url].localdir + '/' + capability['path'], save_to,)

    #os.system('python populate.py --port ' + repr(confdPort) + ' --dir temp --api --ip ' + confd_ip + ' --credentials '
    #          + ' '.join(credentials))
    with open("log.txt", "wr") as f:
        try:
            arguments = ["python", "../parseAndPopulate/populate.py", "--port", repr(confdPort), "--dir", "temp",
                         "--api", "--ip", confd_ip, "--credentials", credentials[0], credentials[1]]
            subprocess.check_call(arguments, stderr=f)
            #df = subprocess.Popen(args, stdout=subprocess.PIPE)
            #output, err = df.communicate()
        except subprocess.CalledProcessError as e:
            shutil.rmtree('temp/')
            for key in repo:
                repo[key].remove()
            return jsonify({'error': 'Was not able to write all or partial yang files'})
    try:
        os.makedirs('../../api/vendor/')
    except OSError as e:
        # be happy if someone already created the path
        if e.errno != errno.EEXIST:
            raise
    subprocess.call(["cp", "-r", "temp/.", "../../api/vendor/"])

    shutil.rmtree('temp/')
    for item in os.listdir('./'):
        if 'log' in item and '.txt' in item:
            os.remove(item)
    for key in repo:
        repo[key].remove()
    return jsonify({'info': 'success'})


@auth.hash_password
def hash_pw(password):
    return hashlib.sha256(password).hexdigest()

@auth.get_password
def get_password(username):
    #    if username in users:
    #        return users.get(username)
    #    return None
    try:
        db = MySQLdb.connect(host=dbHost, db=dbName, user=dbUser, passwd=dbPass)
        # prepare a cursor object using cursor() method
        cursor = db.cursor()

        # execute SQL query using execute() method.
        cursor.execute("SELECT * FROM `users`")

        data = cursor.fetchall()

        for row in data:
            if username in row[1]:
                return row[2]
        db.close()
        return None
    # print row

    except MySQLdb.MySQLError as err:
        print("Cannot connect to database. MySQL error: " + str(err))


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-path', type=str, default='./config.ini',
                        help='Set path to config file')
    args = parser.parse_args()
    config = ConfigParser.ConfigParser()
    config.read(args.config_path)
    global dbHost
    dbHost = config.get('SectionOne', 'dbIp')
    global dbName
    dbName = config.get('SectionOne', 'dbName')
    global dbUser
    dbUser = config.get('SectionOne', 'dbUser')
    global dbPass
    dbPass = config.get('SectionOne', 'dbPassword')
    global credentials
    credentials = config.get('SectionOne', 'credentials').split(' ')
    global confd_ip
    confd_ip = config.get('SectionOne', 'confd-ip')
    global confdPort
    confdPort = int(config.get('SectionOne', 'confd-port'))
    global token
    token = config.get('SectionOne', 'yang-catalog-token')
    ssl_context = None
    global log
    ip = config.get('SectionOne', 'ip')
    port = int(config.get('SectionOne', 'port'))
    debug = config.get('SectionOne', 'debug')
    key = config.get('SectionOne', 'ssl-key')
    cert = config.get('SectionOne', 'ssl-cert')
    log = open('api_log_file.txt', 'w')
    if cert:
        ssl_context = (cert, key)
    app.run(host=ip, debug=debug, port=port, ssl_context=ssl_context)
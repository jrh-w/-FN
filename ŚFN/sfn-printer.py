import hashlib
import requests
import time
import json
import os

from svg2gcode import convertToGcode
from printer_const import *
from conn_functions import *

printer_id = 0
logged_in = False

while logged_in == False:
    printer_name = input("Printer's name: ")
    printer_password = hashlib.sha256(input("Password: ").encode()).hexdigest()

    print('Connecting to the PostgreSQL database...')
    logged_in, printer_id = postgresConn(logIn, { 'name': printer_name, 'password': printer_password })

# Delete any files that are in printer memory (fresh start)
get_files = requests.get('http://{}/api/files'.format(ip_address), headers=headers)
files = json.loads(get_files.text)['files']

for file in files:
    requests.delete('http://{}/api/files/local/{}'.format(ip_address, file['name']), headers=headers)

# Connect with the printer
requests.post('http://{}/api/connection'.format(ip_address), headers=headers, json=connectCommand)

# Restore the unfinished jobs in DB
postgresConn(resetUnfinishedFiles)

printer_local = []
exit = False

while exit == False:
    printer_jobs = []
    addJob = False

    result, printer_jobs = postgresConn(getJobs, { 'id': printer_id })
    exit = result == False

    try:
        # Getting current job
        get_job = requests.get('http://{}/api/job'.format(ip_address), headers=headers)

        currentJob = json.loads(get_job.text)['job']
        progress = json.loads(get_job.text)['progress']

        if currentJob['file']['name'] == None:
            print('No jobs for printer at the moment')
            addJob = True
        else:
            print('Current job:', currentJob['file']['name'], progress['completion'])
            printer_local.append((currentJob['file']['name'], progress['completion'],
                'complete' if progress['completion'] == 100.0 else 'in_progress'))

        # Getting current saved files
        get_files = requests.get('http://{}/api/files'.format(ip_address), headers=headers)
        files = json.loads(get_files.text)['files']

        # Sieve current files in printer memory
        for file in files:
            if file['name'] == currentJob['file']['name'] and progress['completion'] == 100.0:
                # Delete the file from printer memory
                requests.delete('http://{}/api/files/local/{}'.format(ip_address, file['name']), headers=headers)
                printer_local.remove(printer_local[0])
            else:
                for job in printer_jobs:
                    if file['name'] == '{}_{}.gcode'.format(job[2], job[0]):
                        printer_local.append((file['name'], 0.0, 'in_queue'))
                        printer_jobs.remove(job)

        # Add new jobs to the list
        for job in printer_jobs:
            paths = job[3].split(';')
            result = convertToGcode(paths)
            print(result)

            # Generate .gcode file and send it to the printer
            filename = "{}_{}.gcode".format(job[2], job[0])
            gcodeFile = open(filename, "w")
            gcodeFile.write(result)
            gcodeFile.close()

            binData = open(filename,'rb')

            files=[
                ('file',(filename, binData, 'application/octet-stream'))
            ]
            requests.post('http://{}/api/files/local'.format(ip_address), headers=headers, files=files)
            printer_local.append((filename, 0.0, 'in_queue'))

            binData.close()
            os.remove(filename)

        # Add a job to printer, if there is none
        if addJob and len(printer_local) > 0 and printer_local[0][2] != 'complete':
            addJob = False
            printFile = printer_local[0][0]
            printer_local[0] = (printer_local[0][0], printer_local[0][1], 'in_progress')
            print("Printing", printer_local[0], printFile)
            requests.post('http://{}/api/files/local/{}'.format(ip_address, printFile), headers=printHeaders, json=printCommand)
    except requests.exceptions.RequestException as e:
        print("Error:", error)
    else:
        # Send update to DB
        postgresConn(updateJobs, { 'localData': printer_local })

    time.sleep(0.5)

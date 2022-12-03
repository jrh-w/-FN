import psycopg2
import hashlib
import requests
import time
import json
import math
import re
import os

# TODO: Refactor, %s --> convert(), split files

from svg2gcode import convertToGcode

printer_name = input("Printer's name: ")
printer_password = hashlib.sha256(input("Password: ").encode()).hexdigest()
printer_id = 0

try:
    print('Connecting to the PostgreSQL database...')
    conn = psycopg2.connect(
        host="containers-us-west-120.railway.app",
        dbname="railway",
        user="postgres",
        password="f6yK2thZe5OJmvQnzw1T",
        port="5440")

    cur = conn.cursor()

    print('Logging in...')
    cur.execute("SELECT * FROM printers WHERE name=%s", (printer_name,))

    if cur.rowcount == 1:
        result = cur.fetchone()
        if result[2] == printer_password:
            print('Access granted')
            printer_id = result[0]
        else:
            raise Exception('Incorrect password')
    else:
        print('No account found. Adding new printer...')
        cur.execute("INSERT INTO printers(name, password) VALUES(%s, %s)",
            (printer_name, hashlib.sha256(printer_password.encode()).hexdigest()))
        conn.commit()
        print('New printer successfully added')

    cur.close()
except (Exception, psycopg2.DatabaseError) as error:
    print("Error:", error)
finally:
    if conn is not None:
        conn.close()

exit = False
printer_local = []

while exit == False:
    printer_jobs = []

    try:
        conn = psycopg2.connect(
            host="containers-us-west-120.railway.app",
            dbname="railway",
            user="postgres",
            password="f6yK2thZe5OJmvQnzw1T",
            port="5440")

        cur = conn.cursor()

        cur.execute("SELECT * FROM jobs WHERE printer_id=%s AND status='preparing'", (printer_id,))

        for job in cur:
            printer_jobs.append(job)
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error:", error)
        exit = True
    finally:
        if conn is not None:
            conn.close()

        api_token = 'B9BF2A023A064DF3AC872A8CF3062ED8'

        headers = {
            'X-Api-Key': api_token
        }

        printHeaders = {
            'X-Api-Key': api_token,
            'Content-Type': "application/json"
        }

        addJob = False

        # Getting current job
        get_job = requests.get('http://192.168.1.28/api/job', headers=headers)
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
        get_files = requests.get('http://192.168.1.28/api/files', headers=headers)
        files = json.loads(get_files.text)['files']

        # Sieve current files in printer memory
        for file in files:
            if file['name'] == currentJob['file']['name'] and progress['completion'] == 100.0:
                # Delete the file from printer memory
                requests.delete('http://192.168.1.28/api/files/local/{}'.format(file['name']), headers=headers)
                printer_local.remove(printer_local[0])
            else:
                for job in printer_jobs:
                    if file['name'] == '{}_{}.gcode'.format(job[2], job[0]):
                        printer_local.append((file['name'], 0.0, 'in_queue'))
                        printer_jobs.remove(job)
                    elif job == printer_jobs[-1]:
                        # Delete the file from printer memory
                        # requests.delete('http://192.168.1.28/api/files/local/{}'.format(file['name']), headers=headers)
                        print("test")

        # Add new jobs to the list
        for job in printer_jobs:
            paths = job[3].split(';')
            result = convertToGcode(paths)

            EXTRUDER_SPEED = 0.03326;
            Z_POS = 0.2;

            SKIA_XY_RANGE = 330;
            PRINTER_XY_RANGE = 220;

            scale = PRINTER_XY_RANGE / SKIA_XY_RANGE;

            GCODE_CONST = {
                "start": ";FLAVOR:Marlin ;TIME:35 ;Filament used: 0.0171848m ;Layer height: 0.2 ;MINX:96.558 ;MINY:96.693 ;MINZ:0.2 ;MAXX:138.442 ;MAXY:138.308 ;MAXZ:0.4 M140 S50 M105 M190 S50 M104 S200 M105 M109 S200 M82 ;absolute extrusion mode ; Ender 3 Custom Start G-code G92 E0 ; Reset Extruder G28 ; Home all axes G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed G1 X0.1 Y20 Z0.3 F5000.0 ; Move to start position G1 X0.1 Y200.0 Z0.3 F1500.0 E15 ; Draw the first line G1 X0.4 Y200.0 Z0.3 F5000.0 ; Move to side a little G1 X0.4 Y20 Z0.3 F1500.0 E30 ; Draw the second line G92 E0 ; Reset Extruder G1 Z2.0 F3000 ; Move Z Axis up little to prevent scratching of Heat Bed G1 X5 Y20 Z0.3 F5000.0 ; Move over to prevent blob squish G92 E0 G92 E0 G1 F2700 E-5 ;LAYER_COUNT:2 ;LAYER:0 M107 \n",
                "end": "\n G1 F2700 E12.18475 M140 S0 M107 G91 ;Relative positioning G1 E-2 F2700 ;Retract a bit G1 E-2 Z0.2 F2400 ;Retract and raise Z G1 X5 Y5 F3000 ;Wipe out G1 Z10 ;Raise Z more G90 ;Absolute positioning G1 X0 Y235 ;Present print M106 S0 ;Turn-off fan M104 S0 ;Turn-off hotend M140 S0 ;Turn-off bed M84 X Y E ;Disable all steppers but Z M82 ;absolute extrusion mode M104 S0 ;End of Gcode"
            }

            result = GCODE_CONST['start']

            extruderPosition = 0

            for path in paths:
                # Split the path into coordinates
                data = re.split(r'[ML]', path)
                filtered = list(filter(lambda x: x != '', data))

                # For each coord pass a line directing the printer to the next destination
                for s in filtered:
                    data = s.split(' ')
                    if path == paths[0] and s == filtered[0]:
                        result += f'\n G0 F2700 X{float(data[0])*scale} Y{(SKIA_XY_RANGE - float(data[1])) * scale} Z{Z_POS} E0';
                    elif s == filtered[0]:
                        result += f'\n G0 X{float(data[0])*scale} Y{(SKIA_XY_RANGE - float(data[1])) * scale}';
                    else:
                        index = filtered.index(s)
                        dExtrude = 0
                        if index > 1:
                            prev = filtered[index - 1].split(' ')
                            xDiff = float(prev[0]) - float(data[0])
                            yDiff = float(prev[1]) - float(data[1])
                            length = math.sqrt(math.pow(xDiff*scale, 2) + math.pow(yDiff*scale, 2))
                            dExtrude = length * EXTRUDER_SPEED;

                        result += f'\n G1 X{float(data[0])*scale} Y{(SKIA_XY_RANGE - float(data[1])) * scale} E{extruderPosition + dExtrude}';
                        extruderPosition += dExtrude;

                result += GCODE_CONST['end']

            # Generate .gcode file and send it to the printer
            filename = "{}_{}.gcode".format(job[2], job[0])
            gcodeFile = open(filename, "w")
            gcodeFile.write(result)
            gcodeFile.close()

            binData = open(filename,'rb')

            files=[
                ('file',(filename, binData, 'application/octet-stream'))
            ]
            requests.post('http://192.168.1.28/api/files/local', headers=headers, files=files)
            printer_local.append((filename, 0.0, 'in_queue'))

            binData.close()
            os.remove(filename)

        # Add a job to printer, if there is none
        if addJob and len(printer_local) > 0 and printer_local[0][2] != 'complete':
            addJob = False
            printFile = printer_local[0][0]
            printer_local[0] = (printer_local[0][0], printer_local[0][1], 'in_progress')
            data={'command': 'select', 'print': 'true'}
            print("Printing", printer_local[0], printFile)
            result = requests.post('http://192.168.1.28/api/files/local/{}'.format(printFile), headers=printHeaders, json=data)

        # Send update to DB
        try:
            conn = psycopg2.connect(
                host="containers-us-west-120.railway.app",
                dbname="railway",
                user="postgres",
                password="f6yK2thZe5OJmvQnzw1T",
                port="5440")

            cur = conn.cursor()

            for job in printer_local:
                job_id = re.split(r'[_.]', job[0])[1]
                cur.execute("UPDATE jobs SET (progress, status) = ({}, '{}') WHERE job_id={}".format(job[1], job[2], job_id))
                conn.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            print("Error:", error)
        finally:
            if conn is not None:
                conn.close()

        time.sleep(1)

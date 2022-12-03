import hashlib
import re

def getJobs(cur, conn, data):
    result = []
    cur.execute("SELECT * FROM jobs WHERE printer_id=%s AND status='preparing' ORDER BY job_id", (data['id'],))

    for job in cur:
        result.append(job)

    return result

def updateJobs(cur, conn, data):
    for job in data['localData']:
        job_id = re.split(r'[_.]', job[0])[1]
        cur.execute("UPDATE jobs SET (progress, status) = (%s, %s) WHERE job_id=%s", (job[1], job[2], job_id))

    conn.commit()

def logIn(cur, conn, data):
    print('Logging in...')
    cur.execute("SELECT * FROM printers WHERE name=%s", (data['name'],))

    if cur.rowcount == 1:
        result = cur.fetchone()
        if result[2] == data['password']:
            print('Access granted')
            id = result[0]
            return id
        else:
            raise Exception('Incorrect password')
    else:
        print('No account found. Adding new printer...')
        cur.execute("INSERT INTO printers(name, password) VALUES(%s, %s)",
            (data['name'], hashlib.sha256(data['password'].encode()).hexdigest()))
        conn.commit()
        print('New printer successfully added')

def resetUnfinishedFiles(cur, conn):
    print('Resetting unfinished GCode files...')
    cur.execute("UPDATE jobs SET (progress, status) = (0.0, 'preparing') WHERE status!='complete'")
    conn.commit()

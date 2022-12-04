import psycopg2

ip_address = '172.20.10.8'

api_token = 'B9BF2A023A064DF3AC872A8CF3062ED8'

headers = {
    'X-Api-Key': api_token
}

printHeaders = {
    'X-Api-Key': api_token,
    'Content-Type': "application/json"
}

connectCommand = {'command': 'connect'}

printCommand = {'command': 'select', 'print': 'true'}

# Function for connecting with and operating on the DB
def postgresConn(innerFunc, data={}):
    hasException = False
    result = None
    try:
        conn = psycopg2.connect(
            host="containers-us-west-120.railway.app",
            dbname="railway",
            user="postgres",
            password="f6yK2thZe5OJmvQnzw1T",
            port="5440")

        cur = conn.cursor()

        if data == {}:
            result = innerFunc(cur, conn)
        else:
            result = innerFunc(cur, conn, data)

        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error:", error)
        hasException = True
    finally:
        if conn is not None:
            conn.close()
        return hasException == False, result

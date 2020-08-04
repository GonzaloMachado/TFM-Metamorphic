import psycopg2


def get_connection_data(db_instance):
    db_data = {}
    db_data['database'] = db_instance.db_name
    db_data['host'] = db_instance.host
    db_data['user'] = db_instance.db_user
    db_data['password'] = db_instance.db_password
    db_data['port'] = db_instance.port
    return db_data


def db_connection(connection_data):
    try:
        conn = psycopg2.connect(**connection_data)
        response = {"status": True, "error": None}
        conn.close()
    except Exception as error:
        response = {"status": False, "error": error.args[0]}
    finally:
        conn = None
    return response


def check_statement(connection_data, statement):
    try:
        conn = psycopg2.connect(**connection_data)
        cur = conn.cursor()
        postgreSQL_select_Query = statement
        cur.execute(postgreSQL_select_Query)
        response = {"status": True, "error": None}
        conn.close()
    except Exception as error:
        response = {"status": False, "error": error.args[0]}
    finally:
        conn = None
    return response


def check_nullables_in_table(tablename):
    """Funcion que recibe el nombre de una tabla y ubica que columnas admiten null"""
    # Obtain the configuration parameters
    params = None
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()
    postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_name=%s and c.is_nullable='NO'"

    cur.execute(postgreSQL_select_Query, (tablename,))
    nullables_columns = cur.fetchall()
    for row in nullables_columns:
        print(row[0])
    cur.close()
    conn.close()


def check_nullables_in_instance():
    # Obtain the configuration parameters
    params = None
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()
    postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_schema='public' and c.is_nullable='NO'"

    cur.execute(postgreSQL_select_Query)
    nullables_columns = cur.fetchall()
    for row in nullables_columns:
        print(row[0])
    cur.close()
    conn.close()
    return nullables_columns


def get_table_from_column(column_name):
    """Funcion que recibe el nombre de una columna y ubica a que tabla pertenece."""
    # Obtain the configuration parameters
    params = None
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()
    postgreSQL_select_Query = "select c.table_name from information_schema.columns c where c.column_name=%s "

    cur.execute(postgreSQL_select_Query, (column_name,))
    columns = cur.fetchall()
    for row in columns:
        print(row[0])
    cur.close()
    conn.close()


def check_nullable_column(column_name, obj):
    # Obtain the configuration parameters
    params = get_connection_data(obj.instance)
    try:
        #Connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # Create a new cursor
        cur = conn.cursor()
        postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_schema='public' and c.is_nullable='NO' and c.column_name=%s"

        cur.execute(postgreSQL_select_Query, (column_name,))
        nullables_columns = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as error:
        response = {"status": False, "error": error.args[0]}
    finally:
        if nullables_columns:
            response = {"status": True, "nullable": True, "error": None}
        else:
            response = {"status": True, "nullable": False, "error": None}
    return response



import psycopg2


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
    params = config()
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
    params = config()
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



def get_table_from_column(column_name):
    """Funcion que recibe el nombre de una columna y ubica a que tabla pertenece."""
    # Obtain the configuration parameters
    params = config()
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


if __name__ == '__main__':
    check_nullables_in_table('persona')

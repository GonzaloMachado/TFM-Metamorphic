from config import config
import psycopg2


def prueba_db(statement):
    # Obtain the configuration parameters
    params = config()
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()

    postgreSQL_select_Query = statement
    #postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_name='persona' and c.is_nullable='NO'"

    cur.execute(postgreSQL_select_Query)
    print("Selecting rows from mobile table using cursor.fetchall")
    all_records = cur.fetchall()
    print("Print each row and it's columns values")

    for row in all_records:
        print("Id = ", row[0], )
    cur.close()
    conn.close()


def check_statement(current_statement):
    try:
        # Obtain the configuration parameters
        params = config()
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        # Create a new cursor
        cur = conn.cursor()

        postgreSQL_select_Query = current_statement
        cur.execute(postgreSQL_select_Query)

    except Exception as error:
        print("Oops! An exception has occured:", error)
        print("Exception TYPE:", type(error))


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

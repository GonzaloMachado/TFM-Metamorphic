from config import config
import psycopg2


def prueba_db():
    # Obtain the configuration parameters
    params = config()
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()

    postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_name='persona' and c.is_nullable='NO'"

    cur.execute(postgreSQL_select_Query)
    print("Selecting rows from mobile table using cursor.fetchall")
    mobile_records = cur.fetchall()
    print("Print each row and it's columns values")

    for row in mobile_records:
        print("Id = ", row[0], )
    cur.close()
    conn.close()


def check_nullables(tablename):
    # Obtain the configuration parameters
    params = config()
    # Connect to the PostgreSQL database
    conn = psycopg2.connect(**params)
    # Create a new cursor
    cur = conn.cursor()
    postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_name=%s and c.is_nullable='NO' "

    cur.execute(postgreSQL_select_Query, (tablename,))
    nullables_columns = cur.fetchall()
    for row in nullables_columns:
        print(row[0])
    cur.close()
    conn.close()

def get_table(column_name):
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
    check_nullables('persona')

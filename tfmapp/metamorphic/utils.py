from psqlparse import parse, nodes
import psycopg2
from .printer import *


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


def main(query_string):
    """Sentencia que se recibe desde el FRONTEND"""
    # query_string = "select a+b from ta where x < (select t.col from t where c)"
    print(query_string)
    """Probar que el statement sea valido en la BD (Ya incluye sintaxis)"""
    # prueba_db.check_statement(query_string)
    """Se obtiene el parsed tree"""
    parsed_tree = parse(query_string)
    # """se limpia el arbol"""
    # allData = list()
    # for statement in parsed_tree:
    #     allData.append(clean_tree(statement))
    """Se buscan los casos y se hacen transformaciones"""
    # equivalent = select_match_case(allData[0])
    serialized = serialize(parsed_tree)
    equivalent2 = select_match_case_2(parsed_tree[0])
    print(serialized)
    # other = parse(equivalent)
    print('done')
    return serialized


def select_match_case_2(statement):
    """Función que utiliza el parsed tree para conseguir casos."""
    changes = []
    if statement.target_list is not None:
        for position, current_target in enumerate(statement.target_list):
            if isinstance(current_target.val, nodes.AExpr):
                detected_case = caso_uno(current_target.val)
                current_change = save_changes(current_target, position, detected_case)
                changes.append(current_change)
                statement.target_list[position] = current_change['change']
                serialized = serialize([statement])
                print(serialized)
            else:
                print("No cases found in target_list")
    if statement.where_clause is not None:
        # HAY QUE MEJORAR EL MATCH DEL CASO
        # Funcion que se encargue de los SubLink?
        if isinstance(statement.where_clause, nodes.BoolExpr) and isinstance(statement.where_clause.args[0], nodes.SubLink):
            where_compuesto_bool(statement.where_clause)
        elif isinstance(statement.where_clause, nodes.AExpr) and isinstance(statement.where_clause.rexpr, nodes.SubLink):
            where_other(statement.where_clause)
        elif isinstance(statement.where_clause, nodes.SubLink):
            where_compuesto(statement.where_clause)
        else:
            # NO SE PUEDE SUSTITUIR T0D0 EL WHERE_CLAUSE
            statement.where_clause = where_simple(statement.where_clause)
            serialized = serialize([statement])
            print(serialized)
            # HAY QUE GUARDAR EL CAMBIO
    return changes


def save_changes(current_target, position, detected_case):
    current_change = dict()
    current_change['node'] = current_target
    current_change['position'] = position
    current_change['change'] = detected_case
    return current_change


def caso_uno(target_node):
    """Cubre la relación B.1 y B.2 de la tabla 3"""
    if target_node.name[0].val == "||":
        identity_element = "''"
    else:
        identity_element = 1 if target_node.name[0].val == ("*" or "/") else 0
    if isinstance(target_node.lexpr, nodes.AExpr):
        equivalent = caso_uno(
            target_node.lexpr) + f"{target_node.name[0].val} COALESCE({target_node.rexpr.fields[0].val},{identity_element})"
    else:
        equivalent = f"COALESCE({target_node.lexpr.fields[0].val},{identity_element}) {target_node.name[0].val} COALESCE({target_node.rexpr.fields[0].val},{identity_element})"
    return equivalent


def where_simple(current_node):
    equivalent = ""
    string_value = node_to_str(current_node)
    if isinstance(current_node, nodes.AExpr):
        if current_node.kind == 0:
            """Kind 0 es comp"""
            equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null OR {node_to_str(current_node.rexpr)} is null"
        elif current_node.kind == 10 or current_node.kind == 11:
            """Kind 10/11 es BETWEEN/NOT BETWEEN"""
            if isinstance(current_node.rexpr, list):
                equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null"
                for item in current_node.rexpr:
                    equivalent += f" OR {node_to_str(item)} is null"
            else:
                equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null OR {node_to_str(current_node.rexpr)} is null"
        elif current_node.kind == 6:
            """Kind 6 es IN/NOT IN"""
            if isinstance(current_node.rexpr, list):
                equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null"
                for item in current_node.rexpr:
                    equivalent += f" OR {node_to_str(item)} is null"
            else:
                equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null OR {node_to_str(current_node.rexpr)} is null"
        elif current_node.kind == 7:
            """Kind 7 es LIKE/NOT LIKE"""
            equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null OR {node_to_str(current_node.rexpr)} is null"
    return equivalent


def where_compuesto(current_node):
    equivalent = ""
    equivalent2 = ""
    subselect_str = node_to_str(current_node.subselect)
    testexpr = current_node.testexpr.fields[0].str
    if current_node.sub_link_type == 1:
        if current_node.oper_name[0].str == "<>":
            # CASO A.6
            equivalent += f"{testexpr} NOT IN ({subselect_str})"
        else:
            # CASO A.1 OJO CON EL ALIAS 'AS'
            columns = node_to_str(current_node.subselect.target_list)
            neg_sign = negate_operator(current_node.oper_name[0].str)
            equivalent += f"NOT EXISTS( {subselect_str}  AND {testexpr}  {neg_sign}  {columns})"
            equivalent2 += f"NOT {testexpr}  {neg_sign} ANY ({subselect_str})"
    elif current_node.sub_link_type == 2:
        pass
    pass

def where_compuesto_bool(current_node):
    equivalent = ""
    equivalent2 = ""
    subnode = current_node.args[0]
    subselect_str = node_to_str(subnode.subselect)
    if subnode.sub_link_type == 2:
        testexpr = subnode.testexpr.fields[0].str
        columns = node_to_str(subnode.subselect.target_list)
        if subnode.oper_name is not None:
            # CASO A.2 - HAY UN ANY
            oper_name = subnode.oper_name[0].str
            neg_sign = negate_operator(oper_name)
            equivalent += f"{testexpr}  {neg_sign} ALL ({subselect_str})"
            equivalent2 += f"NOT EXISTS ({subselect_str} AND {testexpr} {oper_name} {columns} )"
        else:
            # CASO A.3 - HAY UN IN
            equivalent += f"NOT EXISTS ({subselect_str} AND {testexpr} = {columns})"
            # NOT EXISTS (QUEY AND X = COL)
            # X <> ALL (QUERY)
            equivalent2 += f"{testexpr} <> ALL ({subselect_str})"
    pass


def where_other(current_node):
    equivalent = ""
    subnode = current_node.rexpr
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(current_node.lexpr)
    oper_name = current_node.name[0].str
    neg_sign = negate_operator(oper_name)
    equivalent += f"{testexpr} IS NULL OR {testexpr} {oper_name} COALESCE({subselect_str}, 0) OR {testexpr} {neg_sign} COALESCE({subselect_str}, 0)"
    pass


def negate_operator(operator):
    defined_operators = ['<', '<=', '>', '>=', '=', '<>']
    negate_operators = ['>=', '>', '<=', '<', '<>', '=']
    index_search = defined_operators.index(operator)
    return negate_operators[index_search]


def node_to_str(target_node):
    serializer = Serializer()
    serializer.print_node(target_node)
    return serializer.getvalue()



if __name__ == '__main__':
    check_nullables_in_table('persona')

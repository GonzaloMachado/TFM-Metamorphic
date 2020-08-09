from .psqlparse import parse, nodes
from . import printer
import psycopg2
import six
import copy
import json

global conn_data


def parse_query(query):
    # connection = db_connection(connection_data)
    parsed_tree = parse(query.query_text)
    parsed_tree[0].get_nullable_state()
    # response = parsed_tree[0].nullable
    response = {
        "nullable": parsed_tree[0].nullable,
        "changes": search_transformations(parsed_tree[0])
    }
    return response

"""SE USA UNA ESTRUCTURA AUXILIAR PARA REGRESAR EL ARBOL A SU ESADO ORIGINAL"""
def search_transformations(statement):
    aux = copy.deepcopy(statement)
    transformations = list()
    if statement.target_list is not None:
    # if statement.target_list is not None and statement.nullable_results:
        for position, current_target in enumerate(statement.target_list):
            if isinstance(current_target.val, nodes.AExpr):
                if current_target.val.name[0].val in ('+', '-', '*', '/', '||'):
                    detected_case = transform_a_expr_select(current_target.val)
                    aux.target_list[position] = detected_case
                    save_change(aux, statement, transformations, 'B1/B2')
            else:
                print("No cases found in target_list")
    if statement.where_clause is not None:
        if isinstance(statement.where_clause, nodes.AExpr):
            a_expr_where(statement, aux, transformations, statement.where_clause)
        elif isinstance(statement.where_clause, nodes.BoolExpr):
            bool_expr_where(statement, aux, transformations, statement.where_clause)
        elif isinstance(statement.where_clause, nodes.SubLink):
            sub_link_where(statement, aux, transformations, statement.where_clause)
    return transformations


def transform_a_expr_select(target_node):
    """Cubre la relación B.1 y B.2 de la tabla 3"""
    if target_node.name[0].val == "||":
        identity_element = "''"
    else:
        identity_element = 1 if target_node.name[0].val == ("*" or "/") else 0
    if isinstance(target_node.lexpr, nodes.AExpr):
        equivalent = transform_a_expr_select(
            target_node.lexpr) + f"{target_node.name[0].val} COALESCE({target_node.rexpr.fields[0].val},{identity_element})"
    else:
        equivalent = f"COALESCE({target_node.lexpr.fields[0].val},{identity_element}) {target_node.name[0].val} COALESCE({target_node.rexpr.fields[0].val},{identity_element})"
    return equivalent


def a_expr_where(statement, aux, transformations, a_expr_node):
    if isinstance(a_expr_node.rexpr, nodes.SubLink):
        aux.where_clause = where_other(a_expr_node)
        save_change(aux, statement, transformations, "A.7")
        detected_case = search_transformations(a_expr_node.rexpr.subselect)
        for item in detected_case:
            aux.where_clause.rexpr.subselect = item['transformacion']
            save_change(aux, statement, transformations, "Subquery")
    else:
        aux.where_clause = where_simple(statement.where_clause)
        save_change(aux, statement, transformations, "B.3-B.6")


def bool_expr_where(statement, aux, transformations, bool_expr_node):
    for arg in bool_expr_node.args:
        if isinstance(arg, nodes.SubLink):
            aux.where_clause = where_compuesto_bool(statement.where_clause)
            save_change(aux, statement, transformations, "A.2/A.3")
            detected_case = search_transformations(statement.where_clause.args[0].subselect)
            for item in detected_case:
                aux.where_clause.args[0].subselect = '('+item['transformacion']+')'
                save_change(aux, statement, transformations, "Subquery")


def sub_link_where(statement, aux, transformations, sub_link_node):
    aux.where_clause = where_compuesto(sub_link_node)
    save_change(aux, statement, transformations, "A.1/A.6")


def save_change(aux, statement, transformations, info):
    serialized = printer.serialize([aux])
    transformations.append(dict(transformacion=serialized, info=info))
    aux.target_list = statement.target_list
    aux.where_clause = statement.where_clause


def node_to_str(target_node):
    serializer = printer.Serializer()
    serializer.print_node(target_node)
    return serializer.getvalue()


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
            # CASO A.1 OJO CON EL ALIAS 'AS EN EQUIVALENT1'
            columns = node_to_str(current_node.subselect.target_list)
            neg_sign = negate_operator(current_node.oper_name[0].str)
            equivalent += f"NOT EXISTS( {subselect_str}  AND {testexpr}  {neg_sign}  {columns})"
            equivalent2 += f"NOT {testexpr}  {neg_sign} ANY ({subselect_str})"
    return equivalent


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
    return equivalent


"""CASO A.7"""
def where_other(current_node):
    equivalent = ""
    subnode = current_node.rexpr
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(current_node.lexpr)
    oper_name = current_node.name[0].str
    neg_sign = negate_operator(oper_name)
    equivalent += f"{testexpr} IS NULL OR ({subselect_str}) IS NULL OR {testexpr} {oper_name} ({subselect_str})"
    return equivalent


def negate_operator(operator):
    defined_operators = ['<', '<=', '>', '>=', '=', '<>']
    negate_operators = ['>=', '>', '<=', '<', '<>', '=']
    index_search = defined_operators.index(operator)
    return negate_operators[index_search]


def get_conn_data(db_instance):
    global conn_data
    conn_data = dict()
    conn_data['database'] = db_instance.db_name
    conn_data['host'] = db_instance.host
    conn_data['user'] = db_instance.db_user
    conn_data['password'] = db_instance.db_password
    conn_data['port'] = db_instance.port


def check_nullable(column_name, obj):
    # Obtain the configuration parameters
    global conn_data
    try:
        #Connect to the PostgreSQL database
        conn = psycopg2.connect(**conn_data)
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


def run_statement(query):
    try:
        global conn_data
        conn = psycopg2.connect(**conn_data)
        cur = conn.cursor()
        #cur = conn.cursor(cursor_factory=psycopg2.extras.NamedTupleCursor)
        # cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        postgreSQL_select_Query = query
        cur.execute(postgreSQL_select_Query)
        rows = [dict((cur.description[i][0], value if value is not None else 'Null')
                     for i, value in enumerate(row)) for row in cur.fetchall()]
        # rows2= [json.dumps(rows)]
        columns = [dict(data=column.name, name=column.name) for column in cur.description]
        response = {"status": True, "columns": columns, "rows": rows, "rowcount": cur.rowcount, "error": None}
        conn.close()
    except Exception as error:
        response = {"status": False, "error": error.args[0]}
    finally:
        conn = None
    return response


def compare_results(original, transformation):
    if original["rowcount"] == transformation["rowcount"]:
        union = zip(original["rows"], transformation["rows"])
        if any(x != y for x, y in union):
            return {"status": False, "Text": "Diferencia en la unión"}
        else:
            return {"status": True, "Text": "Todo en orden"}
    else:
        return {"status": False, "Text": "Diferencia en el número de filas"}

from .psqlparse import parse, nodes
from . import printer
import psycopg2
import six
import copy
import json

global conn_data

NODE_ANALYZERS = {}


def parse_query(query):
    # connection = db_connection(connection_data)
    parsed_tree = parse(query.query_text)
    parsed_tree[0].get_nullable_state()
    # response = parsed_tree[0].nullable
    analize_node(parsed_tree[0])
    response = {
        "nullable": parsed_tree[0].nullable,
        "changes": parsed_tree[0].equivalent
    }
    return response


def get_case_for_node(node):
    """Get specific case implementation for given `node` instance."""

    try:
        return NODE_ANALYZERS[type(node)]
    except KeyError:
        return None
        # raise NotImplementedError("Printer for node %r is not implemented yet"
        #                           % node.__class__.__name__)


def node_analyzer(node_class):
    """Decorator to change a specific case in sql statement"""

    def decorator(impl):
        assert node_class not in NODE_ANALYZERS
        NODE_ANALYZERS[node_class] = impl
        return impl

    return decorator


def analize_node(node):
    case = get_case_for_node(node)
    if case and node.nullable:
        case(node)


@node_analyzer(nodes.SelectStmt)
def select_statement(node):
    aux = copy.deepcopy(node)
    transformations = list()
    if node.target_list is not None:
        for position, current_target in enumerate(node.target_list):
            if isinstance(current_target.val, nodes.AExpr):
                if current_target.val.name[0].val in ('+', '-', '*', '/', '||'):
                    if isinstance(current_target.val.lexpr, nodes.ColumnRef):
                        transform_a_expr_select(current_target.val)
                        for change in current_target.val.equivalent:
                            aux.target_list[position] = copy.deepcopy(change)
                            save_change(aux, node)
                            aux = copy.deepcopy(node)
            else:
                print("No cases found in target_list")
    if node.where_clause is not None:
        analize_node(node.where_clause)
        for change in node.where_clause.equivalent:
            aux.where_clause = copy.deepcopy(change)
            save_change(aux, node)


@node_analyzer(nodes.AExpr)
def a_expr(a_expr_node):
    aux = copy.deepcopy(a_expr_node)
    if a_expr_node.kind in (0, 6, 7, 10):
        where_simple(a_expr_node)
    if isinstance(a_expr_node.lexpr, list):
        for position, item in enumerate(a_expr_node.lexpr):
            analize_node(item)
            for change in item.equivalent:
                aux.lexpr[position] = copy.deepcopy(change)
                save_change(aux, a_expr_node)
                aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.lexpr, nodes.Node):
        analize_node(a_expr_node.lexpr)
        for change in a_expr_node.lexpr.equivalent:
            aux.lexpr = copy.deepcopy(change)
            save_change(aux, a_expr_node)
            aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.rexpr, list):
        for position, item in enumerate(a_expr_node.rexpr):
            analize_node(item)
            for change in item.equivalent:
                aux.rexpr[position] = copy.deepcopy(change)
                save_change(aux, a_expr_node)
                aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.rexpr, nodes.Node):
        analize_node(a_expr_node.rexpr)
        for change in a_expr_node.rexpr.equivalent:
            aux.rexpr = copy.deepcopy(change)
            save_change(aux, a_expr_node)
            aux = copy.deepcopy(a_expr_node)


@node_analyzer(nodes.BoolExpr)
def bool_expr(bool_expr_node):
    aux = copy.deepcopy(bool_expr_node)
    for position, arg in enumerate(bool_expr_node.args):
        analize_node(arg)
        for change in arg.equivalent:
            aux.args[position] = copy.deepcopy(change)
            save_change(aux, bool_expr_node)
            aux = copy.deepcopy(bool_expr_node)
    if bool_expr_node.boolop == 2:
        for arg in bool_expr_node.args:
            if isinstance(arg, nodes.SubLink):
                if arg.sub_link_type == 2:
                    where_compuesto_bool(bool_expr_node)
                    # save_change(aux, statement, transformations, "A.2/A.3")
                if arg.sub_link_type == 0:
                    """Verificar ALIAS"""
                    columns = node_to_str(arg.subselect.target_list).split(" ")
                    where_exists(bool_expr_node, columns)
                    # save_change(aux, statement, transformations, "A.4/A.5")


@node_analyzer(nodes.SubLink)
def sub_link(sub_link_node):
    aux = copy.deepcopy(sub_link_node)
    if sub_link_node.sub_link_type == 1:
        where_compuesto(sub_link_node)
    analize_node(sub_link_node.subselect)
    for change in sub_link_node.subselect.equivalent:
        aux.subselect = copy.deepcopy(change)
        save_change(aux, sub_link_node)
        aux = copy.deepcopy(sub_link_node)



def transform_a_expr_select(target_node):
    """Cubre la relación B.1 y B.2 de la tabla 3"""
    if target_node.name[0].val == "||":
        target_node.transformations_applied.append('B2')
        identity_element = "''"
    else:
        target_node.transformations_applied.append('B1')
        identity_element = 1 if target_node.name[0].val == ("*" or "/") else 0
    if isinstance(target_node.lexpr, nodes.AExpr):
        equivalent = transform_a_expr_select(
            target_node.lexpr) + f"{target_node.name[0].val} COALESCE({'.'.join(c.str for c in target_node.rexpr.fields)},{identity_element})"

    else:
        equivalent = f"COALESCE({'.'.join(c.str for c in target_node.lexpr.fields)},{identity_element}) {target_node.name[0].val} COALESCE({'.'.join(c.str for c in target_node.rexpr.fields)},{identity_element})"
    target_node.equivalent.append(equivalent)
    #return equivalent


def get_column(target_list):
    for item in target_list:
        if isinstance(item.val, nodes.FuncCall):
            return node_to_str(item.val.args)
        else:
            return node_to_str(target_list)

"""CASO A.4 Y A.5 Hay que usar las columnas externas e internas y ver el ALIAS"""
def get_from_tables(from_clause):
    tables = list()
    for column in from_clause:
        tables.append(column.relname)
    return tables



def save_change(aux, node):
    serialized = printer.serialize([aux])
    node.equivalent.append(serialized)


def node_to_str(target_node):
    serializer = printer.Serializer()
    serializer.print_node(target_node)
    return serializer.getvalue()


"""CASO B4 ,B5 Y B6"""
def where_simple(current_node):
    equivalent = ""
    string_value = node_to_str(current_node)
    equivalent += string_value
    # equivalent = string_value + f" OR {node_to_str(current_node.lexpr)} is null OR {node_to_str(current_node.rexpr)} is null"
    if isinstance(current_node.lexpr, list):
        for item in current_node.lexpr:
            if not isinstance(item, nodes.AConst):
                equivalent += f" OR {node_to_str(item)} IS NULL"
    else:
        if not isinstance(current_node.lexpr, nodes.AConst):
            equivalent += f" OR {node_to_str(current_node.lexpr)} IS NULL"
    if isinstance(current_node.rexpr, list):
        for item in current_node.rexpr:
            if not isinstance(item, nodes.AConst):
                equivalent += f" OR {node_to_str(item)} IS NULL"
    else:
        if not isinstance(current_node.rexpr, nodes.AConst):
            equivalent += f" OR {node_to_str(current_node.rexpr)} IS NULL"
    current_node.transformations_applied.append('B3')
    current_node.equivalent.append("(" + equivalent + ")")
    #return "(" + equivalent + ")"


"""CASO A1"""
def where_compuesto(current_node):
    equivalent = ""
    equivalent2 = ""
    subselect_str = node_to_str(current_node.subselect)
    testexpr = current_node.testexpr.fields[0].str
    if current_node.sub_link_type == 1:
        if current_node.oper_name[0].str == "<>":
            equivalent += f"{testexpr} NOT IN ({subselect_str})"
        else:
            # CASO A.1 OJO CON EL ALIAS 'AS EN EQUIVALENT1'
            columns = get_column(current_node.subselect.target_list)
            operator = current_node.oper_name[0].str
            neg_sign = negate_operator(operator)
            if current_node.subselect.where_clause:
                equivalent += f"NOT EXISTS ( {subselect_str}  AND {testexpr}  {neg_sign}  {columns})"
            else:
                equivalent += f"NOT EXISTS ( {subselect_str}  WHERE {testexpr}  {neg_sign}  {columns})"
            equivalent2 += f"NOT {testexpr}  {neg_sign} ANY ({subselect_str})"
    current_node.transformations_applied.append('A1')
    current_node.equivalent.extend((equivalent, equivalent2))
    # return "(" + equivalent + ")"


"""CASO A.4"""
def where_other(current_node):
    equivalent = ""
    subnode = current_node.rexpr
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(current_node.lexpr)
    oper_name = current_node.name[0].str
    neg_sign = negate_operator(oper_name)
    equivalent += f"{testexpr} IS NULL OR ({subselect_str}) IS NULL OR {testexpr} {oper_name} ({subselect_str})"
    current_node.transformations_applied.append('A4')
    current_node.equivalent.append("(" + equivalent + ")")
    # return "(" + equivalent + ")"


def where_compuesto_bool(current_node):
    equivalent = ""
    equivalent2 = ""
    equivalent3 = ""
    subnode = current_node.args[0]
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(subnode.testexpr)
    # columns = node_to_str(subnode.subselect.target_list)
    columns = get_column(subnode.subselect.target_list)
    if subnode.oper_name is not None:
        # CASO A.2 - HAY UN ANY
        oper_name = subnode.oper_name[0].str
        neg_sign = negate_operator(oper_name)
        # equivalent2 += f"{testexpr}  {neg_sign} ALL ({subselect_str})"
        if subnode.subselect.where_clause:
            equivalent += f"NOT EXISTS ({subselect_str} AND {testexpr} {oper_name} {columns})"
        else:
            equivalent += f"NOT EXISTS ({subselect_str} WHERE {testexpr} {oper_name} {columns})"
        current_node.transformations_applied.extend(('A2','A5'))
        if neg_sign == '=':
            equivalent2 += f"{testexpr}  NOT IN ({subselect_str})"
        else:
            equivalent2 += f"{testexpr}  {neg_sign} ALL ({subselect_str})"
    else:
        # CASO A.3 - HAY UN IN
        if subnode.subselect.where_clause:
            equivalent += f"NOT EXISTS ({subselect_str} AND {testexpr} = {columns})"
        else:
            equivalent += f"NOT EXISTS ({subselect_str} WHERE {testexpr} = {columns})"
        # ADEMAS CASO A6
        equivalent2 = f"{testexpr} {negate_operator('=')} ALL ({node_to_str(subselect_str)})"
        # ADEMAS CASO A7
        equivalent3 = f"NOT {testexpr} = ANY ({node_to_str(subselect_str)})"
        current_node.transformations_applied.append('A3')
        # current_node.equivalent.append(equivalent3)
    # return "(" + equivalent + ")"
    current_node.equivalent.extend(("" + equivalent + "", equivalent2, equivalent3))
    # current_node.equivalent.append("(" + equivalent2 + ")")


def where_exists(current_node, columns):
    equivalent = ""
    columns_ref = list()
    subselect_statement = copy.deepcopy(current_node.args[0].subselect)
    subselect_where = current_node.args[0].subselect.where_clause
    internal_tables = get_from_tables(current_node.args[0].subselect.from_clause)
    if isinstance(subselect_where, nodes.AExpr):
        oper = subselect_where.name[0].str
        if isinstance(subselect_where.lexpr, nodes.ColumnRef):
            columns_ref.append(subselect_where.lexpr.fields)
        if isinstance(subselect_where.rexpr, nodes.ColumnRef):
            columns_ref.append(subselect_where.rexpr.fields)
            subselect_statement.where_clause = None
    elif isinstance(subselect_where, nodes.BoolExpr) and subselect_where.boolop == 0:
        arg = subselect_where.args[0]
        oper = arg.name[0].str
        if isinstance(arg.lexpr, nodes.ColumnRef):
            columns_ref.append(arg.lexpr.fields)
        if isinstance(arg.rexpr, nodes.ColumnRef):
            columns_ref.append(arg.rexpr.fields)
        subselect_statement.where_clause = subselect_where.args[1]
    for column in columns_ref:
        if column[0].str not in internal_tables:
            if oper == '=':
                current_node.transformations_applied.append('A5')
                equivalent = f"{column[0].str} NOT IN ({node_to_str(subselect_statement)})"
            else:
                current_node.transformations_applied.append('A6')
                equivalent2 = f"{column[0].str} {negate_operator(oper)} ALL ({node_to_str(subselect_statement)})"
                current_node.equivalent.append("" + equivalent2 + "")
                """A.7"""
                equivalent = f"NOT {column[0].str} {oper} ANY ({node_to_str(subselect_statement)})"
                current_node.transformations_applied.append('A7')

    current_node.equivalent.append("" + equivalent + "")


def negate_operator(operator):
    defined_operators = ['<', '<=', '>', '>=', '=', '<>']
    negated_operators = ['>=', '>', '<=', '<', '<>', '=']
    index_search = defined_operators.index(operator)
    return negated_operators[index_search]


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
        postgreSQL_select_Query = "select c.column_name from information_schema.columns c where c.table_schema='public' and c.is_nullable='YES' and c.column_name=%s"

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
        rows = [dict((cur.description[i][0], value if value is not None else '[null]')
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

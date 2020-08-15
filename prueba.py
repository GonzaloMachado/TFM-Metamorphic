from psqlparse import parse, nodes
from prueba_db import check_all_nullables_in_instance, check_nullable_column

import printer2 as printer
import prueba_db
import six, copy

NODE_ANALYZERS = {}
"Registry of specialized printers."


# select SUBSTR("geeksforgeeks", 1, 5)  from persona as tabla1 , departamento where edad>35 and city="Paris"
# or sexo is not null
# select a from ta where x<= all(select y from tb)
# select colA from T2 as A where NOT EXISTS (SELECT * FROM T2 as B WHERE Colc='x' and B.colB>A.colB)
# select col1 + col2 from tabla1 where edad between 25 and 35

def main():
    """Sentencia que se recibe desde el FRONTEND"""
    # query_string = "select ka||level from ta where ka > (select ka||level from ta)"
    # query_string = "select colA from T2 where a<(select ka||level from ta) and  c > (select ka from ta)"
    query_string = "select colA from T2 where a < (select ka||level from ta where x>2)"
    # query_string = "select colA from T2 as A where NOT x > any (select * from T2)"
    # query_string = "select colA from T2 as A where x <> all (select ka || level from T1 where a<2)"
    # query_string = "select colA from t1 where a in (b,3,5,6)"
    parsed_tree = parse(query_string)
    print(printer.serialize([parsed_tree[0]]))
    equivalent = select_match_case_3(parsed_tree[0])
    for item in equivalent:
        print(item["info"])
        print(item["transformacion"])
    print('done')



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


def analize_node(statement, aux, transformations, node):
    case = get_case_for_node(node)
    case(statement, aux, transformations, node)


"""SE USA UNA ESTRUCTURA AUXILIAR PARA REGRESAR EL ARBOL A SU ESADO ORIGINAL"""
@node_analyzer(nodes.SelectStmt)
def select_match_case_3(statement):
    aux = copy.deepcopy(statement)
    transformations = list()
    if statement.target_list is not None:
        for position, current_target in enumerate(statement.target_list):
            if isinstance(current_target.val, nodes.AExpr):
                if current_target.val.name[0].val in ('+', '-', '*', '/', '||'):
                    detected_case = transform_a_expr_select(current_target.val)
                    aux.target_list[position] = detected_case
                    save_change(aux, statement, transformations, 'B1/B2')
            else:
                print("No cases found in target_list")
    from_info = get_from_tables(statement.from_clause)
    if statement.where_clause is not None:
        # func = get_case_for_node(statement, aux, transformations, statement.where_clause)
        # func( statement.where_clause)
        analize_node(statement, aux, transformations, aux.where_clause)
        # if isinstance(statement.where_clause, nodes.AExpr):
        #     a_expr_where(statement, aux, transformations, statement.where_clause)
        # elif isinstance(statement.where_clause, nodes.BoolExpr):
        #     bool_expr_where(statement, aux, transformations, statement.where_clause)
        # elif isinstance(statement.where_clause, nodes.SubLink):
        #     sub_link_where(statement, aux, transformations, statement.where_clause)
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


"""DEBERIA ENCARGARSE DE B3 B4 B5 B6 A1 A7"""
@node_analyzer(nodes.AExpr)
def a_expr_where(statement, aux, transformations, a_expr_node):
    if a_expr_node.kind in (0, 6, 7, 10):
        equiv = where_simple(a_expr_node)
        a_expr_node.equivalent.append(equiv)
        # save_change(aux, statement, transformations, 'B.3-B.6')
    if isinstance(a_expr_node.rexpr, nodes.SubLink):
        equiv2 = where_other(a_expr_node)
        a_expr_node.equivalent.append(equiv2)
        # save_change(aux, statement, transformations, "A.7")
        detected_case = select_match_case_3(a_expr_node.rexpr.subselect)
        if detected_case:
            for item in detected_case:
                a_expr_node.rexpr = "("+item['transformacion']+")"
                save_change(aux, statement, transformations, "Subquery")
    # if isinstance(a_expr_node.lexpr, list):
    #     for item in a_expr_node.lexpr:
    #         func = get_case_for_node(item)
    #         if func:
    #             equiv = func(statement, aux, transformations, item)
    # if isinstance(a_expr_node.lexpr, nodes.Node):
    #     func = get_case_for_node(a_expr_node.lexpr)
    #     if func:
    #         equiv = func(statement, aux, transformations, a_expr_node.lexpr)
    # if isinstance(a_expr_node.rexpr, list):
    #     for item in a_expr_node.rexpr:
    #         func = get_case_for_node(item)
    #         if func:
    #             equiv = func(statement, aux, transformations, item)
    # if isinstance(a_expr_node.rexpr, nodes.Node):
    #     func = get_case_for_node(a_expr_node.rexpr)
    #     if func:
    #         equiv = func(statement, aux, transformations, a_expr_node.rexpr)
    """Y SI HAY MAS DE UN CASO?"""


@node_analyzer(nodes.BoolExpr)
def bool_expr_where(statement, aux, transformations, bool_expr_node):
    for position, arg in enumerate(bool_expr_node.args):
        analize_node(statement, aux, transformations, arg)
        for change in arg.equivalent:
            aux.where_clause.args[position] = change
            save_change(aux, statement, transformations, "")
    if bool_expr_node.boolop == 2:
        for arg in bool_expr_node.args:
            if isinstance(arg, nodes.SubLink):
                if arg.sub_link_type == 2:
                    aux.where_clause = where_compuesto_bool(statement.where_clause)
                    save_change(aux, statement, transformations, "A.2/A.3")
                if arg.sub_link_type == 0:
                     aux.where_clause = where_exists(statement.where_clause)
                     save_change(aux, statement, transformations, "A.4/A.5")
                detected_case = select_match_case_3(statement.where_clause.args[0].subselect)
                if detected_case:
                     for item in detected_case:
                        aux.where_clause.args[0].subselect = '(' + item['transformacion'] + ')'
                        save_change(aux, statement, transformations, "Subquery")


@node_analyzer(nodes.SubLink)
def sub_link_where(statement, aux, transformations, sub_link_node):
    # equivalent = where_compuesto(sub_link_node)
    aux.where_clause = where_compuesto(sub_link_node)
    save_change(aux, statement, transformations, "A.1/A.6")
    detected_case = select_match_case_3(sub_link_node.subselect)
    if detected_case:
        for item in detected_case:
            aux.where_clause.subselect = item['transformacion']
            save_change(aux, statement, transformations, "Subquery")


"""CASO A.4 Y A.5 Hay que usar las columnas externas e internas y ver el ALIAS"""
def get_from_tables(from_clause):
    for column in from_clause:
        pass


def save_change(aux, statement, transformations, info):
    serialized = printer.serialize([aux])
    # print(serialized)
    transformations.append(dict(transformacion=serialized, info=info))
    aux.target_list = copy.deepcopy(statement.target_list)
    aux.where_clause = copy.deepcopy(statement.where_clause)


def node_to_str(target_node):
    serializer = printer.Serializer()
    serializer.print_node(target_node)
    return serializer.getvalue()


def case_b3(current_node):
    equivalent = ""
    string_value = node_to_str(current_node)
    equivalent += string_value
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
    return "(" + equivalent + ")"


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
    return "(" + equivalent + ")"


"""CASO A1 Y A6"""
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
    return "(" + equivalent + ")"


"""CASO A.7"""
def where_other(current_node):
    equivalent = ""
    subnode = current_node.rexpr
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(current_node.lexpr)
    oper_name = current_node.name[0].str
    neg_sign = negate_operator(oper_name)
    equivalent += f"{testexpr} IS NULL OR ({subselect_str}) IS NULL OR {testexpr} {oper_name} ({subselect_str})"
    return "(" + equivalent + ")"


def where_compuesto_bool(current_node):
    equivalent = ""
    equivalent2 = ""
    subnode = current_node.args[0]
    subselect_str = node_to_str(subnode.subselect)
    testexpr = subnode.testexpr.fields[0].str
    columns = node_to_str(subnode.subselect.target_list)
    if subnode.oper_name is not None:
        # CASO A.2 - HAY UN ANY
        oper_name = subnode.oper_name[0].str
        neg_sign = negate_operator(oper_name)
        equivalent += f"{testexpr}  {neg_sign} ALL ({subselect_str})"
        equivalent2 += f"NOT EXISTS ({subselect_str} AND {testexpr} {oper_name} {columns})"
    else:
        # CASO A.3 - HAY UN IN
        equivalent += f"NOT EXISTS ({subselect_str} AND {testexpr} = {columns})"
        # NOT EXISTS (QUEY AND X = COL)
        # X <> ALL (QUERY)
        equivalent2 += f"{testexpr} <> ALL ({subselect_str})"
    return "(" + equivalent + ")"



def where_exists(current_node):
    equivalent = ""

    return equivalent


def negate_operator(operator):
    defined_operators = ['<', '<=', '>', '>=', '=', '<>']
    negate_operators = ['>=', '>', '<=', '<', '<>', '=']
    index_search = defined_operators.index(operator)
    return negate_operators[index_search]


def range_var_type(from_clause):
    _tables = []
    for item in from_clause:
        _tablesInfo = dict()
        if item.alias:
            _tablesInfo['alias'] = item.alias.aliasname
        else:
            _tablesInfo['alias'] = None
        _tablesInfo['schemaname'] = item.schemaname
        _tablesInfo['relname'] = item.relname
        _tables.append(_tablesInfo)
    return _tables


def column_ref_type(target_list):
    _fields = dict()
    if isinstance(target_list.val.fields[0], nodes.AStar):
        _fields['type'] = 'AStar'
        _fields['name'] = '*'
        _fields['alias'] = None
    else:
        _fields['type'] = 'ColumnRef'
        _fields['name'] = target_list.val.fields[0].val
        _fields['alias'] = target_list.name
    return _fields


def a_expr_type(target_list):
    _fields = dict()
    _fields['type'] = 'AExpr'
    _fields['kind'] = target_list.kind
    if isinstance(target_list.lexpr, nodes.AExpr):
        _fields['lexpr'] = a_expr_type(target_list.lexpr)
    if isinstance(target_list.lexpr, nodes.ColumnRef):
        _fields['lexpr'] = target_list.lexpr.fields[0].val
    _fields['arithoper'] = target_list.name[0].val
    if isinstance(target_list.rexpr, nodes.AConst):
        _fields['rexpr'] = target_list.rexpr.val.ival
    else:
        _fields['rexpr'] = target_list.rexpr.fields[0].val
    return _fields


def func_call_type(target_list):
    _fields = dict()
    _fields['type'] = 'FuncCall'
    _args = []
    _fields['funcname'] = target_list.funcname[0].val
    for arguments in target_list.args:
        _args.append(arguments.fields[0].val)
    _fields['args'] = _args
    return _fields


if __name__ == '__main__':
    main()

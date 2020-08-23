import string

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
    # query_string = "select ka||level, colA+colB from ta where ka > (select ka||level from ta)"
    # query_string = "select colA from T2 where a < (select ka from ta) and  c > (select ka||level  from ta where x>2)"
    # query_string = "select colA from T2 where (select ka||level from ta where x>2)"
    # query_string = "select colA from T2 where NOT x > any (select colB from T2 where c>2)"
    # query_string = "select miAlias.colA + miAlias.colB from T2 as miAlias where X NOT IN (select colB from T2 where c>2)"
    # query_string = "select colA + colB from T2 where X NOT IN (select colB from T2 where c>2)"
    query_string = "select col1 from T1 where not exists (select col2 from T2 where T1.col1 < T2.col2 and c)"
    # query_string = "select colA from T2 as A where x <> all (select ka || level from T1 where a<2)"
    # query_string = "select colA from t1 where x not in (1,2,3,4)"
    # query_string = "select colA from T2 where a < (select a+b from ta where x > y)"
    # query_string = "select colA+colB from T2 where x > (select a||level from ta)"
    # query_string = "select colA  from t2 where not exists (select col from t where c and E.colA = col )"
    parsed_tree = parse(query_string)
    print(printer.serialize([parsed_tree[0]]))
    #equivalent = select_match_case_3(parsed_tree[0], None, None, parsed_tree[0])
    # analize_node(parsed_tree[0], None, None, parsed_tree[0])
    analize_node2(parsed_tree[0])
    for item in parsed_tree[0].equivalent:
        print(item)
    # for item in equivalent:
    #     print(item["info"])
    #     print(item["transformacion"])
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
    if case:
        case(statement, aux, transformations, node)


def analize_node2(node):
    case = get_case_for_node(node)
    if case:
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
                            save_change2(aux, node)
                            aux = copy.deepcopy(node)
            else:
                print("No cases found in target_list")
    if node.where_clause is not None:
        analize_node2(node.where_clause)
        for change in node.where_clause.equivalent:
            aux.where_clause = copy.deepcopy(change)
            save_change2(aux, node)


@node_analyzer(nodes.AExpr)
def a_expr(a_expr_node):
    aux = copy.deepcopy(a_expr_node)
    if a_expr_node.kind in (0, 6, 7, 10):
        where_simple(a_expr_node)
        if (isinstance(a_expr_node.lexpr, nodes.ColumnRef) or isinstance(a_expr_node.rexpr, nodes.ColumnRef)) and a_expr_node.kind == 0:
            print("COL comp COL")
    if isinstance(a_expr_node.lexpr, list):
        for position, item in enumerate(a_expr_node.lexpr):
            analize_node2(item)
            for change in item.equivalent:
                aux.lexpr[position] = copy.deepcopy(change)
                save_change2(aux, a_expr_node)
                aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.lexpr, nodes.Node):
        analize_node2(a_expr_node.lexpr)
        for change in a_expr_node.lexpr.equivalent:
            aux.lexpr = copy.deepcopy(change)
            save_change2(aux, a_expr_node)
            aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.rexpr, list):
        for position, item in enumerate(a_expr_node.rexpr):
            analize_node2(item)
            for change in item.equivalent:
                aux.rexpr[position] = copy.deepcopy(change)
                save_change2(aux, a_expr_node)
                aux = copy.deepcopy(a_expr_node)
    if isinstance(a_expr_node.rexpr, nodes.Node):
        analize_node2(a_expr_node.rexpr)
        for change in a_expr_node.rexpr.equivalent:
            aux.rexpr = copy.deepcopy(change)
            save_change2(aux, a_expr_node)
            aux = copy.deepcopy(a_expr_node)


@node_analyzer(nodes.BoolExpr)
def bool_expr(bool_expr_node):
    aux = copy.deepcopy(bool_expr_node)
    for position, arg in enumerate(bool_expr_node.args):
        analize_node2(arg)
        for change in arg.equivalent:
            aux.args[position] = copy.deepcopy(change)
            save_change2(aux, bool_expr_node)
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
    # equivalent = where_compuesto(sub_link_node)
    if sub_link_node.sub_link_type == 1:
        where_compuesto(sub_link_node)
        # save_change2(None, nodes.SubLink)
    analize_node2(sub_link_node.subselect)
    for change in sub_link_node.subselect.equivalent:
        aux.subselect = copy.deepcopy(change)
        save_change2(aux, sub_link_node)
        aux = copy.deepcopy(sub_link_node)
        # sub_link_node.equivalent.append("("+change+")")


"""SE USA UNA ESTRUCTURA AUXILIAR PARA REGRESAR EL ARBOL A SU ESADO ORIGINAL"""
# @node_analyzer(nodes.SelectStmt)
def select_match_case_3(statement, aux, transformations, node):
    aux = copy.deepcopy(node)
    transformations = list()
    if node.target_list is not None:
        for position, current_target in enumerate(node.target_list):
            if isinstance(current_target.val, nodes.AExpr):
                if current_target.val.name[0].val in ('+', '-', '*', '/', '||'):
                    detected_case = transform_a_expr_select(current_target.val)
                    aux.target_list[position] = detected_case
                    save_change(aux, statement, transformations, 'B1/B2')
            else:
                print("No cases found in target_list")
    from_info = get_from_tables(statement.from_clause)
    if node.where_clause is not None:
        # func = get_case_for_node(statement, aux, transformations, statement.where_clause)
        # func( statement.where_clause)
        analize_node(statement, aux, transformations, node.where_clause)
        for change in aux.where_clause.equivalent:
            aux.where_clause = change
            save_change(aux, statement, transformations, "")
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
            target_node.lexpr) + f"{target_node.name[0].val} COALESCE({'.'.join(c.str for c in target_node.rexpr.fields)},{identity_element})"

    else:
        equivalent = f"COALESCE({'.'.join(c.str for c in target_node.lexpr.fields)},{identity_element}) {target_node.name[0].val} COALESCE({'.'.join(c.str for c in target_node.rexpr.fields)},{identity_element})"
    target_node.equivalent.append(equivalent)
    #return equivalent


"""DEBERIA ENCARGARSE DE B3 B4 B5 B6 A1 A7 Y REVISAR EL NODO ENTERO LEXPR Y REXPR"""
# @node_analyzer(nodes.AExpr)
def a_expr_where(statement, aux, transformations, a_expr_node):
    if a_expr_node.kind in (0, 6, 7, 10):
        equiv = where_simple(a_expr_node)
        a_expr_node.equivalent.append(equiv)
    if isinstance(a_expr_node.lexpr, list):
        for item in a_expr_node.lexpr:
            analize_node(statement, aux, transformations, item)
    if isinstance(a_expr_node.lexpr, nodes.Node):
        analize_node(statement, aux, transformations, a_expr_node.lexpr)
    if isinstance(a_expr_node.rexpr, list):
        for item in a_expr_node.rexpr:
            analize_node(statement, aux, transformations, item)
    if isinstance(a_expr_node.rexpr, nodes.Node):
        analize_node(statement, aux, transformations, a_expr_node.rexpr)
        # save_change(aux, statement, transformations, 'B.3-B.6')
    # if isinstance(a_expr_node.rexpr, nodes.SubLink):
    #     equiv2 = where_other(a_expr_node)
    #     a_expr_node.equivalent.append(equiv2)
    #     # save_change(aux, statement, transformations, "A.7")
    #     detected_case = select_match_case_3(a_expr_node.rexpr.subselect)
    #     if detected_case:
    #         for item in detected_case:
    #             #print("SE DETECTO UNA TRANSFORMACION")
    #             #print(item)
    #             """OJO ESTÁ CABLEADO NO SIRVE"""
    #             aux.where_clause.args[0].rexpr = "("+item['transformacion']+")"
    #             save_change(aux, statement, transformations, "Subquery")


# @node_analyzer(nodes.BoolExpr)
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


# @node_analyzer(nodes.SubLink)
def sub_link_where(statement, aux, transformations, sub_link_node):
    # equivalent = where_compuesto(sub_link_node)
    if sub_link_node.sub_link_type == 1:
        aux.where_clause = where_compuesto(sub_link_node)
        save_change(aux, statement, transformations, "A.1/A.6")
    analize_node(statement, aux, transformations, sub_link_node.subselect)
    # detected_case = select_match_case_3(sub_link_node.subselect)
    # if detected_case:
    #     for item in detected_case:
    #         """ NO ES GENERICO, SE ESTA CREANDO UNA VARIABLE NUEVA LLAMADA SUBSELECT DONDE NO VA, NO EXISTE PARA ESE NODO"""
    #         sub_link_node.subselect = item['transformacion']
    #         save_change(aux, statement, transformations, "Subquery "+item['info'])


"""CASO A.4 Y A.5 Hay que usar las columnas externas e internas y ver el ALIAS"""
def get_from_tables(from_clause):
    tables = list()
    for column in from_clause:
        tables.append(column.relname)
    return tables


def save_change(aux, statement, transformations, info):
    serialized = printer.serialize([aux])
    #print("SE VA A GUARDAR:")
    print(serialized)
    transformations.append(dict(transformacion=serialized, info=info))
    aux.target_list = copy.deepcopy(statement.target_list)
    aux.where_clause = copy.deepcopy(statement.where_clause)


def save_change2(aux, node):
    serialized = printer.serialize([aux])
    # print(serialized)
    node.equivalent.append(serialized)


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
    current_node.equivalent.append("(" + equivalent + ")")
    #return "(" + equivalent + ")"


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
    current_node.equivalent.append("(" + equivalent + ")")
    # return "(" + equivalent + ")"


"""CASO A.7"""
def where_other(current_node):
    equivalent = ""
    subnode = current_node.rexpr
    subselect_str = node_to_str(subnode.subselect)
    testexpr = node_to_str(current_node.lexpr)
    oper_name = current_node.name[0].str
    neg_sign = negate_operator(oper_name)
    equivalent += f"{testexpr} IS NULL OR ({subselect_str}) IS NULL OR {testexpr} {oper_name} ({subselect_str})"
    current_node.equivalent.append("(" + equivalent + ")")
    # return "(" + equivalent + ")"


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
    # return "(" + equivalent + ")"
    current_node.equivalent.append("" + equivalent + "")
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
            # columns_ref.append('.'.join(c.str for c in subselect_where.lexpr.fields))
            columns_ref.append(subselect_where.lexpr.fields)
        if isinstance(subselect_where.rexpr, nodes.ColumnRef):
            # columns_ref.append('.'.join(c.str for c in subselect_where.rexpr.fields))
            columns_ref.append(subselect_where.rexpr.fields)
            subselect_statement.where_clause = None
    elif isinstance(subselect_where, nodes.BoolExpr) and subselect_where.boolop == 0:
        arg = subselect_where.args[0]
        oper = arg.name[0].str
        if isinstance(arg.lexpr, nodes.ColumnRef):
            # columns_ref.append('.'.join(c.str for c in arg.lexpr.fields))
            columns_ref.append(arg.lexpr.fields)
        if isinstance(arg.rexpr, nodes.ColumnRef):
            # columns_ref.append('.'.join(c.str for c in arg.rexpr.fields))
            columns_ref.append(arg.rexpr.fields)
        subselect_statement.where_clause = subselect_where.args[1]
    for column in columns_ref:
        if column[0].str not in internal_tables:
    # if [column[0].str for column in columns_ref if column[0].str not in internal_tables]:
            if oper == '=':
                equivalent = f"{column[1].str} NOT IN ({node_to_str(subselect_statement)})"
            else:
                equivalent = f"NOT {column[1].str} {oper} ANY ({node_to_str(subselect_statement)})"
                equivalent2 = f"{column[1].str} {negate_operator(oper)} ALL ({node_to_str(subselect_statement)})"
    current_node.equivalent.append("" + equivalent + "")


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

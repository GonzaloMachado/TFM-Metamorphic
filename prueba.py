from psqlparse import parse, nodes
from pglast import parse_sql, Node
from prueba_db import check_all_nullables_in_instance, check_nullable_column

import printer, prueba_db
import six

DEFINED_CASES = {}
"Registry of specialized printers."


# select SUBSTR("geeksforgeeks", 1, 5)  from persona as tabla1 , departamento where edad>35 and city="Paris"
# or sexo is not null
# select a from ta where x<= all(select y from tb)
# select colA from T2 as A where NOT EXISTS (SELECT * FROM T2 as B WHERE Colc='x' and B.colB>A.colB)
# select col1 + col2 from tabla1 where edad between 25 and 35

def main():
    """Sentencia que se recibe desde el FRONTEND"""
    query_string = "select a from ta where not x < any(select ka from tb)"
    print(query_string)
    """Probar que el statement sea valido en la BD (Ya incluye sintaxis)"""
    #prueba_db.check_statement(query_string)
    """Se obtiene el parsed tree"""
    parsed_tree = parse(query_string)
    """se limpia el arbol"""
    # allData = list()
    # for statement in parsed_tree:
    #     allData.append(clean_tree(statement))
    """Se buscan los casos y se hacen transformaciones"""
    # equivalent = select_match_case(allData[0])

    root = parse_sql('select a from ta where x < (select t.col from t where c)')
    #print(root)
    root2 = Node(root)
    #print(root2)
    myStruct2 = clean_tree2(parsed_tree[0])
    myStruct = clean_tree(parsed_tree[0])
    # propagate_nullable(root[0]['RawStmt']['stmt']['SelectStmt'])
    # propagate_nullable(parsed_tree[0])
    propagate_nullable(parsed_tree[0])
    #serialized = printer.serialize(parsed_tree)
    #equivalent2 = select_match_case_2(parsed_tree[0])
    # print(serialized)
    # other = parse(equivalent)
    print('done')


def clean_tree(statement):
    """Function to extract most important information from the parsed tree"""
    """Se puede mejorar usando decoradores, en vez de if/elif???????????"""
    statement_dict = dict()
    if statement.target_list:
        _fields = []
        for targetList in statement.target_list:
            if isinstance(targetList.val, nodes.ColumnRef):
                _fields.append(column_ref_type(targetList))
            elif isinstance(targetList.val, nodes.AExpr):
                _fields.append(a_expr_type(targetList.val))
            elif isinstance(targetList.val, nodes.FuncCall):
                _fields.append(func_call_type(targetList.val))
        statement_dict['select'] = _fields
    if statement.from_clause:
        _tables = range_var_type(statement.from_clause)
        statement_dict['from'] = _tables
    if statement.where_clause:
        # where_list = []
        if isinstance(statement.where_clause, nodes.SubLink):
            # print('Hay subquery')
            _subqueryinfo = {}
            statement_dict['where'] = statement.where_clause
            _subqueryinfo = clean_tree(statement.where_clause.subselect)
            statement_dict['subquery'] = _subqueryinfo
        # # print('No hay subquery')
        # elif isinstance(statement.where_clause, BoolExpr):
        #     # where_list['boolop'] = statement.where_clause.boolop
        #     if all([isinstance(argument, AExpr) for argument in statement.where_clause.args]):
        #         print("all aExpr")
        #         for args in statement.where_clause.args:
        #             where_list.append({statement.where_clause.boolop: a_expr_type(args)})
        else:
            statement_dict['where'] = statement.where_clause
        # _conditions = []
        # for condition in statement.where_clause.oper_name:
        #     _conditions.append(condition.str)
        # statement_dict['conditions'] = _conditions

    return statement_dict


def clean_tree2(statement):
    """Function to extract most important information from the parsed tree"""
    """Se puede mejorar usando decoradores, en vez de if/elif???????????"""
    # statement_dict = dict()
    # statement_dict['select'] = statement.target_list
    # statement_dict['from'] = statement.from_clause
    # statement_dict['where'] = statement.where_clause
    tree = list()
    tree.append(statement.target_list)
    tree.append(statement.from_clause)
    tree.append(statement.where_clause)
    return tree


def propagate_nullable(tree):
    results = list()
    i = 0
    nullable = None
    for attr in six.itervalues(tree.__dict__):
        if isinstance(attr, list):
            for item in attr:
                if isinstance(item, nodes.Node):
                    results.append(item.get_nullable_state())
        elif isinstance(attr, nodes.Node):
            results.append(attr.get_nullable_state())
    if any(results):
        tree.nullable = True

    nullable_results = None
    nullable_contents = None



def get_nullable_state(current_node, results):
    nullable = current_node.get_nullable_state()
    print(nullable)
    return nullable


def get_case_for_node(node):
    """Get specific case implementation for given `node` instance."""

    try:
        return DEFINED_CASES[type(node)]
    except KeyError:
        return None
        # raise NotImplementedError("Printer for node %r is not implemented yet"
        #                           % node.__class__.__name__)


def case_detector(node_class):
    """Decorator to change a specific case in sql statement"""

    def decorator(impl):
        assert printer.isclass(node_class)
        assert node_class not in DEFINED_CASES
        DEFINED_CASES[node_class] = impl
        return impl

    return decorator


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
                serialized = printer.serialize([statement])
                print(serialized)
            else:
                print("No cases found in target_list")
    if statement.where_clause is not None:
        """HAY QUE MEJORAR EL MATCH DEL CASO"""
        """Funcion que se encargue de los SubLink?"""
        if isinstance(statement.where_clause, nodes.BoolExpr) and isinstance(statement.where_clause.args[0], nodes.SubLink):
            where_compuesto_bool(statement.where_clause)
        elif isinstance(statement.where_clause, nodes.AExpr) and isinstance(statement.where_clause.rexpr, nodes.SubLink):
            statement.where_clause = where_other(statement.where_clause)
            print(printer.serialize([statement]))
            """Ya se cambió a STR *error*"""
            # select_match_case_2(statement.where_clause.rexpr.subselect)
        elif isinstance(statement.where_clause, nodes.SubLink):
            where_compuesto(statement.where_clause)
        else:
            """NO SE PUEDE SUSTITUIR T0D0 EL WHERE_CLAUSE"""
            statement.where_clause = where_simple(statement.where_clause)
            serialized = printer.serialize([statement])
            print(serialized)
            """HAY QUE GUARDAR EL CAMBIO"""
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
    return equivalent


def negate_operator(operator):
    defined_operators = ['<', '<=', '>', '>=', '=', '<>']
    negate_operators = ['>=', '>', '<=', '<', '<>', '=']
    index_search = defined_operators.index(operator)
    return negate_operators[index_search]


def print_statement(cleaned_tree):
    query = " FROM "
    first = True
    for tables in cleaned_tree['tables']:
        if first:
            first = False
        else:
            query += ', '
        query += f'{tables["relname"]} AS {tables["alias"]}' if tables["alias"] is not None else tables["relname"]
    if cleaned_tree['where'] is not None:
        query += " WHERE "
        if isinstance(cleaned_tree['where'], nodes.AExpr):
            query += print_a_expr(cleaned_tree['where'])
        elif isinstance(cleaned_tree['where'], nodes.BoolExpr):
            first = True
            for argument in cleaned_tree['where'].args:
                if first:
                    first = False
                else:
                    query += (' AND ', ' OR ')[cleaned_tree['where'].boolop]
                if isinstance(argument, nodes.AExpr):
                    query += print_a_expr(argument)
                elif isinstance(argument, nodes.BoolExpr):
                    query += print_bool_expr(argument)
                elif isinstance(argument, nodes.NullTest):
                    query += print_null_test(argument)
    else:
        print_statement(cleaned_tree['subquery'])
    return query


def print_a_expr(expression):
    # PUEDE FALTAR EL ATRIBUTO KIND
    query = ""
    if expression.kind == 0:
        query += f"{expression.lexpr.fields[0].val}{expression.name[0].val}"
    if isinstance(expression.rexpr, nodes.AConst):
        query += f"{expression.rexpr.val}"
    elif isinstance(expression.rexpr, nodes.ColumnRef):
        query += f"'{expression.rexpr.fields[0].val}'"
    return query


def print_bool_expr(expression):
    query = ""
    first = True
    for arg in expression.args:
        if first:
            first = False
        else:
            query += (' AND ', ' OR ')[expression.boolop]
        if isinstance(arg, nodes.AExpr):
            query += print_a_expr(arg)
    return query


def print_null_test(expression):
    query = f"{expression.arg.fields[0].val}"
    query += (' IS NULL ', ' IS NOT NULL ')[expression.nulltesttype]
    return query


def print_func_call(expression):
    query = ""
    query += f"{expression['funcname']}(" + ','.join([x for x in expression['args']]) + ")"
    return query


def caso_uno_cleaned(expression):
    """Funcion para sustituir el caso 1 en cleaned_tree"""
    # Elemento neutro de la operacion.
    if expression['arithoper'] == ('+' or '-'):
        if isinstance(expression['lexpr'], dict):
            equivalent_statement = caso_uno_cleaned(
                expression['lexpr']) + f" {expression['arithoper']} COALESCE({expression['rexpr']},0)"
        else:
            equivalent_statement = f"COALESCE({expression['lexpr']},0) {expression['arithoper']} COALESCE({expression['rexpr']},0)"
    else:
        if isinstance(expression['lexpr'], dict):
            equivalent_statement = caso_uno_cleaned(
                expression['lexpr']) + f" {expression['arithoper']} COALESCE({expression['rexpr']},1)"
        else:
            equivalent_statement = f"COALESCE({expression['lexpr']},1) {expression['arithoper']} COALESCE({expression['rexpr']},1)"
    return equivalent_statement


def caso_dos_cleaned(expression):
    """Funcion para sustituir el caso 2 en cleaned_tree"""
    #  PREGUNTAR EQUIVALENTE DE FUNCIONES
    if isinstance(expression['lexpr'], dict):
        equivalent_statement = caso_dos_cleaned(
            expression['lexpr']) + f" {expression['arithoper']} COALESCE({expression['rexpr']},'')"
    else:
        equivalent_statement = f"COALESCE({expression['lexpr']},'') {expression['arithoper']} COALESCE({expression['rexpr']},'')"
    return equivalent_statement


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

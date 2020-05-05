import psqlparse
from psqlparse.nodes.parsenodes import AStar, ColumnRef, AExpr, FuncCall, AConst
from psqlparse.nodes.primnodes import SubLink, BoolExpr, NullTest


# select SUBSTR("geeksforgeeks", 1, 5)  from persona as tabla1 , departamento where edad>35 and city="Paris" or sexo is not null
def main():
    query_string = ' select a from ta where x<= all(select y from tb)'
    print(query_string)
    statements = psqlparse.parse(query_string)
    allData = list()
    for statement in statements:
        allData.append(get_info(statement))
    equivalent = select_match_case(allData[0])
    # other = psqlparse.parse(equivalent)
    print('done')


def get_info(statement):
    statement_dict = dict()
    if statement.target_list:
        _fields = []
        for targetList in statement.target_list:
            if isinstance(targetList.val, ColumnRef):
                _fields.append(column_ref_type(targetList))
            elif isinstance(targetList.val, AExpr):
                _fields.append(a_expr_type(targetList.val))
            elif isinstance(targetList.val, FuncCall):
                _fields.append(func_call_type(targetList.val))
        statement_dict['fields'] = _fields
    if statement.from_clause:
        _tables = range_var_type(statement.from_clause)
        statement_dict['tables'] = _tables
    if statement.where_clause:
        # where_list = []
        if isinstance(statement.where_clause, SubLink):
            # print('Hay subquery')
            _subqueryinfo = {}
            statement_dict['where'] = statement.where_clause
            _subqueryinfo = get_info(statement.where_clause.subselect)
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


def select_match_case(statement):
    query = 'SELECT '
    first = True
    not_case_found = True
    for fields in statement['fields']:
        if first:
            first = False
        else:
            query += ', '
        if not_case_found:
            if fields['type'] == 'AStar':
                query += '*'
            if fields['type'] == 'ColumnRef':
                query += f"{fields['alias']}.{fields['name']} " if fields['alias'] is not None else fields['name']
            if fields['type'] == 'AExpr':
                query += caso_uno(fields)
                print("Caso #1")
                not_case_found = False
                # print(query)
            elif fields['type'] == 'FuncCall':
                print("Caso #2")
                not_case_found = False
                query += caso_dos(fields)
        else:
            if fields['type'] == 'FuncCall':
                query += print_func_call(fields)
            if fields['type'] == 'AExpr':
                query += print_a_expr(fields)
    query += print_statement(statement)
    print(query)
    return query


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
        if isinstance(cleaned_tree['where'], AExpr):
            query += print_a_expr(cleaned_tree['where'])
        elif isinstance(cleaned_tree['where'], BoolExpr):
            first = True
            for argument in cleaned_tree['where'].args:
                if first:
                    first = False
                else:
                    query += (' AND ', ' OR ')[cleaned_tree['where'].boolop]
                if isinstance(argument, AExpr):
                    query += print_a_expr(argument)
                elif isinstance(argument, BoolExpr):
                    query += print_bool_expr(argument)
                elif isinstance(argument, NullTest):
                    query += print_null_test(argument)
    else:
        print_statement(cleaned_tree['subquery'])
    return query


def print_a_expr(expression):
    # PUEDE FALTAR EL ATRIBUTO KIND
    query = ""
    if expression.kind == 0:
        query += f"{expression.lexpr.fields[0].val}{expression.name[0].val}"
    if isinstance(expression.rexpr, AConst):
        query += f"{expression.rexpr.val}"
    elif isinstance(expression.rexpr, ColumnRef):
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
        if isinstance(arg, AExpr):
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


def caso_uno(expression):
    if isinstance(expression['lexpr'], dict):
        equivalent_statement = caso_uno(
            expression['lexpr']) + f" {expression['arithoper']} COALESCE({expression['rexpr']},0)"
    else:
        equivalent_statement = f"COALESCE({expression['lexpr']},0) {expression['arithoper']} COALESCE({expression['rexpr']},0)"
    return equivalent_statement


def caso_dos(expression):
    # PREGUNTAR EQUIVALENTE DE FUNCIONES
    equivalent_statement = "aqui hay un caso 2"
    for arg in expression['args']:
        pass
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
    if isinstance(target_list.val.fields[0], AStar):
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
    if isinstance(target_list.lexpr, AExpr):
        _fields['lexpr'] = a_expr_type(target_list.lexpr)
    if isinstance(target_list.lexpr, ColumnRef):
        _fields['lexpr'] = target_list.lexpr.fields[0].val
    _fields['arithoper'] = target_list.name[0].val
    if isinstance(target_list.rexpr, AConst):
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

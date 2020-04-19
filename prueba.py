import psqlparse
from psqlparse.nodes.parsenodes import AStar, ColumnRef, AExpr, FuncCall
from psqlparse.nodes.primnodes import SubLink


def main():
    statements = psqlparse.parse(
        'select col1+col2  from persona as tabla1 , departamento where edad>35 and city="Paris" or sexo is not null')
    allData = list()
    for statement in statements:
        allData.append(get_info(statement))
    select_match_case(allData[0]['fields'])
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
        _tables = [range_var_type(statement.from_clause)]
        statement_dict['tables'] = _tables
    if statement.where_clause:
        _conditions = []
        for condition in statement.where_clause.oper_name:
            _conditions.append(condition.str)
        statement_dict['conditions'] = _conditions
    if isinstance(statement.where_clause, SubLink):
        print('Hay subquery')
        _subqueryinfo = {}
        _subqueryinfo = get_info(statement.where_clause.subselect)
        statement_dict['subquery'] = _subqueryinfo
        print('No hay subquery')
    return statement_dict


def select_match_case(select_data):
    for fields in select_data:
        data_type = fields['type']
        if data_type == 'AExpr':
            print("Caso #1")
        elif data_type == 'FuncCall':
            print("Caso #2")


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
        _fields['name'] = [str(x.val) for x in target_list.val.fields]
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

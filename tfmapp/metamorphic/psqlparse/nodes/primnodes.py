from .utils import build_from_item
from .nodes import Node


class RangeVar(Node):

    def __init__(self, obj):
        """
        Range variable, used in FROM clauses

        Also used to represent table names in utility statements; there,
        the alias field is not used, and inhOpt shows whether to apply the
        operation recursively to child tables.
        """
        super().__init__()
        self.catalogname = obj.get('catalogname')
        self.schemaname = obj.get('schemaname')
        self.relname = obj.get('relname')
        self.inh_opt = obj.get('inhOpt')
        self.relpersistence = obj.get('relpersistence')
        self.alias = build_from_item(obj, 'alias')
        self.location = obj['location']

    def __repr__(self):
        return '<RangeVar (%s)>' % self.relname

    def __str__(self):
        return '%s' % self.relname

    def tables(self):
        components = [
            getattr(self, name) for name in ('schemaname', 'relname')
            if getattr(self, name, None) is not None
        ]
        return {'.'.join(components)}

    def get_nullable_state(self):
        return self.nullable


class JoinExpr(Node):
    """
    For SQL JOIN expressions
    """

    def __init__(self, obj):
        self.jointype = obj.get('jointype')
        self.is_natural = obj.get('isNatural')
        self.larg = build_from_item(obj, 'larg')
        self.rarg = build_from_item(obj, 'rarg')
        self.using_clause = build_from_item(obj, 'usingClause')
        self.quals = build_from_item(obj, 'quals')
        self.alias = build_from_item(obj, 'alias')

    def __repr__(self):
        return '<JoinExpr type=%s>' % self.jointype

    def __str__(self):
        return '%s JOIN %s ON ()' % (self.larg, self.rarg)

    def tables(self):
        return self.larg.tables() | self.rarg.tables()


    def get_nullable_state(self):
        return list() 


class Alias(Node):

    def __init__(self, obj):
        self.aliasname = obj.get('aliasname')
        self.colnames = build_from_item(obj, 'colnames')

    def tables(self):
        return set()

    def get_nullable_state(self):
        return list() 


class IntoClause(Node):

    def __init__(self, obj):
        self._obj = obj


class Expr(Node):
    """
    Expr - generic superclass for executable-expression nodes
    """


class BoolExpr(Expr):

    def __init__(self, obj):
        super().__init__()
        self.boolop = obj.get('boolop')
        self.args = build_from_item(obj, 'args')
        self.location = obj.get('location')

    def tables(self):
        _tables = set()
        for item in self.args:
            _tables |= item.tables()
        return _tables


    def get_nullable_state(self):
        _nullables = list()
        for item in self.args:
            if isinstance(item, SubLink):
                item.get_nullable_state()
                item.nullable |= item.subselect.nullable_results
                _nullables.append(item.nullable)
            else:
                _nullables.append(item.get_nullable_state())
        if any(_nullables):
            self.nullable = True
        return self.nullable


class SubLink(Expr):

    def __init__(self, obj):
        super().__init__()
        self.sub_link_type = obj.get('subLinkType')
        self.sub_link_id = obj.get('subLinkId')
        self.testexpr = build_from_item(obj, 'testexpr')
        self.oper_name = build_from_item(obj, 'operName')
        self.subselect = build_from_item(obj, 'subselect')
        self.location = obj.get('location')

    def tables(self):
        return self.subselect.tables()


    def get_nullable_state(self):
        #_nullables = list()
        if self.testexpr:
            # _nullables.append(self.testexpr.get_nullable_state())
            # _nullable = self.testexpr.get_nullable_state()
            self.testexpr.get_nullable_state()
        # results, contents = self.subselect.get_nullable_state()
        self.subselect.get_nullable_state()
        """Type:Exists. Solo toma en cuenta el nullable contents"""
        if self.sub_link_type == 0:
            # self.nullable = self.subselect.nullable_contents
            self.nullable = self.subselect.nullable_contents
        """Type:Op-All, NOT IN Toma en cuenta results y contents"""
        if self.sub_link_type == 1:
            self.nullable = self.subselect.nullable_results | self.subselect.nullable_contents | self.testexpr.nullable
        """Type:Op-Any, IN Toma en cuenta contents"""
        if self.sub_link_type == 2:
            self.nullable =  self.subselect.nullable_contents | self.testexpr.nullable
        if self.sub_link_type == 4:
            self.nullable =  self.subselect.nullable_results
        return self.nullable


class SetToDefault(Node):

    def __init__(self, obj):
        self.type_id = obj.get('typeId')
        self.type_mod = obj.get('typeMod')
        self.collation = obj.get('collation')
        self.location = obj.get('location')


class CaseExpr(Node):

    def __init__(self, obj):
        self.casetype = obj.get('casetype')
        self.casecollid = obj.get('casecollid')
        self.arg = build_from_item(obj, 'arg')
        self.args = build_from_item(obj, 'args')
        self.defresult = build_from_item(obj, 'defresult')
        self.location = obj.get('location')


class CaseWhen(Node):

    def __init__(self, obj):
        self.expr = build_from_item(obj, 'expr')
        self.result = build_from_item(obj, 'result')
        self.location = obj.get('location')


class NullTest(Node):

    def __init__(self, obj):
        super().__init__()
        self.arg = build_from_item(obj, 'arg')
        self.nulltesttype = obj.get('nulltesttype')
        self.argisrow = obj.get('argisrow')
        self.location = obj.get('location')


class BooleanTest(Node):

    def __init__(self, obj):
        super().__init__()
        self.arg = build_from_item(obj, 'arg')
        self.booltesttype = obj.get('booltesttype')
        self.location = obj.get('location')


class RowExpr(Node):

    def __init__(self, obj):
        self.args = build_from_item(obj, 'args')
        self.colnames = build_from_item(obj, 'colnames')
        self.location = obj['location']
        self.row_format = obj.get('row_format')
        self.type_id = obj.get('typeId')

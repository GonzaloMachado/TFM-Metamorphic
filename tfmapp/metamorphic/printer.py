# -*- coding: utf-8 -*-
# :Project:   psqlparse -- Pretty Indent SQL
# :Created:   gio 27 lug 2017 08:39:28 CEST
# :Author:    Lele Gaifax <lele@metapensiero.it>
# :License:   BSD
# :Copyright: © 2017 Lele Gaifax
#


from contextlib import contextmanager
from inspect import isclass
from .psqlparse import nodes, parse

from six import PY2, StringIO, string_types


NODE_PRINTERS = {}
"Registry of specialized printers."


def get_printer_for_node(node):
    "Get specific printer implementation for given `node` instance."

    try:
        return NODE_PRINTERS[type(node)]
    except KeyError:
        raise NotImplementedError("Printer for node %r is not implemented yet"
                                  % node.__class__.__name__)


def node_printer(node_class):
    "Decorator to register a specific printer implementation for given `node_class`."

    def decorator(impl):
        assert isclass(node_class)
        assert node_class not in NODE_PRINTERS
        NODE_PRINTERS[node_class] = impl
        return impl

    return decorator


class Serializer(StringIO, object):
    """Basic SQL syntax tree serializer.
    :param separate_statements: a boolean, ``True`` by default, that tells whether multiple
                                statements shall be separated by an empty line
    This implement the basic machinery needed to serialize the syntax tree produced by
    :func:`~.parser.parse()` back to a textual representation, without any adornment.
    """

    def __init__(self, separate_statements=True):
        super(Serializer, self).__init__()
        self.separate_statements = separate_statements
        self.expression_level = 0

    if PY2:
        # Python 2/3 compatibility shim, as Python 2 version returns None
        def write(self, s):
            super(Serializer, self).write(s)
            return len(s)

    def newline_and_indent(self):
        "Emit a single whitespace, shall be overridden by the prettifier subclass."

        self.write(' ')

    def indent(self, amount=0):
        "Do nothing, shall be overridden by the prettifier subclass."

    def dedent(self):
        "Do nothing, shall be overridden by the prettifier subclass."

    @contextmanager
    def push_indent(self, amount=0):
        """Create a context manager that calls :meth:`indent` and :meth:`dedent` around a block
        of code.
        This is just an helper to simplify code that adjust the indentation level:
        .. code-block:: python
          with output.push_indent(4):
              # code that emits something with the new indentation
        """

        self.indent(amount)
        yield
        self.dedent()

    def print_node(self, node):
        "Lookup the specific printer for the given `node` and execute it."

        printer = get_printer_for_node(node)
        printer(node, self)

    def _print_list_items(self, items, sep, newline=True):
        first = True
        for item in items:
            if first:
                first = False
            else:
                if newline:
                    self.newline_and_indent()
                self.write(sep)
            self.print_node(item)

    def print_list(self, items, sep=', ', relative_indent=None, standalone_items=True):
        """Execute :meth:`print_node` on all the `items`, separating them with `sep`.
        :param items: a sequence of :class:`~.nodes.Node` instances
        :param sep: the separator between them
        :param relative_indent: if given, the relative amount of indentation to apply before
                                the first item, by default computed automatically from the
                                length of the separator `sep`
        :param standalone_items: a boolean that tells whether a newline will be emitted before
                                 each item
        """

        if relative_indent is None:
            relative_indent = -len(sep)
        with self.push_indent(relative_indent):
            self._print_list_items(items, sep, standalone_items)

    def print_expression(self, items, operator):
        """Emit a list of `items` between parens, using `operator` as separator.
        :param items: a sequence of expression operands
        :param operator: the operator between items
        """

        self.expression_level += 1
        if self.expression_level > 1:
            self.write('(')
        self._print_list_items(items, operator)
        self.expression_level -= 1
        if self.expression_level > 0:
            self.write(')')

    def __call__(self, sql):
        """Main entry point: execute :meth:`print_node` on each statement in `sql`.
        :param sql: either the source SQL in textual form, or a syntax tree produced by
                    :func:`~.parser.parse`
        :returns: a string with the equivalent SQL obtained by serializing the syntax tree
        """

        if isinstance(sql, string_types):
            sql = parse(sql)
        first = True
        for statement in sql:
            if first:
                first = False
            else:
                self.write(';')
                self.newline_and_indent()
                if self.separate_statements:
                    self.newline_and_indent()
            self.print_node(statement)
        return self.getvalue()


class PrettyPrinter(Serializer):
    """A serializer that emits a prettified representation of SQL.
    :param align_expression_operands: whether to vertically align the operands of an expression
    :param \*\*options: other options accepted by :class:`Serializer`
    """

    def __init__(self, align_expression_operands=True, **options):
        super(PrettyPrinter, self).__init__(**options)
        self.align_expression_operands = align_expression_operands
        self.column = 0
        self.current_indent = 0
        self.indentation_stack = []

    def write(self, s):
        """Write string `s` to the stream, adjusting the `column` accordingly, in particular
        setting it to 0 when `s` is a newline.
        Return the number of character written to the stream.
        """

        count = super(PrettyPrinter, self).write(s)
        if s == '\n':
            self.column = 0
        else:
            self.column += count
        return count

    def indent(self, amount=0):
        """Push current indentation level to the stack, then set it adding `amount` to the
        current `column`.
        """

        self.indentation_stack.append(self.current_indent)
        self.current_indent = self.column + amount

    def dedent(self):
        "Pop the indentation level from the stack and set `current_indent` to that."

        self.current_indent = self.indentation_stack.pop()

    def newline_and_indent(self):
        "Emit a newline followed by a number of whitespaces equal to the current indentation."

        self.write('\n')
        self.write(' ' * self.current_indent)

    def print_expression(self, items, operator):
        """Emit a list of `items` between parens, using `operator` as separator.
        :param items: a sequence of expression operands
        :param operator: the operator between items
        If `align_expression_operands` is ``True`` then the operands will be vertically
        aligned.
        """

        self.expression_level += 1
        if self.expression_level > 1:
            if self.align_expression_operands:
                oplen = len(operator)
                self.write('(' + ' ' * oplen)
                indent = -oplen
            else:
                self.write('(')
                indent = 0
        else:
            indent = -len(operator)

        with self.push_indent(indent):
            self._print_list_items(items, operator)

        self.expression_level -= 1
        if self.expression_level > 0:
            self.write(')')


def format(sql, **options):
    """Reformat given `sql` into a pretty representation.
    :param sql: either the source SQL in textual form, or a syntax tree produced by
                :func:`~.parser.parse`
    :param \*\*options: any keyword argument accepted by :class:`PrettyPrinter`
    :returns: a string with the equivalent SQL obtained by serializing the syntax tree
    """

    printer = PrettyPrinter(**options)
    return printer(sql)


def serialize(sql, **options):
    """Serialize given `sql` into a pretty representation.
    :param sql: either the source SQL in textual form, or a syntax tree produced by
                :func:`~.parser.parse`
    :param \*\*options: any keyword argument accepted by :class:`Serializer`
    :returns: a string with the equivalent SQL obtained by serializing the syntax tree
    """

    printer = Serializer(**options)
    return printer(sql)


##
## Specific Node printers, please keep them in alphabetic order
##

@node_printer(nodes.AArrayExpr)
def a_array_expr(node, output):
    output.write('ARRAY[')
    output.print_list(node.elements)
    output.write(']')


@node_printer(nodes.AConst)
def a_const(node, output):
    output.print_node(node.val)


@node_printer(nodes.AExpr)
def a_expr(node, output):
    if node.kind == 0:
        output.print_node(node.lexpr)
        for operator in node.name:
            output.write(' ')
            output.write(operator.str)
        output.write(' ')
        output.print_node(node.rexpr)
    elif node.kind == 6:
        output.print_node(node.lexpr)
        if node.name[0].str == '<>':
            output.write(' NOT')
        output.write(' IN (')
        output.print_expression(node.rexpr, ',')
        output.write(')')
    elif node.kind == 7:
        output.print_node(node.lexpr)
        if node.name[0].str == '!~~':
            output.write(' NOT')
        output.write(' LIKE ')
        output.print_node(node.rexpr)
    elif node.kind == 10 or node.kind == 11:
        output.print_node(node.lexpr)
        output.write(' ')
        # Debe separarse el kind si se quiere imprimir acá directamente en vez del valor de .str
        output.write(node.name[0].str)
        output.write(' ')
        output.print_expression(node.rexpr, 'AND ')






@node_printer(nodes.AIndices)
def a_indices(node, output):
    output.write('[')
    is_slice = node.is_slice
    if is_slice is None:
        # PG < 9.6
        is_slice = node.lidx is not None and node.uidx is not None
    if is_slice:
        if node.lidx is not None:
            output.print_node(node.lidx)
        output.write(':')
        if node.uidx is not None:
            output.print_node(node.uidx)
    else:
        output.print_node(node.uidx)
    output.write(']')


@node_printer(nodes.Alias)
def alias(node, output):
    output.write(node.aliasname)
    if node.colnames is not None:
        output.write(' (  ')
        output.print_list(node.colnames)
        output.write(')')


@node_printer(nodes.BoolExpr)
def bool_expr(node, output):
    if node.boolop == 2:
        output.write('NOT ')
        output.print_node(node.args[0])
    else:
        operator = ('AND ', 'OR ', 'NOT ')[node.boolop]
        output.print_expression(node.args, operator)


@node_printer(nodes.CaseExpr)
def case_expr(node, output):
    with output.push_indent():
        output.write('CASE')
        if node.arg is not None:
            output.write(' ')
            output.print_node(node.arg)
        output.newline_and_indent()
        output.write('  ')
        with output.push_indent():
            output.print_list(node.args, '')
            if node.def_result is not None:
                output.newline_and_indent()
                output.write('ELSE ')
                output.print_node(node.def_result)
        output.newline_and_indent()
        output.write('END')


@node_printer(nodes.CaseWhen)
def case_when(node, output):
    output.write('WHEN ')
    with output.push_indent(-3):
        output.print_node(node.expr)
        output.newline_and_indent()
        output.write('THEN ')
        output.print_node(node.result)


@node_printer(nodes.ColumnRef)
def column_ref(node, output):
    output.write('.'.join('*' if isinstance(c, nodes.AStar) else c.str
                          for c in node.fields))


@node_printer(nodes.CommonTableExpr)
def common_table_expr(node, output):
    output.print_node(node.ctename)
    if node.aliascolnames is not None:
        output.write('(')
        if len(node.aliascolnames) > 1:
            output.write('  ')
        output.print_list(node.aliascolnames)
        output.write(')')
        output.newline_and_indent()
    else:
        output.write(' ')
    output.write('AS (')
    output.print_node(node.ctequery)
    output.write(')')
    output.newline_and_indent()


@node_printer(nodes.DeleteStmt)
def delete_stmt(node, output):
    with output.push_indent():
        if node.with_clause is not None:
            output.write('WITH ')
            output.print_node(node.with_clause)
            output.newline_and_indent()
            output.write('  ')
            output.indent()

        output.write('DELETE FROM ')
        output.print_node(node.relation)
        if node.using_clause is not None:
            output.newline_and_indent()
            output.write('USING ')
            output.print_list(node.using_clause)
        if node.where_clause is not None:
            output.newline_and_indent()
            output.write('WHERE ')
            output.print_node(node.where_clause)
        if node.returning_list is not None:
            output.newline_and_indent()
            output.write('RETURNING ')
            output.print_list(node.returning_list)

        if node.with_clause is not None:
            output.dedent()


@node_printer(nodes.Float)
def float(node, output):
    output.write(str(node))


@node_printer(nodes.FuncCall)
def func_call(node, output):
    output.write('.'.join(n.str for n in node.funcname))
    output.write('(')
    if node.agg_distinct:
        output.write('DISTINCT ')
    if node.args is None:
        if node.agg_star:
            output.write('*')
    else:
        if len(node.args) > 1:
            output.write('  ')
        output.print_list(node.args)
    if node.agg_order is not None:
        if node.agg_within_group is None:
            output.write(' ORDER BY ')
            output.print_list(node.agg_order)
        else:
            output.write(') WITHIN GROUP (ORDER BY ')
            output.print_list(node.agg_order)
    output.write(')')
    if node.agg_filter is not None:
        output.write(' FILTER (WHERE ')
        output.print_node(node.agg_filter)
        output.write(')')
    if node.over is not None:
        output.write(' OVER ')
        output.print_node(node.over)


@node_printer(nodes.Integer)
def integer(node, output):
    output.write(str(node))


@node_printer(nodes.InsertStmt)
def insert_stmt(node, output):
    with output.push_indent():
        if node.with_clause is not None:
            output.write('WITH ')
            output.print_node(node.with_clause)
            output.newline_and_indent()
            output.write('  ')
            output.indent()

        output.write('INSERT INTO ')
        output.print_node(node.relation)
        if node.cols is not None:
            output.write(' (  ')
            output.print_list(node.cols)
            output.write(')')
            output.newline_and_indent()
        else:
            output.write(' ')
        if node.select_stmt is not None:
            output.newline_and_indent()
            output.write('  ')
            output.print_node(node.select_stmt)
        else:
            output.write('DEFAULT VALUES')
        if node.on_conflict_clause is not None:
            output.newline_and_indent()
            output.write('ON CONFLICT ')
            output.print_list(node.on_conflict_clause)
        if node.returning_list is not None:
            output.newline_and_indent()
            output.write('RETURNING ')
            output.print_list(node.returning_list)

        if node.with_clause is not None:
            output.dedent()


@node_printer(nodes.JoinExpr)
def join_expr(node, output):
    with output.push_indent(-3):
        output.print_node(node.larg)
        output.newline_and_indent()
        if node.is_natural:
            output.write('NATURAL ')
        output.write(('INNER', 'LEFT', 'FULL', 'RIGHT')[node.jointype])
        output.write(' JOIN ')
        output.print_node(node.rarg)
        if node.using_clause is not None:
            output.write(' USING (')
            output.print_list(node.using_clause)
            output.write(')')
        elif node.quals is not None:
            output.write(' ON ')
            output.print_node(node.quals)
        if node.alias is not None:
            output.write(' AS ')
            output.print_node(node.alias)


# @node_printer(nodes.Literal)
# def literal(node, output):
#     name = node.str
#     if name == '~~':
#         name = 'LIKE'
#     output.write(name)


@node_printer(nodes.LockingClause)
def locking_clause(node, output):
    output.write((None,
                  'KEY SHARE',
                  'SHARE',
                  'NO KEY UPDATE',
                  'UPDATE')[node.strength])
    if node.locked_rels is not None:
        output.write(' OF ')
        output.print_list(node.locked_rels)
    if node.wait_policy:
        output.write(' ')
        output.write((None, 'SKIP LOCKED', 'NOWAIT')[node.wait_policy])


@node_printer(nodes.MultiAssignRef)
def multi_assign_ref(node, output):
    output.print_node(node.source)


# @node_printer(nodes.Name)
# def name(node, output):
#     output.write(str(node))


@node_printer(nodes.NullTest)
def null_test(node, output):
    output.print_node(node.arg)
    output.write(' IS')
    output.write((' NULL', ' NOT NULL')[node.nulltesttype])


@node_printer(nodes.RangeFunction)
def range_function(node, output):
    if node.lateral:
        output.write('LATERAL ')
    for fun, cdefs in node.functions:
        output.print_node(fun)
        if cdefs is not None:
            output.write(' AS ')
            output.print_list(cdefs)
    if node.alias is not None:
        output.write(' AS ')
        output.print_node(node.alias)
    if node.ordinality:
        output.write(' WITH ORDINALITY')


@node_printer(nodes.RangeSubselect)
def range_subselect(node, output):
    if node.lateral:
        output.write('LATERAL ')
    output.print_node(node.subquery)
    if node.alias is not None:
        output.write(' AS ')
        output.print_node(node.alias)


@node_printer(nodes.RangeVar)
def range_var(node, output):
    if node.schemaname:
        output.write(node.schemaname)
        output.write('.')
    output.write(node.relname)
    _alias = node.alias
    if _alias:
        output.write(' AS ')
        output.print_node(_alias)


@node_printer(nodes.ResTarget)
def res_target(node, output):
    if node.val is not None:
        output.print_node(node.val)
        if node.name is not None:
            output.write(' AS ')
            output.print_node(node.name)
    else:
        output.print_node(node.name)
    if node.indirection:
        output.print_list(node.indirection, '', standalone_items=False)


@node_printer(nodes.SelectStmt)
def select_stmt(node, output):
    with output.push_indent():
        if node.with_clause is not None:
            output.write('WITH ')
            output.print_node(node.with_clause)
            output.newline_and_indent()
            output.write('  ')
            output.indent()

        if node.values_lists is not None:
            # Is this a SELECT ... FROM (VALUES (...))?
            require_parens = getattr(node.values_lists[0][0], '_add_outer_parens', False)
            if require_parens:
                output.write('(')
            output.write('VALUES (  ')
            with output.push_indent(-5):
                first = True
                for values in node.values_lists:
                    if first:
                        first = False
                    else:
                        output.newline_and_indent()
                        output.write(', (  ')
                    output.print_list(values)
                    output.write(')')
            if require_parens:
                output.write(')')
        elif node.target_list is None:
            with output.push_indent():
                output.print_node(node.larg)
                output.newline_and_indent()
                output.newline_and_indent()
                output.write((None, 'UNION', 'INTERSECT', 'EXCEPT')[node.op])
                if node.all:
                    output.write(' ALL')
                output.newline_and_indent()
                output.newline_and_indent()
                output.print_node(node.rarg)
        else:
            output.write('SELECT')
            if node.distinct_clause:
                output.write(' DISTINCT')
                if node.distinct_clause[0]:
                    output.write(' ON (')
                    output.print_list(node.distinct_clause)
                    output.write(')')
            output.write(' ')
            output.print_list(node.target_list)
            if node.from_clause is not None:
                # Add a recognizable marker to distinguish the
                # SELECT ... FROM (VALUES (...)) case from the
                # INSERT INTO ... VALUES (...)
                for clause in node.from_clause:
                    if (isinstance(clause, nodes.RangeSubselect)
                            and clause.subquery.values_lists is not None):
                        clause.subquery.values_lists[0][0]._add_outer_parens = True
                output.newline_and_indent()
                output.write('FROM ')
                output.print_list(node.from_clause)
            if node.where_clause is not None:
                output.newline_and_indent()
                output.write('WHERE ')
                output.print_node(node.where_clause)
            if node.group_clause is not None:
                output.newline_and_indent()
                output.write('GROUP BY ')
                output.print_list(node.group_clause)
            if node.having_clause is not None:
                output.newline_and_indent()
                output.write('HAVING ')
                output.print_node(node.having_clause)
            if node.window_clause is not None:
                output.newline_and_indent()
                output.write('WINDOW ')
                output.print_list(node.window_clause)
            if node.sort_clause is not None:
                output.newline_and_indent()
                output.write('ORDER BY ')
                output.print_list(node.sort_clause)
            if node.limit_count is not None:
                output.newline_and_indent()
                output.write('LIMIT ')
                output.print_node(node.limit_count)
            if node.limit_offset is not None:
                output.newline_and_indent()
                output.write('OFFSET ')
                output.print_node(node.limit_offset)
            if node.locking_clause is not None:
                output.newline_and_indent()
                output.write('FOR ')
                output.print_list(node.locking_clause)

        if node.with_clause is not None:
            output.dedent()


@node_printer(nodes.SetToDefault)
def set_to_default(node, output):
    output.write('DEFAULT')


# @node_printer(nodes.SortBy)
# def sort_by(node, output):
#     output.print_node(node.node)
#     if node.dir == nodes.SortBy.DIR_ASC:
#         output.write(' ASC')
#     elif node.dir == nodes.SortBy.DIR_DESC:
#         output.write(' DESC')
#     elif node.dir == nodes.SortBy.DIR_USING:
#         output.write(' USING ')
#         output.print_list(node.using)
#     if node.nulls:
#         output.write(' NULLS ')
#         output.write('FIRST' if node.nulls == nodes.SortBy.NULLS_FIRST else 'LAST')


@node_printer(nodes.String)
def string(node, output):
    output.write("'%s'" % node)


@node_printer(nodes.SubLink)
def sub_link(node, output):
    if node.testexpr is not None:
        output.print_node(node.testexpr)
    if node.oper_name is not None:
        for operator in node.oper_name:
            output.write(' ')
            output.write(operator.str)
            output.write((' EXISTS ', ' ALL ', ' ANY ', '', '')[node.sub_link_type])
    else:
        output.write((' EXISTS ', ' ALL ', ' IN ', '', '')[node.sub_link_type])
    # output.write(' ')
    output.write('(')
    with output.push_indent():
        output.print_node(node.subselect)
    output.write(')')


_common_values = {
    't::pg_catalog.bool': 'TRUE',
    'f::pg_catalog.bool': 'FALSE',
    'now::pg_catalog.text::pg_catalog.date': 'CURRENT_DATE',
}


@node_printer(nodes.TypeCast)
def type_cast(node, output):
    # Replace common values
    if isinstance(node.arg, nodes.TypeCast):
        if isinstance(node.arg.arg, nodes.AConst):
            value = '%s::%s::%s' % (
                node.arg.arg.val,
                ('.'.join(str(n) for n in node.arg.type_name.names)),
                ('.'.join(str(n) for n in node.type_name.names)))
            if value in _common_values:
                output.write(_common_values[value])
                return
    elif isinstance(node.arg, nodes.AConst):
        value = '%s::%s' % (
            node.arg.val,
            ('.'.join(str(n) for n in node.type_name.names)))
        if value in _common_values:
            output.write(_common_values[value])
            return
    output.print_node(node.arg)
    output.write('::')
    output.print_node(node.type_name)


@node_printer(nodes.TypeName)
def type_name(node, output):
    names = node.names
    output.write('.'.join(str(n) for n in names))


@node_printer(nodes.UpdateStmt)
def update_stmt(node, output):
    with output.push_indent():
        if node.with_clause is not None:
            output.write('WITH ')
            output.print_node(node.with_clause)
            output.newline_and_indent()
            output.write('  ')
            output.indent()

        output.write('UPDATE ')
        output.print_node(node.relation)
        output.newline_and_indent()
        output.write('SET ')
        output.print_list(node.target_list)
        if node.from_clause is not None:
            output.newline_and_indent()
            output.write('FROM ')
            output.print_list(node.from_clause)
        if node.where_clause is not None:
            output.newline_and_indent()
            output.write('WHERE ')
            output.print_node(node.where_clause)
        if node.returning_list is not None:
            output.newline_and_indent()
            output.write('RETURNING ')
            output.print_list(node.returning_list)

        if node.with_clause is not None:
            output.dedent()


@node_printer(nodes.WindowDef)
def window_def(node, output):
    empty = node.partition_clause is None and node.order_clause is None
    if node.name is not None:
        output.print_node(node.name)
        if not empty:
            output.write(' AS ')
    if not empty or node.name is None:
        output.write('(')
        with output.push_indent():
            if node.partition_clause is not None:
                output.write('PARTITION BY ')
                output.print_list(node.partition_clause)
            if node.order_clause is not None:
                if node.partition_clause is not None:
                    output.newline_and_indent()
                output.write('ORDER BY ')
                output.print_list(node.order_clause)
        output.write(')')


@node_printer(nodes.WithClause)
def with_clause(node, output):
    relindent = -3
    if node.recursive:
        relindent -= output.write('RECURSIVE ')
    output.print_list(node.ctes, relative_indent=relindent)


@node_printer(list)
def list_type(node, output):
    output.print_list(node, 'AND ', True)
    # output.print_list(node)


@node_printer(str)
def str_type(node, output):
    output.write(node)


@node_printer(dict)
def dict_type(node, output):
    for item, value in node.items():
        if item == 'CoalesceExpr':
            output.write('COALESCE(')
            output.print_node(value["args"][0]["ColumnRef"]["fields"][0]["String"]["str"])
            output.write(',')
            if value["args"][1]["A_Const"]["val"] == 'integer':
                output.write(str(value["args"][1]["A_Const"]["val"]["integer"]["ival"]))
            else:
                output.write("''")
            output.write(')')

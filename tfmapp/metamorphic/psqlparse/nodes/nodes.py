import six


class Node(object):

    def __init__(self):
        self.nullable = False


    def tables(self):
        """
        Generic method that does a depth-first search on the node attributes.

        Child classes should override this method for better performance.
        """
        _tables = set()

        for attr in six.itervalues(self.__dict__):
            if isinstance(attr, list):
                for item in attr:
                    if isinstance(item, Node):
                        _tables |= item.tables()
            elif isinstance(attr, Node):
                _tables |= attr.tables()

        return _tables


    def get_nullable_state(self):

        _nullables = list()

        for attr in six.itervalues(self.__dict__):
            if isinstance(attr, list):
                for item in attr:
                    if isinstance(item, Node):
                        _nullables.append(item.get_nullable_state())
            elif isinstance(attr, Node):
                _nullables.append(attr.get_nullable_state())

        return _nullables
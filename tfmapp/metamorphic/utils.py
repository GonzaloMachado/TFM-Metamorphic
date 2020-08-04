from .psqlparse import parse, nodes
from .db_utils import get_connection_data, db_connection

def parse_query(query):
	connection_data = get_connection_data(query.instance)
	connection = db_connection(connection_data)
	parsed_tree = parse(query.query_text)
	parsed_tree[0].get_nullable_state(query)
	response = parsed_tree[0].nullable
	return response




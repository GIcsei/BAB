import json
import re

from app.core.firestore_handler.Utils import parse_to_firestore


class FirestoreQueryBuilder:
    OPERATOR_MAP = {
        "==": "EQUAL",
        "!=": "NOT_EQUAL",
        ">": "GREATER_THAN",
        ">=": "GREATER_THAN_OR_EQUAL",
        "<": "LESS_THAN",
        "<=": "LESS_THAN_OR_EQUAL",
    }

    def __init__(self, collection):
        self.collection = collection

    def _parse_condition(self, condition: str):
        match = re.match(r"(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)", condition.strip())
        if not match:
            raise ValueError(f"Invalid condition format: {condition}")
        field, op, value = match.groups()
        return {
            "fieldFilter": {
                "field": {"fieldPath": field},
                "op": self.OPERATOR_MAP[op],
                "value": parse_to_firestore(value),
            }
        }

    def _tokenize(self, filter_string: str):
        # Tokenizer to preserve parentheses and split by logical operators
        # Match everything: conditions, AND, OR, and parentheses
        token_pattern = r"(\s+AND\s+|\s+OR\s+|\(|\))"
        tokens = re.split(token_pattern, filter_string)

        # Clean up any leading/trailing spaces from tokens and remove empty tokens
        tokens = [token.strip() for token in tokens if token.strip()]
        return tokens

    def _parse_expression(self, tokens):
        def parse(tokens):
            stack = []
            while tokens:
                token = tokens.pop(0)
                if token == "(":
                    stack.append(parse(tokens))
                elif token == ")":
                    break
                elif token in ("AND", "OR"):
                    stack.append(token)
                else:
                    stack.append(self._parse_condition(token))

            # Convert flat expression into nested structure
            while "OR" in stack or "AND" in stack:
                for i, token in enumerate(stack):
                    if token in ("AND", "OR"):
                        left = stack[i - 1]
                        right = stack[i + 1]
                        combined = {
                            "compositeFilter": {"op": token, "filters": [left, right]}
                        }
                        stack[i - 1 : i + 2] = [combined]
                        break
            return stack[0]

        return parse(tokens)

    def build_query(self, filter_string):
        if not filter_string:
            raise ValueError("Filter string is empty")

        tokens = self._tokenize(filter_string)
        where_clause = self._parse_expression(tokens)

        return {
            "structuredQuery": {
                "from": [{"collectionId": self.collection}],
                "where": where_clause,
            }
        }


# Example usage:
if __name__ == "__main__":
    builder = FirestoreQueryBuilder("messages")

    query = builder.build_query(
        "(status == 'sent' AND priority > 2) OR (archived == true AND owner == 'admin')"
    )

    print(json.dumps(query, indent=2))

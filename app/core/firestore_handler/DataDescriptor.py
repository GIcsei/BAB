from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    name: str
    created: str
    updated: str
    data_fields: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        field_preview = "\n\t\t".join(
            f"{k}={repr(v)}" for k, v in (self.data_fields or {}).items()
        )
        if len(field_preview) > 300:
            field_preview = field_preview[:297] + "..."

        return (
            f"Document: {self.name}\n"
            f"\tcreated: {self.created}\n"
            f"\tupdated: {self.updated}\n"
            f"\tfields: \n\t\t{field_preview}\n\t"
        )

    def __repr__(self) -> str:
        # shorter, single-line representation for debugging
        field_preview = ", ".join(
            f"{k}={repr(v)}" for k, v in (self.data_fields or {}).items()
        )
        if len(field_preview) > 60:
            field_preview = field_preview[:57] + "..."
        return f"Document(name='{self.name}', created='{self.created}', updated='{self.updated}', fields={{ {field_preview} }})"

    @staticmethod
    def from_dict(input_dict: dict):
        if not isinstance(input_dict, dict):
            raise ValueError("Input must be a dictionary")

        # Support wrapped format {"document": {...}} or bare document dict
        dictionary = input_dict.get("document", input_dict)

        required_keys = {"name", "createTime", "updateTime"}
        if not required_keys.issubset(set(dictionary.keys())):
            raise ValueError(
                "Given dictionary cannot be used as a document entry: missing required keys"
            )

        name = dictionary["name"].split("/")[-1]
        created = dictionary["createTime"]
        updated = dictionary["updateTime"]

        datafields = None
        if dictionary.get("fields"):
            datafields = {
                key: Document.convert_firefield(value)
                for key, value in dictionary["fields"].items()
            }

        return Document(name, created, updated, datafields)

    @staticmethod
    def convert_firefield(fire_field: dict):
        if not isinstance(fire_field, dict) or len(fire_field) != 1:
            raise ValueError("Given value is not a field!")

        key, value = next(iter(fire_field.items()))
        type_casts = {
            "stringValue": str,
            "integerValue": int,
            "doubleValue": float,
            "booleanValue": lambda v: (
                v.lower() == "true" if isinstance(v, str) else bool(v)
            ),
            "nullValue": lambda v: None,
        }

        caster = type_casts.get(key)
        if caster is None:
            raise ValueError(f"Unsupported value type: {key}")

        return caster(value)


class Collection:
    def __init__(self, name: str, docs: Optional[List[Document]] = None):
        if name is None:
            raise ValueError("Name cannot be None!")
        self.documents: List[Document] = []
        self.name = name
        if docs:
            self.documents = docs

    def add_doc(self, doc: Document):
        self.documents.append(doc)

    def sort_by(self, field: str, reverse: bool = True):
        def sort_key(doc: Document):
            return (
                doc.data_fields.get(field)
                if (doc.data_fields and (field in doc.data_fields))
                else None
            )

        self.documents = sorted(self.documents, key=sort_key, reverse=reverse)
        return self

    def update_elems(self, elemnum=None):
        """
        Narrow or pick elements from the collection.
        - If elemnum is int: keep only the element at that index (wrapped in list).
        - If elemnum is slice: apply slice to documents.
        - If elemnum is list/tuple of ints: select those indices.
        - If elemnum is None: no-op.
        """
        if elemnum is None:
            return self

        if isinstance(elemnum, int):
            # keep single element as a list (preserve documents type)
            try:
                self.documents = [self.documents[elemnum]]
            except IndexError:
                self.documents = []
            return self

        if isinstance(elemnum, slice):
            self.documents = self.documents[elemnum]
            return self

        if isinstance(elemnum, (list, tuple)):
            selected = []
            for i in elemnum:
                if not isinstance(i, int):
                    raise TypeError("Indices must be integers")
                if 0 <= i < len(self.documents):
                    selected.append(self.documents[i])
            self.documents = selected
            return self

        raise TypeError("Unsupported elemnum type for update_elems")

    @staticmethod
    def from_list(name: str, list_of_docs):
        new_docs = [Document.from_dict(elem) for elem in list_of_docs]
        return Collection(name, new_docs)

    def __repr__(self):
        doc_ids = [doc.name.split("/")[-1] for doc in self.documents]
        return f"Collection({len(self.documents)} documents: {', '.join(doc_ids[:5])}{'...' if len(doc_ids) > 5 else ''})"

    def __str__(self):
        output = [f"Collection with {len(self.documents)} document(s):"]
        for doc in self.documents:
            output.append(str(doc))  # uses Document.__str__()
        return "\n\n".join(output)

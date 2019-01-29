#!/usr/bin/env python3
# coding: utf8
from datetime import datetime
from typing import Mapping, Any, List, ClassVar, TypeVar, Type

from . import Utils
import logging

log = logging.getLogger(__name__)

# this allows self reference to this class in its factory methods
DB = TypeVar('DB', bound='DBRow')


class DbRow:
    """
    base class for classes representing a row in the database to allow easy
    generation of queries and an easy interface for callers e.g.
        q = "INSERT INTO SyncFiles ({0}) VALUES ({1})".format(
            self.SyncRow.columns, self.SyncRow.params)
        self.cur.execute(q, row.dict)

    Class Attributes:
        cols_def: keys are names of columns and items are their type
        no_update: list of columns that are not for UPDATE (i.e primary key)
        columns: string to substitute into SELECT {} or INSERT INTO <table> ({})
        params: a string to insert after VALUES in a sql INSERT or UPDATE
        update: a string to substitute into 'UPDATE <table> Set {0}'
        empty: True for an empty row
        dict: a dictionary of the above attributes

        The remaining attributes are on a per subclass basis and are
        generated from row_def by the db_row decorator
    """
    cols_def: ClassVar[Mapping[str, Type]] = None
    no_update: ClassVar[List[str]] = []
    columns: ClassVar[str] = None
    params: ClassVar[str] = None
    update: ClassVar[str] = None
    dict: ClassVar[dict] = None
    empty: ClassVar[bool] = False

    def __init__(self):
        pass

    # empty row object = boolean False
    def __bool__(self) -> bool:
        return not self.empty

    # factory method for delivering a DbRow class based on named arguments
    @classmethod
    def make(cls, **k_args: Any) -> DB:
        new_row_class = cls()
        for key, value in k_args.items():
            if not hasattr(new_row_class, key):
                raise ValueError("{0} does not have column {1}".format(
                    cls, key))
            setattr(new_row_class, key, value)
        new_row_class.empty = False
        return new_row_class

    @classmethod
    def db_row(cls, row_class: DB) -> DB:
        """
        class decorator function to create RowClass classes that represent a row
        in the database

        :param (DbRow) row_class: the class to decorate
        :return (DbRow): the decorated class
        """
        row_class.columns = ','.join(row_class.cols_def.keys())
        row_class.params = ':' + ',:'.join(row_class.cols_def.keys())
        row_class.update = ','.join('{0}=:{0}'.format(col) for
                                    col in row_class.cols_def.keys() if
                                    col not in row_class.no_update)

        def init(self, result_row=None):
            for col, col_type in self.cols_def.items():
                if not result_row:
                    value = None
                elif col_type == datetime:
                    value = Utils.string_to_date(result_row[col])
                else:
                    value = result_row[col]
                setattr(self, col, value)
            if not result_row:
                self.empty = True

        @property
        def to_dict(self):
            return self.__dict__

        row_class.__init__ = init
        row_class.dict = to_dict
        return row_class

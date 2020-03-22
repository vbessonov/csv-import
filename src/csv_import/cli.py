import importlib
import importlib.util
import inspect
import logging
import os
import sys
from types import TracebackType
from typing import Type, Optional

import click

from csv_import.csv.parsers import FileParserFactory, ParserOptions
from csv_import.csv.processors import FileProcessorFactory


def excepthook(
        exception_type: Type[BaseException],
        exception_instance: BaseException,
        exception_traceback: TracebackType) -> None:
    """
    Function called for uncaught exceptions

    :param exception_type: Type of an exception
    :param exception_instance: Exception instance
    :param exception_traceback: Exception traceback
    """

    logging.fatal(
        f'Exception hook has been fired: {exception_instance}',
        exc_info=(exception_type, exception_instance, exception_traceback))


sys.excepthook = excepthook


@click.group()
@click.pass_context
def cli(*args, **kwargs) -> None:
    """
    csv-import is a tool designed to simplify the process of importing CSVs into relational databases.
    It allows you to easily create your own processors to adapt CSVs format to the requirements imposed by databases.
    """

    pass


@cli.group()
def process() -> None:
    """
    Group of command related to processing CSV files.
    """

    pass


@process.command()
@click.option('--input-file', '-i', help='Path to the input CSV file', type=str, required=True)
@click.option('--output-file', '-o', help='Path to the output CSV file', type=str, required=True)
@click.option('--header-lines', '-h', help='Number of header lines', type=int, required=False, default=1)
@click.option('--line-terminator', '-l', help='Character used as a line terminator (new line by default)', type=str, required=False, default='\n')
@click.option('--field-terminator', '-f', help='Character used as a field terminator (comma by default)', type=str, required=False, default=',')
@click.option('--field-enclosing-value', '-e', help='Character used to enclose fields (double quote string by default)', type=str, required=False, default='"')
@click.option('--parser-factory-file', '-p', help='Path to a Python file containing definition of FileParserFactory', type=str, required=False)
def create_import_file(
        input_file: str,
        output_file: str,
        header_lines: int = 1,
        line_terminator: str = '\n',
        field_terminator: str = ',',
        field_enclosing_value: str = '"',
        parser_factory_file: Optional[str] = None) -> None:
    """
    Creates an import file
    """

    file_parser_factory: Optional[FileParserFactory] = None
    parser_options = ParserOptions(
        header_lines=header_lines,
        line_terminator=line_terminator,
        field_terminator=field_terminator,
        field_enclosing_value=field_enclosing_value
    )

    if parser_factory_file:
        parser_factory_module_name = os.path.basename(parser_factory_file)
        parser_factory_module_spec = importlib.util.spec_from_file_location(
            parser_factory_module_name, parser_factory_file)

        if not parser_factory_module_spec:
            raise ValueError(f'Cannot FileParserFactory from {parser_factory_file}')

        parser_factory_module = importlib.util.module_from_spec(parser_factory_module_spec)
        parser_factory_module_spec.loader.exec_module(parser_factory_module)

        for module_type_name, module_type in inspect.getmembers(parser_factory_module):
            if inspect.isclass(module_type) and issubclass(module_type, FileParserFactory):
                file_parser_factory = module_type()
                break

    else:
        file_parser_factory = FileParserFactory()

    file_processor_factory = FileProcessorFactory(file_parser_factory)
    file_processor = file_processor_factory.create(input_file, parser_options)

    file_processor.process(input_file, output_file)

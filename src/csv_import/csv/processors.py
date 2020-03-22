import logging
from abc import ABC, abstractmethod
from logging import Logger
from typing import List, Optional, Sequence

from csv_import.csv.parsers import (FileParser, FileParserFactory, ParsedLine,
                                    ParserOptions)
from csv_import.csv.text import TextWriter


class ProcessingError(Exception):
    pass


class ValueProcessor(ABC):
    """
    Base class for all single-value processors
    """

    @abstractmethod
    def process(self, string: str) -> str:
        """
        Processes single value
        :param string: Input value
        :return: Processed value
        """

        raise NotImplementedError()


class EchoValueProcessor(ValueProcessor):
    """
    Dummy class which doesn't contain any additional logic and just returns input value as is
    """

    def process(self, string: str) -> str:
        return string


class LineProcessor:
    """
    Base class for all line processors
    """

    def __init__(
            self,
            value_processors: Sequence[ValueProcessor],
            options: ParserOptions,
            skip_incorrect_lines: bool = True) -> None:
        """
        :param value_processors: A list of single-value processors
        :param options: Parser options
        :param skip_incorrect_lines: Boolean value indicating whether processor needs to ignore incorrect lines
        """

        self._logger: Logger = logging.getLogger(__name__)
        self._value_processors: Sequence[ValueProcessor] = value_processors
        self._options: ParserOptions = options
        self._skip_incorrect_lines: bool = skip_incorrect_lines

    @property
    def value_processors(self) -> Sequence[ValueProcessor]:
        """
        Returns the list of single-value processors used by this line processor
        :return: List of single-value processors
        """

        return self._value_processors

    def process(self, line: ParsedLine) -> Optional[str]:
        if line.header:
            return line.line

        parsed_values_length = len(line.parsed_values) if line.parsed_values else 0

        if parsed_values_length != len(self._value_processors):
            if self._skip_incorrect_lines:
                return None

            raise ProcessingError(
                f'Expected {len(self._value_processors)} number of values (got {parsed_values_length})')

        processed_values: List[str] = []

        for i in range(len(self._value_processors)):
            value = line.parsed_values[i]
            value_processor = self._value_processors[i]
            processed_value = value_processor.process(value)
            processed_value = \
                self._options.field_enclosing_value + \
                processed_value + \
                self._options.field_enclosing_value

            processed_values.append(processed_value)

        processed_line = self._options.field_terminator.join(processed_values)

        return processed_line


class FileProcessor:
    """
    Base class for file processors
    """

    def __init__(self, file_parser: FileParser, line_processor: LineProcessor) -> None:
        """
        :param file_parser: File parser
        :param line_processor: Line processor
        """

        self._logger: Logger = logging.getLogger(__name__)
        self._file_parser: FileParser = file_parser
        self._line_processor: LineProcessor = line_processor

    @property
    def line_processor(self) -> LineProcessor:
        """
        Returns the line processor used by this file processor
        :return: Line processor
        """

        return self._line_processor

    def process(self, input_file_path: str, output_file_path: str) -> None:
        """
        Processes an input file
        :param input_file_path: Input file path
        :param output_file_path: Output file path
        """

        self._logger.info(f'Started processing file "{input_file_path}" into "{output_file_path}"')

        with TextWriter.create(output_file_path) as output_file:
            for parsed_line in self._file_parser.parse(input_file_path):
                processed_line = self._line_processor.process(parsed_line)

                # Skip incorrect lines
                if processed_line is not None:
                    output_file.write_line(processed_line)

        self._logger.info(f'Finished processing file "{input_file_path}" to "{output_file_path}"')


class FileProcessorFactory:
    """
    Factory class for creating file processors
    """

    def __init__(self, file_parser_factory: FileParserFactory) -> None:
        """
        :param file_parser_factory: Factory to create a file parser
        """

        self._file_parser_factory: FileParserFactory = file_parser_factory

    def create(self, input_file_path: str, options: ParserOptions) -> FileProcessor:
        """
        Creates a file processor
        :param input_file_path: Input file path
        :param options: Parser options
        :return: Created file processor
        """

        file_parser = self._file_parser_factory.create(input_file_path, options)
        value_processors_count = len(file_parser.line_parser.value_parsers)
        value_processors = [EchoValueProcessor() for _ in range(value_processors_count)]
        line_processor = LineProcessor(value_processors, options)
        file_processor = FileProcessor(file_parser, line_processor)

        return file_processor

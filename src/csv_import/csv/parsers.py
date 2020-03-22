import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import Logger
from typing import Iterator, List, Optional, Pattern, Sequence

from csv_import.csv.text import TextReader


class ParsingError(Exception):
    pass


@dataclass(frozen=True)
class ParserOptions:
    """
    Class used for storing different parsing options
    """

    header_lines: int = 1
    line_terminator: str = '\n'
    field_terminator: str = '\t'
    field_enclosing_value: str = ''


class ValueParser(ABC):
    """
    Base class for all single-value parsers
    """

    @abstractmethod
    def parse(self, string: str) -> str:
        """
        Parses string value passed as an argument
        :param string: String to parse
        :return: Parsed result
        """

        raise NotImplementedError()


class NumberParser(ValueParser):
    """
    Class for parsing numeric values
    """

    DEFAULT_PATTERN: str = r'\d+'

    def __init__(self, number_regex: Optional[Pattern[str]] = None, default_value: Optional[int] = None) -> None:
        """
        :param number_regex: Regex used for paring numeric values (by default regex for integers will be used)
        :param default_value: Default value used in the case when a string cannot be parsed
        """

        self._number_regex: Pattern[str] = number_regex if number_regex else re.compile(NumberParser.DEFAULT_PATTERN)
        self._default_value: Optional[int] = default_value

    def parse(self, string: str) -> str:
        if self._number_regex.match(string):
            return string

        if self._default_value:
            return str(self._default_value)

        raise ParsingError(f'{string} is not a number')


class StringParser(ValueParser):
    """
    Class for parsing string values
    """

    def __init__(self, replaceable_symbols: Optional[List[str]] = None) -> None:
        """
        :param replaceable_symbols: List containing symbols to be replaced with an empty string
        """

        self._replaceable_symbols: List[str] = replaceable_symbols if replaceable_symbols else ['\\']

    def parse(self, string: str) -> str:
        for replaceable_symbol in self._replaceable_symbols:
            string = string.replace(replaceable_symbol, '')

        string = string.strip()

        return string


class EchoValueParser(ValueParser):
    """
    Dummy class which doesn't contain any additional logic and just returns input value as is
    """

    def parse(self, string: str) -> str:
        return string


@dataclass
class Line:
    """
    Class used for storing input data used by line parsers
    """

    __slots__ = ['file', 'index', 'header', 'line']
    file: TextReader
    index: int
    header: bool
    line: str


@dataclass
class ParsedLine(Line):
    """
    Class used for storing result of parsing
    """

    def __init__(self, input_line: Line, parsed_values: Optional[List[str]] = None) -> None:
        """
        :param input_line: Line used as an input for a parser
        :param parsed_values: List of parsed values found in an input line
        """
        self._input_line: Line = input_line
        self.parsed_values = parsed_values

    @property
    def file(self) -> TextReader:
        return self._input_line.file

    @property
    def index(self) -> int:
        return self._input_line.index

    @property
    def header(self) -> bool:
        return self._input_line.header

    @property
    def line(self) -> str:
        return self._input_line.line

    def skipped(self) -> bool:
        return self.parsed_values is None

    parsed_values: Optional[List[str]] = None


class LineParser:
    """
    Base class for line parsers responsible for parsing an input string into a list of parsed values
    """

    def __init__(
            self,
            value_parsers: Sequence[ValueParser],
            options: ParserOptions,
            skip_incorrect_lines: bool = True,
            next_line_parser: Optional['LineParser'] = None) -> None:
        """
        :param value_parsers: List of single-value parsers
        :param options: Parsing options
        :param skip_incorrect_lines: Boolean value denoting whether the parser should skip incorrect lines or
                                     halt immediately
        :param next_line_parser: Optional value storing a parser used in the case of the current one failed to parse
                                 an input string.
                                 Please note that @skip_incorrect_lines and @next_line_parser are mutually exclusive:
                                   - if @skip_incorrect_lines is set the error will be skipped,
                                   - otherwise if @next_line_parser is set it will be used for parsing,
                                   - otherwise when @next_line_parser is missing the error will be raised and
                                     parsing will be halted
        """

        self._logger: Logger = logging.getLogger(__name__)
        self._value_parsers: Sequence[ValueParser] = value_parsers
        self._options: ParserOptions = options
        self._skip_incorrect_lines: bool = skip_incorrect_lines
        self._next_line_processor: Optional[LineParser] = next_line_parser

    @property
    def value_parsers(self) -> Sequence[ValueParser]:
        """
        Returns a list of single-value parsers used to parse an input string
        :return: A list of single-value parsers
        """

        return self._value_parsers

    def _parse(self, line: Line, values: List[str]) -> List[str]:
        if len(values) != len(self._value_parsers):
            raise ParsingError(
                f'Line # {line.index}: {line.line}. Expected {len(self._value_parsers)} values, got {len(values)}')

        parsed_values = []

        for value_parser, value in zip(self._value_parsers, values):
            result_value = value_parser.parse(value)

            parsed_values.append(result_value)

        return parsed_values

    @staticmethod
    def char_list_to_string(char_array: List[str]) -> str:
        value = ''.join(char_array)

        return value

    def parse(self, line: Line) -> ParsedLine:
        """
        Parses an input line into a list of parsed values
        :param line: Line object containing a line to parse
        :return: ParsedLine object containing the parsed line
        """

        values = LineParser.split(line.line, self._options)

        try:
            parsed_values = self._parse(line, values)
            parsed_line = ParsedLine(line, parsed_values)

            return parsed_line
        except Exception:
            if self._skip_incorrect_lines:
                self._logger.warning(
                    f'Skipping line # {line.index}: {line.line}')

                return ParsedLine(line)

            if self._next_line_processor:
                return self._next_line_processor.parse(line)

            raise

    @staticmethod
    def split(string: str, parser_options: ParserOptions) -> List[str]:
        """
        Splits an input string into a list of values using separator set in parsing options
        :param string: Input string
        :param parser_options: Parser options
        :return: List of split values
        """

        buffer: List[str] = []
        values: List[str] = []
        inside_field = False

        string = string.strip(parser_options.line_terminator)

        for char in string:
            if not inside_field and char == parser_options.field_terminator:
                value = LineParser.char_list_to_string(buffer)
                values.append(value)
                buffer = []
            elif char == parser_options.field_enclosing_value:
                inside_field = False if inside_field else True
            else:
                buffer.append(char)

        if buffer:
            value = LineParser.char_list_to_string(buffer)
            values.append(value)

        # In the case of an empty string return an empty list
        if len(values) == 1 and values[0] == '':
            return []

        strippable_chars = ' ' + parser_options.field_enclosing_value + parser_options.line_terminator
        values = list(map(lambda value: value.strip(strippable_chars), values))

        return values


class FileParser:
    """
    Base class used for parsing files
    """

    def __init__(self, line_parser: LineParser, options: ParserOptions) -> None:
        """
        :param line_parser: Line parser used to parse lines of an input file
        :param options: Parser options
        """

        self._logger: Logger = logging.getLogger(__name__)
        self._line_parser = line_parser
        self._options: ParserOptions = options

    @property
    def line_parser(self) -> LineParser:
        """
        Returns a line parser used by this parser
        :return: Line parser
        """

        return self._line_parser

    def parse(self, input_file_path: str) -> Iterator[ParsedLine]:
        """
        Parses an input file and returns an iterable sequence of parsed lines
        :param input_file_path: String containing path to the input file
        :return: Iterator of parsed lines
        """

        self._logger.info(f'Started parsing file "{input_file_path}"')

        with TextReader.create(input_file_path) as input_file:
            while True:
                input_line = input_file.read_line()

                if not input_line:
                    break

                if input_file.current_line_index % 1000 == 0:
                    self._logger.info(f'Parsed {input_file.current_line_index} lines')

                header = input_file.current_line_index + 1 <= self._options.header_lines
                input_line = Line(file=input_file, index=input_file.current_line_index, header=header, line=input_line)

                if header:
                    parsed_line = ParsedLine(input_line)
                else:
                    parsed_line = self._line_parser.parse(input_line)

                yield parsed_line

        self._logger.info(f'Finished parsing file "{input_file_path}"')


class FileParserFactory:
    """
    Class used for creating file parsers by sniffing format from the first file's line
    """

    def __init__(self) -> None:
        self._logger: Logger = logging.getLogger(__name__)

    def create(self, input_file_path: str, options: ParserOptions) -> FileParser:
        """
        Creates a file parser by sniffing format from an input file
        :param input_file_path: Input file path
        :param options: Parser options
        :return: Created file parser
        """

        self._logger.info(f'Started creating a file parser for "{input_file_path}"')

        with TextReader.create(input_file_path) as input_file_reader:
            for _ in range(options.header_lines):
                input_file_reader.read_line()

            value_parsers: List[ValueParser] = []
            first_line = input_file_reader.read_line()
            values = LineParser.split(first_line, options)
            number_parser = NumberParser()
            string_parser = StringParser()

            for value in values:
                value = value.strip(' ' + options.field_enclosing_value)

                try:
                    number_parser.parse(value)
                    value_parsers.append(number_parser)
                    continue
                except Exception:
                    value_parsers.append(string_parser)

            if not value_parsers:
                raise ParsingError(f'Could not sniff format from the first line of "{input_file_path}"')

            line_parser = LineParser(value_parsers, options)
            file_parser = FileParser(line_parser, options)

            self._logger.info(f'File parser for "{input_file_path}" has been created')

            return file_parser

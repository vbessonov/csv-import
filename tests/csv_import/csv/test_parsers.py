from typing import List, Optional, Type
from unittest import TestCase, mock
from unittest.mock import MagicMock, create_autospec

from parameterized import parameterized

from csv_import.csv.parsers import (EchoValueParser, FileParser,
                                    FileParserFactory, Line, LineParser,
                                    NumberParser, ParsedLine, ParserOptions,
                                    ParsingError, StringParser, ValueParser)
from csv_import.csv.text import TextReader
from tests.csv_import.csv.test_text import mock_builtin_open


class NumberParserTest(TestCase):
    @parameterized.expand([
        ('0', None),
        ('0.1', None),
        ('s', ParsingError)
    ])
    def test_parse(self, number_string: str, expected_exception_type: Optional[Type] = None) -> None:
        parser = NumberParser()

        try:
            parser.parse(number_string)
        except Exception as exception:
            if expected_exception_type:
                self.assertIsNotNone(exception)
                self.assertIsInstance(exception, expected_exception_type)
            else:
                raise


class StringValueParser(TestCase):
    @parameterized.expand([
        ('0', None),
        ('0.1', None),
        ('s', ParsingError)
    ])
    def test_parse(self, number_string: str, expected_exception_type: Optional[Type] = None) -> None:
        parser = StringParser()

        try:
            parser.parse(number_string)
        except Exception as exception:
            if expected_exception_type:
                self.assertIsNotNone(exception)
                self.assertIsInstance(exception, expected_exception_type)


class EchoValueParserTest(TestCase):
    @parameterized.expand([
        '0',
        '0.1',
        'John Doe'
    ])
    def test_parse(self, input_string: str) -> None:
        # Arrange
        parser = EchoValueParser()

        # Act
        result = parser.parse(input_string)

        # Assert
        self.assertEqual(input_string, result)


class LineParserTest(TestCase):
    @parameterized.expand([
        [
            'empty string',
            '',
            ParserOptions(),
            []
        ],
        [
            'string with a wrong field terminator',
            '1\t2\t3',
            ParserOptions(field_terminator=','),
            ['1\t2\t3']
        ],
        [
            'string with a right field terminator',
            '1\t2\t3',
            ParserOptions(),
            ['1', '2', '3']
        ],
        [
            'string with an overridden field terminator',
            '1,2,3',
            ParserOptions(field_terminator=','),
            ['1', '2', '3']
        ],
        [
            'string with enclosed values',
            '"John Doe"\t"23"\t"10,000"',
            ParserOptions(field_enclosing_value='"'),
            ['John Doe', '23', '10,000']
        ],
        [
            'string with several enclosed values',
            'John Doe\t23\t"10,000"',
            ParserOptions(field_enclosing_value='"'),
            ['John Doe', '23', '10,000']
        ]
    ])
    def test_split(self, name: str, string: str, parser_options: ParserOptions, expected_result: List[str]) -> None:
        # Act
        result = LineParser.split(string, parser_options)

        # Assert
        self.assertEqual(expected_result, result)

    @parameterized.expand([
        [
            'empty string and empty value parsers list (skip errors = True)',
            [],
            ParserOptions(),
            True,
            '',
            []
        ],
        [
            'empty string and empty value parsers list (skip errors = False)',
            [],
            ParserOptions(),
            False,
            '',
            []
        ],
        [
            'empty string and non-empty value parsers list (skip errors = True)',
            [NumberParser()],
            ParserOptions(),
            True,
            '',
            None
        ],
        [
            'empty string and non-empty value parsers list (skip errors = False)',
            [NumberParser()],
            ParserOptions(),
            False,
            '',
            [],
            ParsingError
        ],
        [
            'string with missing fields (skip errors = True)',
            [NumberParser(), NumberParser()],
            ParserOptions(),
            True,
            '123\t',
            None
        ],
        [
            'string with missing fields (skip errors = False)',
            [NumberParser(), NumberParser()],
            ParserOptions(),
            False,
            '123\t',
            [],
            ParsingError
        ],
        [
            'string with numbers and strings',
            [NumberParser(), StringParser(), NumberParser()],
            ParserOptions(field_terminator=','),
            False,
            '123,abc,456',
            ['123', 'abc', '456']
        ]
    ])
    def test_parse(
            self,
            name: str,
            value_parsers: List[ValueParser],
            parser_options: ParserOptions,
            skip_incorrect_lines: bool,
            line: str,
            expected_result: List[str],
            expected_exception_type: Optional[Type] = None) -> None:
        # Arrange
        line_parser = LineParser(value_parsers, parser_options, skip_incorrect_lines)
        file = create_autospec(TextReader)
        input_line = Line(file=file, index=0, header=False, line=line)

        try:
            # Act
            parsed_line = line_parser.parse(input_line)

            # Assert
            self.assertEqual(input_line.index, parsed_line.index)
            self.assertEqual(input_line.header, parsed_line.header)
            self.assertEqual(input_line.line, parsed_line.line)
            self.assertEqual(expected_result, parsed_line.parsed_values)
        except Exception as exception:
            if expected_exception_type:
                self.assertIsInstance(exception, expected_exception_type)
            else:
                raise

    def test_parse_uses_next_line_parser(self) -> None:
        # Arrange
        line = 'abc'
        next_line_parser = LineParser([StringParser()], ParserOptions(), False)
        file = create_autospec(TextReader)
        input_line = Line(file=file, index=0, header=False, line=line)
        next_line_parser_mock = mock.create_autospec(LineParser)
        next_line_parser_mock.parse = MagicMock(side_effect=lambda l: next_line_parser.parse(l))
        line_parser = LineParser([NumberParser()], ParserOptions(), False, next_line_parser_mock)

        # Act
        parsed_line = line_parser.parse(input_line)

        # Assert
        self.assertIsNotNone(parsed_line.parsed_values)
        self.assertEqual(1, len(parsed_line.parsed_values))
        self.assertEqual(line, parsed_line.parsed_values[0])
        next_line_parser_mock.parse.assert_called_once()


class FileParserTest(TestCase):
    @parameterized.expand([
        [
            'empty file',
            LineParser([], ParserOptions()),
            ParserOptions(),
            '',
            []
        ],
        [
            'file with one header',
            LineParser([], ParserOptions()),
            ParserOptions(),
            'name\tage\tsalary',
            [
                None
            ]
        ],
        [
            'file with one header and one data line',
            LineParser([StringParser(), NumberParser(), NumberParser()], ParserOptions()),
            ParserOptions(),
            'name\tage\tsalary\nJohn Doe\t23\t10,000',
            [
                None,
                ['John Doe', '23', '10,000']
            ]
        ],
        [
            'file with two header lines and one data line',
            LineParser([StringParser(), NumberParser(), NumberParser()], ParserOptions(header_lines=2)),
            ParserOptions(header_lines=2),
            'Personnel\nname\tage\tsalary\nJohn Doe\t23\t10,000',
            [
                None,
                None,
                ['John Doe', '23', '10,000']
            ]
        ],
        [
            'file with one header and two data lines',
            LineParser([StringParser(), NumberParser(), NumberParser()], ParserOptions()),
            ParserOptions(),
            'name\tage\tsalary\nJohn Doe\t23\t10,000\nBob Doe\t30\t15,000',
            [
                None,
                ['John Doe', '23', '10,000'],
                ['Bob Doe', '30', '15,000']
            ]
        ]
    ])
    def test_parse(
            self,
            name: str,
            line_parser: LineParser,
            parser_options: ParserOptions,
            data: str,
            expected_result: List[Optional[List[str]]],
            expected_exception_type: Optional[Type] = None) -> None:
        file_parser = FileParser(line_parser, parser_options)

        with mock_builtin_open(data=data):
            try:
                result_iterator = file_parser.parse('')
                result = list(result_iterator)

                self.assertEqual(len(expected_result), len(result))

                for expected_line, line in zip(expected_result, result):
                    self.assertIsInstance(line, ParsedLine)
                    self.assertEqual(expected_line, line.parsed_values)
            except Exception as exception:
                if expected_exception_type:
                    self.assertIsInstance(exception, expected_exception_type)
                else:
                    raise


class FileParserFactoryTest(TestCase):
    @parameterized.expand([
        [
            'empty string',
            ParserOptions(),
            '',
            [],
            ParsingError
        ],
        [
            'string with numbers',
            ParserOptions(header_lines=0),
            '123\t456\t789\n',
            [NumberParser, NumberParser, NumberParser]
        ],
        [
            'string with non-numbers and numbers',
            ParserOptions(header_lines=0),
            'abc\tdef\tghi\t123\n',
            [StringParser, StringParser, StringParser, NumberParser]
        ],
        [
            'text with headers',
            ParserOptions(header_lines=0),
            'abc\tdef\tghi\t123\n',
            [StringParser, StringParser, StringParser, NumberParser]
        ]

    ])
    def test_create(
            self,
            name: str,
            parser_options: ParserOptions,
            data: str,
            expected_value_parser_types: List[Type],
            expected_exception_type: Optional[Type] = None) -> None:
        factory = FileParserFactory()

        with mock_builtin_open(data=data):
            try:
                file_parser = factory.create('', parser_options)
                line_parser = file_parser.line_parser

                self.assertEqual(len(expected_value_parser_types), len(line_parser.value_parsers))

                for expected_value_parser_type, value_parser in zip(
                        expected_value_parser_types,
                        line_parser.value_parsers):
                    self.assertIsInstance(value_parser, expected_value_parser_type)
            except Exception as exception:
                if expected_exception_type:
                    self.assertIsInstance(exception, expected_exception_type)
                else:
                    raise

import os
from typing import List, Sequence
from unittest import TestCase
from unittest.mock import MagicMock, call, create_autospec, patch

from parameterized import parameterized

from csv_import.csv.parsers import (FileParser, FileParserFactory, Line,
                                    LineParser, NumberParser, ParsedLine,
                                    ParserOptions, StringParser)
from csv_import.csv.processors import (EchoValueProcessor, FileProcessor,
                                       FileProcessorFactory, LineProcessor,
                                       ValueProcessor)
from csv_import.csv.text import TextReader, TextWriter
from tests.csv_import.csv.test_text import mock_builtin_open


class EchoValueProcessorTest(TestCase):
    @parameterized.expand([
        [''],
        ['abc'],
        ['123.456']
    ])
    def test_parse(self, string: str) -> None:
        # Arrange
        processor = EchoValueProcessor()

        # Act
        result = processor.process(string)

        # Assert
        self.assertEqual(string, result)


class LineProcessorTest(TestCase):
    @parameterized.expand([
        [
            'header string',
            [],
            ParserOptions(),
            ParsedLine(Line(file=create_autospec(TextReader), index=1, header=True, line='Name\tAge\tSalary')),
            'Name\tAge\tSalary'
        ],
        [
            'data string',
            [EchoValueProcessor(), EchoValueProcessor(), EchoValueProcessor()],
            ParserOptions(),
            ParsedLine(
                Line(file=create_autospec(TextReader), index=1, header=False, line='John Doe\t23\t10,000'),
                parsed_values=['John Doe', '23', '10,000']
            ),
            'John Doe\t23\t10,000'
        ]
    ])
    def test_process(
            self,
            name: str,
            value_processors: Sequence[ValueProcessor],
            options: ParserOptions,
            line: ParsedLine,
            expected_result: str) -> None:
        # Arrange
        line_processor = LineProcessor(value_processors, options)

        # Act
        result = line_processor.process(line)

        # Assert
        self.assertEqual(expected_result, result)


class FileProcessorTest(TestCase):
    @parameterized.expand([
        [
            'empty file',
            LineProcessor([], ParserOptions()),
            []
        ],
        [
            'file with only header',
            LineProcessor([], ParserOptions()),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name\tAge\tSalary'))
            ]
        ],
        [
            'file with one header and one data line',
            LineProcessor([], ParserOptions()),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name\tAge\tSalary')),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=1, header=True, line='John Doe\t23\t10,000'),
                    parsed_values=[
                        'John Doe',
                        '23',
                        '10,000'
                    ]
                )
            ]
        ],
        [
            'file with one header and two data lines',
            LineProcessor([], ParserOptions()),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name\tAge\tSalary')),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=1, header=True, line='John Doe\t23\t10,000'),
                    parsed_values=[
                        'John Doe',
                        '23',
                        '10,000'
                    ]
                ),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=2, header=True, line='Bob Doe\t30\t50,000'),
                    parsed_values=[
                        'Bob Doe',
                        '30',
                        '50,000'
                    ]
                )
            ]
        ]
    ])
    def test_process(self, name: str, line_processor: LineProcessor, lines: List[ParsedLine]) -> None:
        # Arrange
        file_parser = create_autospec(FileParser)
        file_parser.parse = MagicMock(side_effect=lambda _: lines)
        file_processor = FileProcessor(file_parser, line_processor)
        text_writer_instance_mock = create_autospec(TextWriter)
        text_writer_mock = create_autospec(TextWriter)
        text_writer_mock.__enter__ = MagicMock(return_value=text_writer_instance_mock)

        # Act
        with patch('csv_import.csv.text.TextWriter.create', MagicMock(return_value=text_writer_mock)):
            with mock_builtin_open():
                file_processor.process('', '')

        # Arrange
        file_parser.parse.called_once()

        text_writer_instance_mock.write_line.assert_has_calls(
            [call(line.line) for line in lines]
        )


class FileProcessorFactoryTest(TestCase):
    @parameterized.expand([
        [
            'parser without single-value parsers',
            FileParser(LineParser([], ParserOptions()), ParserOptions())
        ],
        [
            'parser with single-value parsers',
            FileParser(LineParser([StringParser(), NumberParser(), NumberParser()], ParserOptions()), ParserOptions())
        ]
    ])
    def test_create(self, name: str, file_parser: FileParser) -> None:
        # Arrangement
        file_parser_factory_mock = create_autospec(FileParserFactory)
        file_parser_factory_mock.create = MagicMock(return_value=file_parser)
        factory = FileProcessorFactory(file_parser_factory_mock)

        # Act
        result = factory.create('', ParserOptions())

        # Assert
        self.assertIsInstance(result, FileProcessor)
        self.assertIsInstance(result.line_processor, LineProcessor)
        self.assertIsNotNone(result.line_processor.value_processors)
        self.assertEqual(len(file_parser.line_parser.value_parsers), len(result.line_processor.value_processors))


class FileProcessorIntegrationTest(TestCase):
    @parameterized.expand([
        [
            '01_correct_file_with_commas.csv',
            ParserOptions(field_terminator=',', field_enclosing_value='"'),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name,Age,Salary\n')),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=1, header=False, line='John Doe,23,"10,000"'),
                    parsed_values=[
                        'John Doe',
                        '23',
                        '10,000'
                    ]
                )
            ]
        ],
        [
            '02_correct_file_with_tabulations.csv',
            ParserOptions(field_terminator='\t', field_enclosing_value='"'),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name\tAge\tSalary\n')),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=1, header=False, line='John Doe\t23\t10,000'),
                    parsed_values=[
                        'John Doe',
                        '23',
                        '10,000'
                    ]
                )
            ]
        ],
        [
            '02_correct_file_with_tabulations.csv',
            ParserOptions(field_terminator='\t', field_enclosing_value='"'),
            [
                ParsedLine(Line(file=create_autospec(TextReader), index=0, header=True, line='Name\tAge\tSalary\n')),
                ParsedLine(
                    Line(file=create_autospec(TextReader), index=1, header=False, line='John Doe\t23\t10,000'),
                    parsed_values=[
                        'John Doe',
                        '23',
                        '10,000'
                    ]
                )
            ]
        ]
    ])
    def test_process(self, input_file: str, options: ParserOptions, expected_parsed_lines: List[ParsedLine]) -> None:
        # Arrange
        def process(parsed_line: ParsedLine) -> str:
            parsed_lines.append(parsed_line)
            return original_process(parsed_line)

        file_parser_factory = FileParserFactory()
        file_processor_factory = FileProcessorFactory(file_parser_factory)
        current_dir = os.path.dirname(os.path.realpath(__file__))
        input_file_path = os.path.join(current_dir, 'fixtures', input_file)
        output_file_path = input_file_path + '.out'
        parsed_lines: List[ParsedLine] = []

        file_processor = file_processor_factory.create(input_file_path, options)
        original_process = file_processor.line_processor.process
        file_processor.line_processor.process = MagicMock(side_effect=process)

        # Act
        with patch('csv_import.csv.text.TextWriter.create'):
            file_processor.process(input_file_path, output_file_path)

        # Assert
        for expected_parsed_line, parsed_line in zip(expected_parsed_lines, parsed_lines):
            self.assertEqual(expected_parsed_line.index, parsed_line.index)
            self.assertEqual(expected_parsed_line.header, parsed_line.header)
            self.assertEqual(expected_parsed_line.line, parsed_line.line)
            self.assertEqual(expected_parsed_line.parsed_values, parsed_line.parsed_values)

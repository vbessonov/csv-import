from typing import List

from csv_import.csv.parsers import (FileParser, FileParserFactory, Line,
                                    LineParser, NumberParser, ParserOptions,
                                    ParsingError, StringParser)


class LineWithIDAndNameFirstLetterParser(LineParser):
    def _parse(self, line: Line, values: List[str]) -> List[str]:
        # First Let's check whether is our case and we can handle it
        if len(values) != 2:
            raise ParsingError(
                f'Line # {line.index}: {line.line}. '
                f'Expected 2 fields, got {len(values)}')

        # We got the first field
        record_id = self._value_parsers[0].parse(values[0])

        # And the first letter of the name
        name_first_letter = values[1]

        # Let's scan the next line and get its fields
        next_line = line.file.read_line()
        next_line_fields = LineParser.split(next_line, self._options)

        # We need to check whether the next line contains all the remaining fields
        if len(next_line_fields) != 3:
            raise ParsingError(
                f'Line # {line.index}: {next_line}. '
                f'Expected 3 fields, got {len(next_line_fields)}')

        # Let's parse all the remaining fields
        name = self._value_parsers[1].parse(name_first_letter + next_line_fields[0])
        age = self._value_parsers[2].parse(next_line_fields[1])
        salary = self._value_parsers[3].parse(next_line_fields[2])

        return [record_id, name, age, salary]


class IDAndNameLineParser(LineParser):
    def _parse(self, line: Line, values: List[str]) -> List[str]:
        # First Let's check whether is our case and we can handle it
        if len(values) != 2:
            raise ParsingError(
                f'Line # {line.index}: {line.line}. '
                f'Expected 2 fields, got {len(values)}')

        # We got the record ID
        record_id = self._value_parsers[0].parse(values[0])

        # And the name too
        name = self._value_parsers[1].parse(values[1])

        # Let's skip empty lines
        next_line = line.file.read_line()

        while next_line.strip() == '':
            next_line = line.file.read_line()

        # We got the next line with data, let's split it
        next_line_fields = LineParser.split(next_line, self._options)

        # We need to check whether the next line contains all the remaining fields
        if len(next_line_fields) != 2:
            raise ValueError(
                f'Line # {line.file.current_line_index}: {next_line}. '
                f'Expected 2 columns, got {len(next_line_fields)}')

        # Let's parse all the remaining fields
        age = self._value_parsers[2].parse(next_line_fields[0])
        salary = self._value_parsers[3].parse(next_line_fields[1])

        return [record_id, name, age, salary]


class BrokerCSVFileParserFactory(FileParserFactory):
    def create(self, input_file_path: str, options: ParserOptions) -> FileParser:
        # Let's define single-value parsers
        value_parsers = [
            NumberParser(),  # Record ID
            StringParser(),  # Name
            NumberParser(),  # Age
            NumberParser()   # Salary
        ]

        # Let's define a line parser as a chain of parsers
        line_parser = LineParser(
            value_parsers,
            options,
            skip_incorrect_lines=False,
            next_line_parser=LineWithIDAndNameFirstLetterParser(
                value_parsers,
                options,
                skip_incorrect_lines=False,
                next_line_parser=IDAndNameLineParser(
                    value_parsers,
                    options,
                    skip_incorrect_lines=False
                )
            )
        )

        # Finally let's create a file parser
        file_parser = FileParser(line_parser, options)

        return file_parser

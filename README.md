# csv-import
**csv-import** is a library designed for creating highly customizable CSV processors able to import parsed result into relational DBs.

## Example
Let's imagine that our customer provided us with a _broken_ [CSV file](examples/broken.csv):
```csv
ID,Name,Age,Salary
1,Kirsty Jacobson,23,"10,000"
2,B
obbie Trejo,30,"15,000"
3,Kristen Krueger,20,"10,000"
4,Roy Mcmillan,




40,"50,000"
```

Let's first try to run **csv-import** with the default settings:
```bash
python -m csv_import process create-import-file \
    --input-file examples/broken.csv \
    --output-file examples/broken.out.csv
```

We will get the following output:
```bash
Skipping line # 2: 2,B

Skipping line # 3: obbie Trejo,30,"15,000"

Skipping line # 5: 4,Roy Mcmillan,

Skipping line # 6: 

Skipping line # 7: 

Skipping line # 8: 

Skipping line # 9: 

Skipping line # 10: 40,"50,000"
```

It can help us to spot the following two errors:
1. A new line symbol after the first letter of a name splitting a string into two (record  2)
2. A new line symbol after a name following by arbitrary new lines (record 4)

To fix these errors we need to create custom parsers and a custom parser factor.
Let's start from custom parsers.

### Custom parser I (new line symbol after the first letter of a name)
To create a custom parser we need to create a new Python class, inherit it from `csv_import.csv.parsers.LineParser` and override `_parse` method:
```python
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
```

### Custom parser II (new line symbol after a name)
Our custom parser fixing this error will be looking like that:
```python
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
```  

### Custom factory
To create a custom factory you need to create a Python class and inherit it from `csv_import.csv.parsers.FileParserFactory`:
```python
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
```

The whole can be found in [broken_parser.py](examples/broken_parser.py)

Now we are ready to try it out:
```bash
python -m csv_import process create-import-file \
    --input-file examples/broken.csv \
    --output-file examples/broken.out.csv
    --parser-factory-file examples/broken_parser.py
```

It will produce perfectly valid CSV:
```csv
ID,Name,Age,Salary
"1","Kirsty Jacobson","23","10,000"
"2","Bobbie Trejo","30","15,000"
"3","Kristen Krueger","20","10,000"
"4","Roy Mcmillan","40","50,000"
```
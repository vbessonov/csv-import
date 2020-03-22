from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Optional, Type, cast
from unittest import TestCase
from unittest.mock import Mock, mock_open, patch

from csv_import.csv.text import TextIO, TextReader, TextWriter


@contextmanager
def mock_builtin_open(open_mock: Optional[Mock] = None, data: Optional[str] = None) -> Mock:
    """
    Patches buit-in open function to avoid the need to work with real files
    :param open_mock: Optional Mock object used as a return value of open function
                      (can be used to get access to internal Handle object)
    :param data: Optional string parameter used as file content
    :return: Mock object
    """
    if data and open_mock:
        raise ValueError('open_mock and data parameters are mutually exclusive')

    if not open_mock:
        open_mock = mock_open(read_data=data)

    with patch('builtins.open', open_mock, create=True) as open_patch:
        yield open_patch


class _AbstractTextIOTest(ABC, TestCase):
    @property
    @abstractmethod
    def _concrete_class(self) -> Type[TextIO]:
        raise NotImplementedError()

    @contextmanager
    def _create_text_instance(self, open_mock: Optional[Mock] = None) -> TextIO:
        # Act
        with mock_builtin_open(open_mock):
            with self._concrete_class('dummy') as text_instance:
                yield text_instance

    def test_current_line_is_initialized_correctly(self) -> None:
        # Act
        with self._create_text_instance() as text_instance:
            # Assert
            self.assertEqual(-1, text_instance.current_line_index)
            self.assertIsNone(text_instance.current_line)

    def test_context_manager_works_opens_and_closes_file(self) -> None:
        # Arrange
        open_mock = mock_open()

        # Act
        with self._create_text_instance(open_mock):
            pass

        open_mock.assert_called_once()
        file_mock = open_mock()
        file_mock.close.assert_called_once()


class TextReaderTest(_AbstractTextIOTest):
    @property
    def _concrete_class(self) -> Type[TextIO]:
        return TextReader

    def test_create(self) -> None:
        open_mock = mock_open()

        with mock_builtin_open(open_mock):
            with TextReader.create(''):
                pass

        open_mock.assert_called_once()
        file_mock = open_mock()
        file_mock.close.assert_called_once()

    def test_read_line_advances_current_line(self) -> None:
        first_line = 'abc\n'
        second_line = 'cde'
        data_mock = f'{first_line}{second_line}'
        open_mock = mock_open(read_data=data_mock)

        # Act
        with cast(TextReader, self._create_text_instance(open_mock)) as text_reader:
            line = text_reader.read_line()
            self.assertEqual(first_line, line)
            self.assertEqual(0, text_reader.current_line_index)
            self.assertEqual(first_line, text_reader.current_line)

            line = text_reader.read_line()
            self.assertEqual(second_line, line)
            self.assertEqual(1, text_reader.current_line_index)
            self.assertEqual(second_line, text_reader.current_line)


class TextWriterTest(_AbstractTextIOTest):
    @property
    def _concrete_class(self) -> Type[TextIO]:
        return TextWriter

    def test_create(self) -> None:
        open_mock = mock_open()

        with mock_builtin_open(open_mock):
            with TextWriter.create(''):
                pass

        open_mock.assert_called_once()
        file_mock = open_mock()
        file_mock.close.assert_called_once()

    def test_write_line_advances_current_line(self) -> None:
        first_line = 'abc\n'
        second_line = 'cde\n'

        # Act
        with cast(TextWriter, self._create_text_instance()) as text_writer:
            text_writer.write_line(first_line)
            self.assertEqual(0, text_writer.current_line_index)
            self.assertEqual(first_line, text_writer.current_line)

            text_writer.write_line(second_line)
            self.assertEqual(1, text_writer.current_line_index)
            self.assertEqual(second_line, text_writer.current_line)

    def test_write_line_always_adds_new_line_symbols(self) -> None:
        first_line = 'abc'

        # Act
        with cast(TextWriter, self._create_text_instance()) as text_writer:
            text_writer.write_line(first_line)
            self.assertEqual(0, text_writer.current_line_index)
            self.assertEqual(first_line + '\n', text_writer.current_line)

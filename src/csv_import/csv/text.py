from abc import ABC
from types import TracebackType
from typing import IO, Optional, Type, TypeVar

TextIOType = TypeVar('TextIOType', bound='TextIO')


class TextIO(ABC):
    """
    Base class for all text file related operations
    """
    def __init__(self, file_path: str, file_mode: str) -> None:
        self._file_path: str = file_path
        self._file_mode: str = file_mode
        self._file: Optional[IO[str]] = None
        self._current_line_index: int = -1
        self._current_line: Optional[str] = None

    @property
    def current_line(self) -> Optional[str]:
        """
        Returns current line

        :return: Current line
        """
        return self._current_line

    @property
    def current_line_index(self) -> int:
        """
        Returns current line index

        :return: Current line index
        """
        return self._current_line_index

    def __enter__(self) -> TextIOType:
        self._file = open(self._file_path, self._file_mode)

        return self

    def __exit__(
            self,
            exception_type: Optional[Type[BaseException]],
            exception_value: Optional[BaseException],
            traceback: Optional[TracebackType]) -> None:
        self.close()

    def close(self) -> None:
        if self._file:
            self._file.close()


class TextReader(TextIO):
    """
    Class for reading text files
    """
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, 'r')

    def read_line(self) -> str:
        """
        Reads lines from a file

        :return: Line read
        """
        if self._file is None:
            raise IOError(f'Cannot read from file {self._file_path}')

        self._current_line = self._file.readline()
        self._current_line_index += 1

        return self._current_line

    @staticmethod
    def create(file_path: str) -> 'TextReader':
        return TextReader(file_path)


class TextWriter(TextIO):
    """
    Class for write textual information to files
    """
    def __init__(self, file_path: str) -> None:
        super().__init__(file_path, 'w')

    def write_line(self, line: str) -> None:
        """
        Writes a line to a file (including a new line symbol)

        :param line: Line to write
        :return: None
        """
        if self._file is None:
            raise IOError(f'Cannot write to file {self._file_path}')

        if not line.endswith('\n'):
            line += '\n'

        self._file.write(line)
        self._current_line = line
        self._current_line_index += 1

    @staticmethod
    def create(file_path: str) -> 'TextWriter':
        return TextWriter(file_path)

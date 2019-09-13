# -*- coding: utf-8 -*-
"""
WebVTT's subtitle parser
"""
from re import compile

from pyvtt.vttexc import InvalidItem
from pyvtt.vtttime import WebVTTTime
from pyvtt.comparablemixin import ComparableMixin
from pyvtt.compat import str, is_py2


# Workaround to compare regex pattern object type
PATTERN_TYPE = type(compile(''))


class WebVTTItem(ComparableMixin):
    """
    WebVTTItem(index, start, end, text, position)

    start, end -> WebVTTTime or coercible.
    text -> unicode: text content for item.
    position -> unicode: raw vtt "display coordinates" string
    """
    ITEM_PATTERN = str('%s --> %s%s\n%s\n')
    TIMESTAMP_SEPARATOR = '-->'

    def __init__(self, index=0, start=None, end=None, text='', position=''):
        try:
            # try to cast as int, but it's not mandatory
            self.index = int(index)
        except (TypeError, ValueError):
            self.index = index

        self.start = WebVTTTime.coerce(start or 0)
        self.end = WebVTTTime.coerce(end or 0)
        self.position = str(position)
        self.text = str(text)

    @property
    def duration(self):
        return self.end - self.start

    @property
    def text_without_tags(self):
        return self._text_tag_cleaner('<', '>')

    @property
    def text_without_brackets(self):
        return self._text_tag_cleaner('\[', '\]')

    @property
    def text_without_keys(self):
        return self._text_tag_cleaner('{', '}')

    def _text_tag_cleaner(self, before_delimiter, after_delimiter):
        def _line_tag_cleaner(line):
            if (line.startswith(before_delimiter) and
                line.count(before_delimiter) == 1 and
                    (line.count(after_delimiter) == 0 or
                     line.endswith(after_delimiter))):
                line = line[1:]
            if (line.endswith(after_delimiter) and
                    line.count(after_delimiter) == 1 and
                    line.count(before_delimiter) == 0):
                line = line[:-1]
            return line

        # Pre process line by line to avoid some ugly corner cases
        text = '\n'.join([_line_tag_cleaner(i) for i in self.text.split('\n')])
        return compile(r"{0}[^>]*?{1}".format(
            before_delimiter, after_delimiter)).sub('', text)

    @property
    def text_without_trailing_spaces(self):
        return self.text.strip()

    @property
    def characters_per_second(self):
        characters_count = len(self.text_without_tags.replace('\n', ''))
        try:
            return characters_count / (self.duration.ordinal / 1000.0)
        except ZeroDivisionError:
            return 0.0

    def text_with_replacements(self, replacements=[]):
        for replaced, replacement in replacements:
            if isinstance(replaced, PATTERN_TYPE):
                self.text = replaced.sub(replacement, self.text)
            else:
                self.text = self.text.replace(replaced, replacement)
        # Avoid trailing spaces or empty lines after all replacements
        self.text = self.text.strip()
        return self.text

    def __str__(self):
        position = ' %s' % self.position if self.position.strip() else ''
        return self.ITEM_PATTERN % (self.start, self.end, position, self.text)

    if is_py2:
        __unicode__ = __str__

        def __str__(self):
            raise NotImplementedError('Use unicode() instead!')

    def _cmpkey(self):
        return self.start, self.end

    def shift(self, *args, **kwargs):
        """
        shift(hours, minutes, seconds, milliseconds, ratio)

        Add given values to start and end attributes.
        All arguments are optional and have a default value of 0.
        """
        self.start.shift(*args, **kwargs)
        self.end.shift(*args, **kwargs)

    @classmethod
    def from_string(cls, source):
        return cls.from_lines(source.splitlines(True))

    @classmethod
    def from_lines(cls, lines):
        if len(lines) < 2:
            raise InvalidItem()
        # All cases are considered: '\n', '\r\n', '\r'
        lines = [l.rstrip("\n\r") for l in lines]
        lines[0] = lines[0].rstrip()
        index = None
        if cls.TIMESTAMP_SEPARATOR not in lines[0]:
            index = lines.pop(0)
        start, end, position = cls.split_timestamps(lines[0])
        body = '\n'.join(lines[1:])
        return cls(index, start, end, body, position)

    @classmethod
    def split_timestamps(cls, line):
        timestamps = line.split(cls.TIMESTAMP_SEPARATOR)
        if len(timestamps) != 2:
            raise InvalidItem()
        start, end_and_position = timestamps
        end_and_position = end_and_position.lstrip().split(' ', 1)
        end = end_and_position[0]
        position = end_and_position[1] if len(end_and_position) > 1 else ''
        return (s.strip() for s in (start, end, position))

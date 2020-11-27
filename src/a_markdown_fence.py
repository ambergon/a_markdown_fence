# coding:utf-8
"""
Fenced Code Extension for Python Markdown
=========================================
This extension adds Fenced Code Blocks to Python-Markdown.
See <https://Python-Markdown.github.io/extensions/fenced_code_blocks>
for documentation.
Original code Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).
All changes Copyright 2008-2014 The Python Markdown Project

License: [BSD](https://opensource.org/licenses/bsd-license.php)
Markdown Custom class extension for Python-Markdown
=========================================

>>> import markdown
>>> md = markdown.Markdown(extensions=['a_markdown_fence'])
>>> md.convert('')


"""

from textwrap import dedent
import markdown
from markdown import Extension
import re
from functools import wraps


FENCED_BLOCK_RE = re.compile(
    dedent(r'''
        (?P<fence>^(?:~{3,}|`{3,}))[ ]*                      # opening fence
        ((\{(?P<attrs>[^\}\n]*)\})?|                         # (optional {attrs} or
        (\.?(?P<lang>[\w#.+-]*))?[ ]*                        # optional (.)lang
        (hl_lines=(?P<quot>"|')(?P<hl_lines>.*?)(?P=quot))?) # optional hl_lines)
        [ ]*\n                                               # newline (end of opening fence)
        (?P<code>.*?)(?<=\n)                                 # the code block
        (?P=fence)[ ]*$                                      # closing fence
    '''),
    re.MULTILINE | re.DOTALL | re.VERBOSE
)
###{{{

#"を除去してk:vに
def _handle_double_quote(s, t):
    k, v = t.split('=', 1)
    return k, v.strip('"')

#'を
def _handle_single_quote(s, t):
    k, v = t.split('=', 1)
    return k, v.strip("'")

#=valueだけの場合?
def _handle_key_value(s, t):
    return t.split('=', 1)

#頭に[#]があれば
#頭に[:]があれば
def _handle_word(s, t):
    if t.startswith('.'):
        return '.', t[1:]
    if t.startswith('#'):
        return 'id', t[1:]
    if t.startswith(':'):
        return 'file_name', t[1:]
    return t, t

_scanner = re.Scanner([
    #'key=value'
    (r'[^ =]+=".*?"', _handle_double_quote),
    #"key=value"
    (r"[^ =]+='.*?'", _handle_single_quote),
    (r'[^ =]+=[^ =]+', _handle_key_value),
    (r'[^ =]+', _handle_word),
    (r' ', None)
])

def get_attrs(str):
    """ Parse attribute list and return a list of attribute tuples. """
    return _scanner.scan(str)[0]

###}}}

###{{{
def deprecated(message, stacklevel=2):
    def deprecated_decorator(func):
        @wraps(func)
        def deprecated_func(*args, **kwargs):
            warnings.warn(
                "'{}' is deprecated. {}".format(func.__name__, message),
                category=DeprecationWarning,
                stacklevel=stacklevel
            )
            return func(*args, **kwargs)
        return deprecated_func
    return deprecated_decorator


class Processor:
    def __init__(self, md=None):
        self.md = md

    @property
    @deprecated("Use 'md' instead.")
    def markdown(self):
        # TODO: remove this later
        return self.md

class Preprocessor(Processor):
    def run(self, lines):
        pass  # pragma: no cover

###}}}

###{{{
def parseBoolValue(value, fail_on_errors=True, preserve_none=False):
    """Parses a string representing bool value. If parsing was successful,
       returns True or False. If preserve_none=True, returns True, False,
       or None. If parsing was not successful, raises  ValueError, or, if
       fail_on_errors=False, returns None."""
    if not isinstance(value, string_type):
        if preserve_none and value is None:
            return value
        return bool(value)
    elif preserve_none and value.lower() == 'none':
        return None
    elif value.lower() in ('true', 'yes', 'y', 'on', '1'):
        return True
    elif value.lower() in ('false', 'no', 'n', 'off', '0', 'none'):
        return False
    elif fail_on_errors:
        raise ValueError('Cannot parse bool value: %r' % value)
###}}}



CONFIG = {
    'lang_prefix': ['language-', 'Prefix prepended to the language. Default: "language-"'],
    'pre_title_prefix': ['pre_title', 'Default: ""']
}
def getCONFIG(key, default=''):
    """ Return a setting for the given key or an empty string. """
    if key in CONFIG:
        return CONFIG[key][0]
    else:
        return default

def getCONFIGS():
    return {key: getCONFIG(key) for key in CONFIG.keys()}

class FencedCodeExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        md.preprocessors.register(FencedBlockPreprocessor(md, getCONFIGS()), 'fenced_code_block', 25)

class FencedBlockPreprocessor(Preprocessor):
    def __init__(self, md, config):
        self.md=md
        self.config = config
        self.use_attr_list = False
        self.bool_options = [
            'linenums',
            'guess_lang',
            'noclasses',
            'use_pygments'
        ]
    def run(self, lines):
        text = "\n".join(lines)
        while 1:
            #条件に引っかかる要素があるなら
            m = FENCED_BLOCK_RE.search(text)
            if m:

                pre_title=""
                pre_title_attr =''

                lang, id, classes, config = None, '', [], {}

                #```{attr}のタイプ
                if m.group('attrs'):
                    id, pre_title , classes, config = self.handle_attrs(get_attrs(m.group('attrs')))
                    if len(classes):
                        #classの最初の奴をlangageとして使う
                        lang = classes.pop(0)
                #```.pythonとかのタイプ
                else:
                    if m.group('lang'):
                        lang = m.group('lang')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlight the code

                id_attr = lang_attr = class_attr = kv_pairs = ''
                pre_title_attr = ''
                #langに文字があれば？
                #configのデフォル+lang
                if lang:
                    lang_attr = ' class="{}{}"'.format(self.config.get('lang_prefix', 'language-'), lang)
                if classes:
                    #残りをすべて
                    class_attr = ' class="{}"'.format(' '.join(classes))

                if pre_title:
                   pre_title_attr = ' {}="{}"'.format(self.config.get('pre_title_prefix', 'def'), pre_title)
                
                if id:
                    id_attr = ' id="{}"'.format(id)
                if self.use_attr_list and config and not config.get('use_pygments', False):
                    # Only assign key/value pairs to code element if attr_list ext is enabled, key/value pairs
                    # were defined on the code block, and the `use_pygments` key was not set to True. The
                    # `use_pygments` key could be either set to False or not defined. It is omitted from output.
                    kv_pairs = ' ' + ' '.join(
                        '{k}="{v}"'.format(k=k, v=v) for k, v in config.items() if k != 'use_pygments'
                    )
                code = '<pre{id}{cls}{pre_title}><code{lang}{kv}>{code}</code></pre>'.format(
                    id=id_attr,
                    cls=class_attr,
                    pre_title=pre_title_attr,
                    #pre_title=' lang="aaaaa"',
                    lang=lang_attr,
                    kv=kv_pairs,
                    code=self._escape(m.group('code'))
                )

                placeholder = self.md.htmlStash.store(code)
                text = '{}\n{}\n{}'.format(text[:m.start()],
                                           placeholder,
                                           text[m.end():])
            else:
                break
        return text.split("\n")

    def handle_attrs(self, attrs):
        """ Return tuple: (id, [list, of, classes], {configs}) """
        id = ''
        file_name = ''
        classes = []
        configs = {}
        for k, v in attrs:
            if k == 'id':
                id = v
            elif k == 'file_name':
                file_name = v
            elif k == '.':
                classes.append(v)
            elif k in self.bool_options:
                configs[k] = parseBoolValue(v, fail_on_errors=False, preserve_none=True)
            else:
                configs[k] = v
                
        return id , file_name, classes, configs

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(**kwargs):  # pragma: no cover
    return FencedCodeExtension(**kwargs)


if __name__ == "__main__":
    import doctest
    doctest.testmod(
            #verbose=True
            )
    

#!/usr/bin/env python
import pyflakes.checker
import compiler, sys
import os

def check(codeString, filename):
    """
    Check the Python source given by C{codeString} for flakes.

    @param codeString: The Python source to check.
    @type codeString: C{str}

    @param filename: The name of the file the source came from, used to report
        errors.
    @type filename: C{str}

    @return: The number of warnings emitted.
    @rtype: C{int}
    """
    # Since compiler.parse does not reliably report syntax errors, use the
    # built in compiler first to detect those.
    try:
        try:
            compile(codeString, filename, "exec")
        except MemoryError:
            # Python 2.4 will raise MemoryError if the source can't be
            # decoded.
            if sys.version_info[:2] == (2, 4):
                raise SyntaxError(None)
            raise
    except (SyntaxError, IndentationError), value:
        msg = value.args[0]

        (lineno, offset, text) = value.lineno, value.offset, value.text

        # If there's an encoding problem with the file, the text is None.
        if text is None:
            # Avoid using msg, since for the only known case, it contains a
            # bogus message that claims the encoding the file declared was
            # unknown.
            return ["%s: problem decoding source" % (filename, )]
        else:
            line = text.splitlines()[-1]

            if offset is not None:
                offset = offset - (len(text) - len(line))

            return ['%s:%d: %s' % (filename, lineno, msg)]
    else:
        # Okay, it's syntactically valid.  Now parse it into an ast and check
        # it.
        tree = compiler.parse(codeString)
        w = pyflakes.checker.Checker(tree, filename)

        lines = codeString.split('\n')
        messages = [message for message in w.messages
                    if lines[message.lineno-1].find('pyflakes:ignore') < 0]
        messages.sort(lambda a, b: cmp(a.lineno, b.lineno))

        return messages


def checkPath(filename):
    """
    Check the given path, printing out any warnings detected.

    @return: the number of warnings printed
    """
    try:
        return check(file(filename, 'U').read() + '\n', filename)
    except IOError, msg:
        return ["%s: %s" % (filename, msg.args[1])]
    
def checkPaths(filenames):
    warnings = []
    for arg in filenames:
        if os.path.isdir(arg):
            for dirpath, dirnames, filenames in os.walk(arg):
                for filename in filenames:
                    if filename.endswith('.py'):
                        warnings.extend(checkPath(os.path.join(dirpath, filename)))
        else:
            warnings.extend(checkPath(arg))
    return warnings

import settings

def run(*filenames):
    if not filenames:
        filenames = getattr(settings, 'PYFLAKES_DEFAULT_ARGS', ['apps'])
    warnings = checkPaths(filenames)
    for warning in warnings:
        print warning
    if warnings:
        print 'Total warnings: %d' % len(warnings)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(run(*sys.argv[1:]))
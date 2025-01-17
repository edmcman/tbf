import logging
import subprocess
import os
import time
import hashlib
import tempfile
import pycparser
import re
from struct import unpack
import codecs

from threading import Thread
from math import floor
import signal

parser = pycparser.CParser()
sym_var_prefix = '__sym_'

GCC_BUILTINS = [
    'cos',
    'sin',
    'tan',
    'acos',
    'asin',
    'atan',
    'atan2',
    'cosh',
    'sinh',
    'tanh',
    'acosh',
    'asinh',
    'atanh',
    'exp',
    'frexp',
    'ldexp',
    'log',
    'log10',
    'modf',
    'exp2',
    'expm1',
    'iologb',
    'log1p',
    'log2',
    'logb',
    'scalbn',
    'scalbln',
    'pow',
    'sqrt',
    'cbrt',
    'hypot',
    'erf',
    'erfc',
    'tgamma',
    'lgamma',
    'ceil',
    'floor',
    'fmod',
    'trunc',
    'round',
    'lround',
    'llround',
    'rint',
    'lrint',
    'nearbyint',
    'remainder',
    'remquo',
    'copysing',
    'nan',
    'nanf',
    'nanl',
    'nextafter',
    'nettoward',
    'fdim',
    'fmax',
    'fmal',
    'fmin',
    'fabs',
    'abs',
    'fma',
    'fpclassify',
    'fpclassifyf',
    'fpclassifyl',
    'isfinite',
    'isfinitef',
    'isfinitel',
    'finite',
    'finitef',
    'finitel',
    'isinf',
    'isinff',
    'isinfl',
    'isnan',
    'isnanf',
    'isnanl',
    'isnormal',
    'signbit',
    'signbitf',
    'signbitl',
    'isgreater',
    'isgreaterequal',
    'isless',
    'islessequal',
    'islessgreater',
    'isunordered',
    '_Exit',
    'acoshf',
    'acoshl',
    'acosh',
    'asinhf',
    'asinhl',
    'asinh',
    'atanhf',
    'atanhl',
    'atanh',
    'cabsf',
    'cabsl',
    'cabs',
    'cacosf',
    'cacoshf',
    'cacoshl',
    'cacosh',
    'cacosl',
    'cacos',
    'cargf',
    'cargl',
    'carg',
    'casinf',
    'casinhf',
    'casinhl',
    'casinh',
    'casinl',
    'casin',
    'catanf',
    'catanhf',
    'catanhl',
    'catanh',
    'catanl',
    'catan',
    'cbrtf',
    'cbrtl',
    'cbrt',
    'ccosf',
    'ccoshf',
    'ccoshl',
    'ccosh',
    'ccosl',
    'ccos',
    'cexpf',
    'cexpl',
    'cexp',
    'cimagf',
    'cimagl',
    'cimag',
    'clogf',
    'clogl',
    'clog',
    'conjf',
    'conjl',
    'conj',
    'copysignf',
    'copysignl',
    'copysign',
    'cpowf',
    'cpowl',
    'cpow',
    'cprojf',
    'cprojl',
    'cproj',
    'crealf',
    'creall',
    'creal',
    'csinf',
    'csinhf',
    'csinhl',
    'csinh',
    'csinl',
    'csin',
    'csqrtf',
    'csqrtl',
    'csqrt',
    'ctanf',
    'ctanhf',
    'ctanhl',
    'ctanh',
    'ctanl',
    'ctan',
    'erfcf',
    'erfcl',
    'erfc',
    'erff',
    'erfl',
    'erf',
    'exp2f',
    'exp2l',
    'exp2',
    'expm1f',
    'expm1l',
    'expm1',
    'fdimf',
    'fdiml',
    'fdim',
    'fmaf',
    'fmal',
    'fmaxf',
    'fmaxl',
    'fmax',
    'fma',
    'fminf',
    'fminl',
    'fmin',
    'hypotf',
    'hypotl',
    'hypot',
    'ilogbf',
    'ilogbl',
    'ilogb',
    'imaxabs',
    'isblank',
    'iswblank',
    'lgammaf',
    'lgammal',
    'lgamma',
    'llabs',
    'llrintf',
    'llrintl',
    'llrint',
    'llroundf',
    'llroundl',
    'llround',
    'log1pf',
    'log1pl',
    'log1p',
    'log2f',
    'log2l',
    'log2',
    'logbf',
    'logbl',
    'logb',
    'lrintf',
    'lrintl',
    'lrint',
    'lroundf',
    'lroundl',
    'lround',
    'nearbyintf',
    'nearbyintl',
    'nearbyint',
    'nextafterf',
    'nextafterl',
    'nextafter',
    'nexttowardf',
    'nexttowardl',
    'nexttoward',
    'remainderf',
    'remainderl',
    'remainder',
    'remquof',
    'remquol',
    'remquo',
    'rintf',
    'rintl',
    'rint',
    'roundf',
    'roundl',
    'round',
    'scalblnf',
    'scalblnl',
    'scalbln',
    'scalbnf',
    'scalbnl',
    'scalbn',
    'snprintf',
    'tgammaf',
    'tgammal',
    'tgamma',
    'truncf',
    'truncl',
    'trunc',
    'vfscanf',
    'vscanf',
    'vsnprintf',
    'acosf',
    'acosl',
    'asinf',
    'asinl',
    'atan2f',
    'atan2l',
    'atanf',
    'atanl',
    'ceilf',
    'ceill',
    'cosf',
    'coshf',
    'coshl',
    'cosl',
    'expf',
    'expl',
    'fabsf',
    'fabsl',
    'floorf',
    'floorl',
    'fmodf',
    'fmodl',
    'frexpf',
    'frexpl',
    'ldexpf',
    'ldexpl',
    'log10f',
    'log10l',
    'logf',
    'logl',
    'modfl',
    'modf',
    'powf',
    'powl',
    'sinf',
    'sinhf',
    'sinhl',
    'sinl',
    'sqrtf',
    'sqrtl',
    'tanf',
    'tanhf',
    'tanhl',
    'tanl',
    # Outside c99 and c89
    '_exit',
    'alloca',
    'bcmp',
    'bzero',
    'dcgettext',
    'dgettext',
    'dremf',
    'dreml',
    'drem',
    'exp10f',
    'exp10l',
    'exp10',
    'ffsll',
    'ffs',
    'fprintf_unlocked',
    'fputs_unlocked',
    'gammaf',
    'gammal',
    'gamma',
    'gammaf_r',
    'gammal_r',
    'gamma_r',
    'gettext',
    'index',
    'isascii',
    'j0f',
    'j0l',
    'j0',
    'j1f',
    'j1l',
    'j1',
    'jnf',
    'jnl',
    'jn',
    'lgammaf_r',
    'lgammal_r',
    'lgamma_r',
    'mempcpy',
    'pow10f',
    'pow10l',
    'pow10',
    'printf_unlocked',
    'rindex',
    'scalbf',
    'scalbl',
    'scalb',
    'signbit',
    'signbitf',
    'signbitl',
    'signbitd32',
    'signbitd64',
    'signbitd128',
    'significandf',
    'significandl',
    'significand',
    'sincosf',
    'sincosl',
    'sincos',
    'stpcpy',
    'stpncpy',
    'strcasecmp',
    'strdup',
    'strfmon',
    'strncasecmp',
    'strndup',
    'toascii',
    'y0f',
    'y0l',
    'y0',
    'y1f',
    'y1l',
    'y1',
    'ynf',
    'ynl',
    'yn',
    'abort',
    'abs',
    'acos',
    'asin',
    'atan2',
    'atan',
    'calloc',
    'ceil',
    'cosh',
    'cos',
    'exit',
    'exp',
    'fabs',
    'floor',
    'fmod',
    'fprintf',
    'fputs',
    'frexp',
    'fscanf',
    'labs',
    'ldexp',
    'log10',
    'log',
    'malloc',
    'memcmp',
    'memcpy',
    'memset',
    'modf',
    'modff',
    'modfl',
    'pow',
    'printf',
    'putchar',
    'puts',
    'scanf',
    'sinh',
    'sin',
    'snprintf',
    'sprintf',
    'sqrt',
    'sscanf',
    'strcat',
    'strchr',
    'strcmp',
    'strcpy',
    'strcspn',
    'strlen',
    'strncat',
    'strncmp',
    'strncpy',
    'strpbrk',
    'strrchr',
    'strspn',
    'strstr',
    'tanh',
    'tan',
    'vfprintf',
    'vprintf',
    'vsprintf'
]

IMPLICIT_FUNCTIONS = [
    '__VERIFIER_assume',
    '__VERIFIER_error',
    #stdio.h
    'fclose',
    'clearerr',
    'feof',
    'ferror',
    'fflush',
    'fgetpos',
    'fopen',
    'fread',
    'freopen',
    'fseek',
    'fsetpos',
    'ftell',
    'fwrite',
    'remove',
    'rename',
    'rewind',
    'setbuf',
    'setvbuf',
    'tmpfile',
    'tmpnam',
    'fprintf',
    'printf',
    'sprintf',
    'vfprintf',
    'vprintf',
    'vsprintf',
    'fscanf',
    'scanf',
    'sscanf',
    'fgetc',
    'fgets',
    'fputc',
    'fputs',
    'getc',
    'getchar',
    'gets',
    'putc',
    'putchar',
    'puts',
    'ungetc',
    'perror',
    #stdlib.h
    'atoi',
    'atof',
    'atol',
    'atoll',
    'strtod',
    'strtol',
    'strtoll',
    'strtoq',
    'strtold',
    'strtof',
    'strtoul',
    'strtoull',
    'calloc',
    'free',
    'malloc',
    'realloc',
    'alloca',
    'valloc',
    'abort',
    'atexit',
    'exit',
    'getenv',
    'system',
    'bsearch',
    'qsort',
    'abs',
    'div',
    'labs',
    'ldiv',
    'mblen',
    'mbstowcs',
    'mbtowc',
    'wcstombs',
    'wctomb',
    #string.h
    'memchr',
    'memcmp',
    'memcpy',
    'memmove',
    'memset',
    'strcat',
    'strncat',
    'strchr',
    'strcmp',
    'strncmp',
    'strcoll',
    'strcpy',
    'strncpy',
    'strcspn',
    'strerror',
    'strlen',
    'strpbrk',
    'strrchr',
    'strspn',
    'strstr',
    'strtok',
    'strxfrm',
    #fenv.h
    'feclearexcpt',
    'feraiseexcept',
    'fegetexceptflag',
    'fesetexceptflag',
    'fegetround',
    'fesetround',
    'fegetenv',
    'fesetenv',
    'feholdexcept',
    'feupdateenv',
    'fetestexcept',
    '__underflow',
    '__uflow',
    '__overflow',
    '_IO_getc',
    '_IO_putc',
    '_IO_feof',
    '_IO_ferror',
    '_IO_peekc_locked',
    '_IO_flockfile',
    '_IO_funlockfile',
    '_IO_ftrylockfile',
    '_IO_vfscanf',
    '_IO_fprintf',
    '_IO_padn',
    '_IO_seekoff',
    '_IO_seekpos',
    '_IO_free_backup_area'
] + GCC_BUILTINS + ['__' + g for g in GCC_BUILTINS
                   ] + ["__builtin__" + g for g in GCC_BUILTINS]


class MachineModel(object):

    def __init__(self, wordsize, name, short_size, int_size, long_size,
                 long_long_size, float_size, double_size, long_double_size,
                 compile_param):
        assert wordsize == 32 or wordsize == 64
        self._wordsize = wordsize
        self._name = name
        self.model = {
            'short': short_size,
            'int': int_size,
            'long': long_size,
            'long long': long_long_size,
            'float': float_size,
            'double': double_size,
            'long double': long_double_size
        }
        self._compile_param = compile_param

    @property
    def short_size(self):
        return self.model['short']

    @property
    def int_size(self):
        return self.model['int']

    @property
    def long_size(self):
        return self.model['long']

    @property
    def long_long_size(self):
        return self.model['long long']

    @property
    def float_size(self):
        return self.model['float']

    @property
    def double_size(self):
        return self.model['double']

    @property
    def long_double_size(self):
        return self.model['long double']

    @property
    def compile_parameter(self):
        return self._compile_param

    @property
    def is_64(self):
        return self._wordsize == 64

    @property
    def is_32(self):
        return self._wordsize == 32

    @property
    def name(self):
        return self._name

    @property
    def witness_key(self):
        return str(self._wordsize) + "bit"

    def get_size(self, data_type):
        if 'short' in data_type:
            return self.short_size
        elif 'long long' in data_type:
            return self.long_long_size
        elif 'long double' in data_type:
            return self.long_double_size
        elif 'long' in data_type:
            return self.long_size
        elif 'double' in data_type:
            return self.double_size
        elif 'float' in data_type:
            return self.float_size
        elif 'int' in data_type:
            return self.int_size
        else:
            raise AssertionError("Unhandled data type: " + data_type)


class TestCase(object):

    def __init__(self, name, origin_file, content):
        self._name = name
        self._origin = origin_file
        self._content = content

    @property
    def name(self):
        return self._name

    @property
    def origin(self):
        return self._origin

    @property
    def content(self):
        return self._content

    def __str__(self):
        return self.name + "(" + self.origin + ")"


class ConfigError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class InputGenerationError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class ParseError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class CompileError(Exception):

    def __init__(self, msg=None, cause=None):
        self.msg = msg
        self.cause = cause


class ExecutionResult(object):
    """Results of a subprocess execution."""

    def __init__(self, returncode, stdout, stderr):
        self._returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    @property
    def returncode(self):
        return self._returncode

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr


class Verdict(object):
    """Results of a test validation, either witness validation or test execution validation currently."""

    def __init__(self,
                 verdict,
                 test=None,
                 test_vector=None,
                 harness=None,
                 witness=None):
        self.verdict = verdict
        self.test = test
        self.test_vector = test_vector
        self.harness = harness
        self.witness = witness

    def is_positive(self):
        """
        Returns whether the verdict is positive, i.e., whether a target was found.
        :return: true if the verdict represents that a target was found, false otherwise
        """
        return self.verdict == FALSE

    def __str__(self):
        return self.verdict


class VerdictTrue(Verdict):

    def __init__(self):
        super().__init__(TRUE)


class VerdictFalse(Verdict):

    def __init__(self,
                 test_origin,
                 test_vector=None,
                 harness=None,
                 witness=None):
        super().__init__(FALSE, test_origin, test_vector, harness, witness)


class VerdictUnknown(Verdict):

    def __init__(self):
        super().__init__(UNKNOWN)


class TestVector(object):

    def __init__(self, name, origin_file):
        self.name = name
        self.origin = origin_file
        self.vector = list()

    def add(self, value, method=None):
        self.vector.append({'value': value, 'name': method})

    def __len__(self):
        return len(self.vector)

    def __str__(self):
        return self.origin + " (" + str(self.vector) + " )"


def shut_down(process):
    process.send_signal(signal.SIGKILL)
    returncode = process.wait()

    return returncode


def execute(command,
            quiet=False,
            env=None,
            err_to_output=True,
            stop_flag=None,
            input_str=None,
            timelimit=None):
    log_cmd = logging.debug if quiet else logging.info

    log_cmd(" ".join(command))

    p = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if input_str else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if err_to_output else subprocess.PIPE,
        universal_newlines=False,
        env=env)

    output = None
    err_output = None
    if stop_flag:
        stopwatch = Stopwatch()
        stopwatch.start()
        returncode = p.poll()
        while returncode is None:
            if stop_flag.is_set() or (timelimit and
                                      stopwatch.curr_s() > timelimit):
                returncode = shut_down(p)
            else:
                time.sleep(0.001)
                returncode = p.poll()
        output, err_output = p.communicate()
    else:
        try:
            if input_str and type(input_str) is not bytes:
                input_str = input_str.encode()
            output, err_output = p.communicate(
                input=input_str, timeout=timelimit if timelimit else None)
            returncode = p.poll()
        except subprocess.TimeoutExpired:
            logging.info("Timeout of %s s expired. Killing process.", timelimit)
            returncode = shut_down(p)
    # Decode output, but we can't decode error output, since it may contain undecodable bytes.
    output = output.decode() if output else ''
    logging.debug(output)
    logging.debug(err_output)

    return ExecutionResult(returncode, output, err_output)


def flatten(list_of_lists):
    return [i for l in list_of_lists for i in l]


def get_hash(filename):
    buf_size = 65536
    sha1 = hashlib.sha1()

    with open(filename, 'rb') as inp:
        data = inp.read(buf_size)
        while data:
            sha1.update(data)
            data = inp.read(buf_size)

    return sha1.hexdigest()


def get_machine_model(witness_file):
    with open(witness_file, 'r') as inp:
        for line in inp.readlines():
            if 'architecture' in line:
                if '32' in line:
                    return MACHINE_MODEL_32
                elif '64' in line:
                    return MACHINE_MODEL_64
                else:
                    raise AssertionError(
                        'Unknown architecture in witness line: ' + line)


def import_tool(tool_name):
    if '.' in tool_name:
        tool_module = tool_name
    else:
        tool_module = 'benchexec.tools.' + tool_name
    return __import__(tool_module, fromlist=['Tool']).Tool()


def get_cpachecker_options(witness_file):
    machine_model = get_machine_model(witness_file)
    if machine_model.is_32:
        machine_model = '-32'
    elif machine_model.is_64:
        machine_model = '-64'
    else:
        raise AssertionError('Unknown machine model: ' + machine_model.name)

    # yapf: disable
    return [
        '-setprop', 'witness.checkProgramHash=false',
        '-disable-java-assertions',
        '-heap', '4000M',
        '-setprop', 'cfa.simplifyCfa=false',
        '-setprop', 'cfa.allowBranchSwapping=false',
        '-setprop', 'cpa.predicate.ignoreIrrelevantVariables=false',
        '-setprop', 'cpa.predicate.refinement.performInitialStaticRefinement=false',
        '-setprop', 'counterexample.export.compressWitness=false',
        '-setprop', 'counterexample.export.assumptions.includeConstantsForPointers=false',
        '-setprop', 'analysis.summaryEdge=true',
        '-setprop', 'cpa.callstack.skipVoidRecursion=true',
        '-setprop', 'cpa.callstack.skipFunctionPointerRecursion=true',
        '-setprop', 'cpa.predicate.memoryAllocationsAlwaysSucceed=true',
        '-witness', witness_file,
        machine_model,
        '-spec', spec_file]
    # yapf: enable


def get_file_path(filename, temp_dir=True):
    if temp_dir:
        prefix = tmp
    else:
        prefix = output_dir
    return os.path.join(prefix, filename)


def get_file_name(filename):
    return os.path.basename(filename)


def get_env():
    return os.environ.copy()


def get_env_with_path_added(path_addition):
    env = os.environ.copy()
    env['PATH'] = path_addition + os.pathsep + env['PATH']
    return env


def get_assume_method():
    return 'void __VERIFIER_assume(int cond) {\n    if(!cond) {\n        abort();\n    }\n}\n'


def get_method_head(method_name, method_type, param_types):
    method_head = '{0} {1}('.format(method_type, method_name)
    params = list()
    for (idx, pt) in enumerate(param_types):
        if '...' in pt:
            params.append('...')
        elif pt != 'void':
            if '{}' not in pt:
                pt += " {}"
            params.append(pt.format("param{}".format(idx)))
        elif params:
            raise AssertionError("Void type parameter in method " + method_name)
    method_head += ', '.join(params)
    method_head += ')'
    return method_head


def get_input_vector(test_vector, escape_newline=False):
    input_vector = ''
    if escape_newline:
        newline = '\\n'
    else:
        newline = '\n'
    for item in test_vector.vector:
        if type(item['value']) is bytes and type(newline) is not bytes:
            newline = newline.encode()
            input_vector = input_vector.encode()
        input_vector += item['value'] + newline

    logging.debug("Input for test %s:", test_vector.name)
    logging.debug([l for l in input_vector.split(newline)][:-1])
    return input_vector


def convert_dec_to_hex(dec_value, byte_number=None):
    hex_value = hex(int(dec_value))
    pure_hex = hex_value[2:]

    if byte_number is not None:
        pure_hex = hex_value[2:]
        hex_size = len(pure_hex)
        necessary_padding = byte_number * 2 - hex_size
        if necessary_padding < 0:
            raise AssertionError("Value " + hex_value +
                                 " doesn't fit byte number " + byte_number)
        hex_value = "0x" + necessary_padding * '0' + pure_hex
    elif len(pure_hex) % 2 > 0:
        hex_value = "0x0" + pure_hex
    return hex_value


class Stopwatch(object):

    def __init__(self):
        self._intervals = list()
        self._current_start = None

    def start(self):
        assert not self._current_start
        # We have to count sleep time because of other processes we wait on!
        self._current_start = time.perf_counter()

    def stop(self):
        end_time = time.perf_counter()
        assert self._current_start
        time_elapsed = self._process(end_time - self._current_start)
        self._current_start = None
        self._intervals.append(time_elapsed)

    def is_running(self):
        return self._current_start is not None

    def curr_s(self):
        """ Return current time in seconds """
        assert self._current_start
        return int(
            floor(self._process(time.perf_counter() - self._current_start)))

    def _process(self, value):
        return round(value, 3)

    def sum(self):
        val = sum(self._intervals) if self._intervals else 0
        return self._process(val)

    def avg(self):
        val = sum(self._intervals) / len(self._intervals) if len(
            self._intervals) else 0
        return self._process(val)

    def min(self):
        val = min(self._intervals) if self._intervals else 0
        return self._process(val)

    def max(self):
        val = max(self._intervals) if self._intervals else 0
        return self._process(val)

    def __str__(self):
        str_rep = "{0} (s)".format(self.sum())
        if len(self._intervals) > 1:
            str_rep += " (Avg.: {0} s, Min.: {1} s, Max.: {2} s)".format(
                self.avg(), self.min(), self.max())
        return str_rep


def rewrite_cproblems(content):
    need_struct_body = False
    skip_asm = False
    in_attribute = False
    in_cxx_comment = False
    prepared_content = ''
    for line in [c + "\n" for c in content.split('\n')]:
        # remove C++-style comments
        if in_cxx_comment:
            if re.search(r'\*/', line):
                line = re.sub(r'.*\*/', '', line)
                in_cxx_comment = False
            else:
                line = ''
        else:
            line = re.sub(r'/\*.*?\*/', '', line)
        if re.search(r'/\*', line):
            line = re.sub(r'/\*.*', '', line)
            in_cxx_comment = True
        # remove __attribute__
        line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*[a-zA-Z0-9_, "\.]+\s*\)\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*sizeof\s*\([a-z ]+\)\s*\)\s*\)\)\s*', '', line)
        # line = re.sub(r'__attribute__\s*\(\(\s*[a-z_, ]+\s*\(\s*\([0-9]+\)\s*<<\s*\([0-9]+\)\s*\)\s*\)\)\s*', '', line)
        line = re.sub(r'__attribute__\s*\(\(.*\)\)\s*', '', line)
        if re.search(r'__attribute__\s*\(\(', line):
            line = re.sub(r'__attribute__\s*\(\(.*', '', line)
            in_attribute = True
        elif in_attribute:
            line = re.sub(r'.*\)\)', '', line)
            in_attribute = False
        # rewrite some GCC extensions
        line = re.sub(r'__extension__', '', line)
        line = re.sub(r'__restrict', '', line)
        line = re.sub(r'__restrict__', '', line)
        line = re.sub(r'__inline__', '', line)
        line = re.sub(r'__inline', '', line)
        line = re.sub(r'__const', 'const', line)
        line = re.sub(r'__signed__', 'signed', line)
        line = re.sub(r'__builtin_va_list', 'int', line)
        # a hack for some C-standards violating code in LDV benchmarks
        if need_struct_body and re.match(r'^\s*}\s*;\s*$', line):
            line = 'int __dummy; ' + line
            need_struct_body = False
        elif need_struct_body:
            need_struct_body = re.match(r'^\s*$', line) is not None
        elif re.match(r'^\s*struct\s+[a-zA-Z0-9_]+\s*{\s*$', line):
            need_struct_body = True
        # remove inline asm
        if re.match(r'^\s*__asm__(\s+volatile)?\s*\("([^"]|\\")*"[^;]*$', line):
            skip_asm = True
        elif skip_asm and re.search(r'\)\s*;\s*$', line):
            skip_asm = False
            line = '\n'
        if (skip_asm or re.match(
                r'^\s*__asm__(\s+volatile)?\s*\("([^"]|\\")*"[^;]*\)\s*;\s*$',
                line)):
            line = '\n'
        # remove asm renaming
        line = re.sub(r'__asm__\s*\(""\s+"[a-zA-Z0-9_]+"\)', '', line)
        prepared_content += line
    return prepared_content


def parse_file_with_preprocessing(file_content, machine_model, includes=[]):
    preprocessed_content = preprocess(file_content, machine_model, includes)
    preprocessed_content = rewrite_cproblems(preprocessed_content)
    ast = parser.parse(preprocessed_content)
    return ast


def preprocess(file_content, machine_model, includes=[]):
    mm_arg = machine_model.compile_parameter

    # -E : only preprocess
    # -o : output file name
    # -xc : Use C language
    # - : Read code from stdin
    preprocess_cmd = ['gcc', '-E', '-xc', mm_arg]
    for inc in includes:
        preprocess_cmd += ['-I', inc]
    final_cmd = preprocess_cmd + ['-std=gnu11', '-lm', '-']
    p = execute(
        final_cmd, err_to_output=False, input_str=file_content, quiet=False)
    if p.returncode != 0:
        final_cmd = preprocess_cmd + ['-std=gnu90', '-lm', '-']
        p = execute(
            final_cmd, err_to_output=False, input_str=file_content, quiet=False)
    return p.stdout


undefined_methods = None


def get_nondet_methods():
    return undefined_methods


def find_nondet_methods(filename, svcomp_only):
    global undefined_methods
    if undefined_methods is None:
        logging.debug("Finding undefined methods")
        with open(filename, 'r') as inp:
            file_content = inp.read()
        if not svcomp_only:
            try:
                undefined_methods = _find_undefined_methods(file_content)
            except pycparser.plyparser.ParseError as e:
                logging.warning(
                    "Parse failure with pycparser while parsing: %s", e)
                undefined_methods = _find_nondet_methods(file_content)
        else:
            undefined_methods = _find_nondet_methods(file_content)
        logging.debug("Undefined methods: %s", undefined_methods)
    return undefined_methods


def _find_undefined_methods(file_content):
    import tbf.ast_visitor as ast_visitor

    ast = parse_file_with_preprocessing(file_content, MACHINE_MODEL_32)

    func_decl_collector = ast_visitor.FuncDeclCollector()
    func_def_collector = ast_visitor.FuncDefCollector()

    func_decl_collector.visit(ast)
    function_declarations = func_decl_collector.func_decls
    func_def_collector.visit(ast)
    function_definitions = [f.name for f in func_def_collector.func_defs]
    function_definitions += IMPLICIT_FUNCTIONS

    undef_func_prepared = [
        f for f in function_declarations
        if ast_visitor.get_name(f) not in function_definitions
    ]
    undef_func_prepared = [_prettify(f) for f in undef_func_prepared]

    # List every undefined, but declared function only once.
    # This is necessary because there are a few SV-COMP programs that declare
    # functions multiple times.
    undef_func_names = set()
    undefined_functions = list()
    for f in undef_func_prepared:
        if f['name'] and f['name'] not in undef_func_names:
            undef_func_names.add(f['name'])
            undefined_functions.append(f)

    return undefined_functions


def _find_nondet_methods(file_content):
    if os.path.exists(file_content):
        with open(file_content, 'r') as inp:
            content = inp.read()
    else:
        content = file_content
    method_names = set([s[:-2] for s in nondet_pattern.findall(content)])

    functions = list()
    for method_name in method_names:
        method_type = _get_return_type(method_name)
        functions.append({
            'name': method_name,
            'type': method_type,
            'params': []
        })
    return functions


def _get_return_type(verifier_nondet_method):
    assert verifier_nondet_method.startswith('__VERIFIER_nondet_')
    assert verifier_nondet_method[-2:] != '()'
    m_type = verifier_nondet_method[len('__VERIFIER_nondet_'):].lower()
    if m_type == 'bool':
        m_type = '_Bool'
    elif m_type == 'u32':
        m_type = 'unsigned int'
    elif m_type == 'u16':
        m_type = 'unsigned short'
    elif m_type == 'u8':
        m_type = 'unsigned char'
    elif m_type == 'unsigned':  # unsigned is a synonym for unsigned int, so recall the method with that
        m_type = 'unsigned int'
    elif m_type[0] == 'u':  # resolve uint to unsigned int (e.g.)
        m_type = 'unsigned ' + m_type[1:]
    elif m_type == 'pointer':
        m_type = 'void *'
    elif m_type == 'pchar':
        m_type = 'char *'
    elif m_type == 's8':
        m_type = 'char'
    return m_type


def _prettify(func_def):
    import tbf.ast_visitor as ast_visitor
    name = ast_visitor.get_name(func_def)
    return_type = ast_visitor.get_type(func_def.type)
    params = list()
    if func_def.args:
        for parameter in func_def.args.params:
            param_type = ast_visitor.get_type(parameter)
            params.append(param_type)
    return {'name': name, 'type': return_type, 'params': params}


def get_sym_var_name(method_name):
    name = sym_var_prefix + method_name
    logging.debug("Getting sym var name for method %s: %s", method_name, name)
    return name


def get_corresponding_method_name(sym_var_name):
    name = sym_var_name[len(sym_var_prefix):]
    logging.debug("Getting method name for %s: %s", sym_var_name, name)
    return name


def convert_to_int(value, method_name):
    assert undefined_methods is not None
    if type(value) is str and value.startswith('\'') and value.endswith('\''):
        value = value[1:-1]
    value = codecs.decode(value, 'unicode_escape').encode('latin1')
    corresponding_method_singleton_list = [
        m for m in undefined_methods if m['name'] == method_name
    ]
    if len(corresponding_method_singleton_list) == 0:
        raise AssertionError(
            "Didn't find {} in list of undefined methods: {}".format(
                method_name, undefined_methods))
    corresponding_method = corresponding_method_singleton_list[0]
    # The type of the symbolic variable may be different from the method return type,
    # but must be ultimately cast to the method return type,
    # so this is fine - unless we have undefined behavior prior to this point due to a downcast of the variable type.
    # In that case, hope is already lost.
    value_type = corresponding_method['type']
    data_format = '<'  # Klee output uses little endian format
    if value_type == 'char' or value_type == 'signed char':

        # b == signed char. There's also 'c' == 'char', but that translates to a python character and not to an int
        data_format += 'b'
    elif value_type == 'unsigned char':
        data_format += 'B'
    elif value_type == '_Bool' or value_type == 'bool':
        data_format += 'b'
    elif value_type == 'short' or value_type == 'signed short':
        data_format += 'h'
    elif value_type == 'unsigned short':
        data_format += 'H'
    elif value_type == 'int' or value_type == 'signed int':
        data_format += 'i'
    elif value_type == 'unsigned int':
        data_format += 'I'
    elif value_type == 'float':
        data_format += 'f'
    elif value_type == 'double':
        data_format += 'd'
    elif '*' in value_type:
        data_format = 'P'
    elif value_type == 'long long' or value_type == 'signed long long':
        data_format += 'q'
    elif value_type == 'unsigned long long':
        data_format += 'Q'
    elif value_type == 'long' or value_type == 'signed long':
        data_format += 'q'
    else:
        logging.debug('Converting type %s using type unsigned long ',
                      value_type)
        data_format += 'Q'
    logging.debug("Converting value %s according to data format %s", value,
                  data_format)
    return unpack(data_format, value)


def get_format_specifier(method_type):
    specifier = '%'
    # Length modifiers
    if 'short' in method_type:
        specifier += 'h'
    elif 'char' in method_type and 'unsigned char' not in method_type:
        specifier += 'hh'
    elif 'long long' in method_type:
        specifier += 'll'
    elif 'long double' in method_type:
        specifier += 'L'
    elif 'long' in method_type:
        specifier += 'l'
    elif 'size_t' in method_type:
        specifier += 'z'

    # Type specifier
    if '*' in method_type:
        specifier += 'p'
    if 'unsigned char' in method_type:
        specifier += 'c'
    if 'float' in method_type or 'double' in method_type:
        specifier += 'f'
    elif 'unsigned' in method_type:
        specifier += 'u'
    elif 'int' in method_type or 'long' in method_type or 'short' in method_type or 'char' in method_type:
        specifier += 'd'
    else:
        logging.debug('Using type unsigned long to read stdin for type %s',
                      method_type)
        specifier = '%lu'
    return specifier


class Counter(object):

    def __init__(self):
        self._count = 0

    @property
    def count(self):
        return self._count

    def inc(self, amount=1):
        self._count += amount

    def __str__(self):
        return str(self.count)


class Constant(object):

    def __init__(self, value=None):
        self.value = value

    def __str__(self):
        return str(self.value)


class Statistics(object):

    def __init__(self, title):
        self._title = title
        self._stats = list()

    @property
    def title(self):
        return self._title

    def add_value(self, property, value):
        assert property not in [p for (p, v) in self._stats]
        self._stats.append((property, value))

    @property
    def stats(self):
        return self._stats

    def __str__(self):
        str_rep = '---- ' + self._title + ' ----\n'
        str_rep += '\n'.join([p + ': ' + str(v) for (p, v) in self._stats])
        return str_rep


class StatisticsPool(object):

    def __init__(self):
        self._stat_objects = list()

    @property
    def stats(self):
        return self._stat_objects

    def new(self, title):
        stat = Statistics(title)
        self._stat_objects.append(stat)
        return stat

    def __str__(self):
        return '\n\n'.join([str(s) for s in self._stat_objects])


error_string = "Error found."
error_return = 107
error_method = '__VERIFIER_error'
spec_file = os.path.join(os.path.dirname(__file__), "ReachSafety.prp")
output_dir = os.path.abspath('./output')
tmp = tempfile.mkdtemp()
nondet_pattern = re.compile('__VERIFIER_nondet_.+?\(\)')

FALSE = 'false'
UNKNOWN = 'unknown'
TRUE = 'true'
ERROR = 'error'

MACHINE_MODEL_32 = MachineModel(32, "32 bit linux", 2, 4, 4, 8, 4, 8, 12,
                                '-m32')
MACHINE_MODEL_64 = MachineModel(64, "64 bit linux", 2, 4, 8, 8, 4, 8, 16,
                                '-m64')

if not os.path.exists(output_dir):
    os.mkdir(output_dir)


def found_err(run_result):
    return run_result.stderr and error_string.encode() in run_result.stderr


def get_prepared_name(filename, tool_name):
    prepared_name = '.'.join(
        os.path.basename(filename).split('.')[:-1] + [tool_name, 'c'])
    prepared_name = get_file_path(prepared_name, temp_dir=True)
    return prepared_name

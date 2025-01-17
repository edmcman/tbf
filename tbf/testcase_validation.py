from abc import abstractmethod, ABCMeta
import tbf.witness_generation as wit_gen
import tbf.harness_generation as harness_gen
import logging
import tbf.utils as utils
import os
from time import sleep
import re
from tbf.utils import FALSE, UNKNOWN, ERROR

valid_validators = ['cpachecker', 'uautomizer', 'cpa-w2t', 'fshell-w2t']


class ValidationConfig(object):

    def __init__(self, args):
        self.machine_model = args.machine_model

        self.use_execution = args.execution_validation
        self.use_witness_validation = args.witness_validation
        self.witness_validators = args.validators if args.validators else []

        self.use_klee_replay = False
        if args.klee_replay_validation:
            if args.input_generator != "klee":
                raise utils.ConfigError(
                    "Klee-replay only works with klee as tester")
            else:
                logging.warning(
                    "Klee-replay only supports the machine architecture! Machine model specified not respected."
                )
                self.use_klee_replay = True

        if self.witness_validators and not self.use_witness_validation:
            raise utils.ConfigError(
                "Validators specified but no witness validation used (--witness-validation)."
            )
        elif self.use_witness_validation and not self.witness_validators:
            logging.warning(
                "Witness validation used and no validator specified. Only generating witnesses."
            )
        elif self.witness_validators:
            for validator in self.witness_validators:
                if validator.lower() not in valid_validators:
                    raise utils.ConfigError(
                        "Validator not in list of known validators:"
                        "{0} not in {1}".format(validator, valid_validators))
        elif not self.use_witness_validation and not self.use_execution and not self.use_klee_replay:
            logging.info(
                "No validation technique specified. If you want TBF to check whether generated tests"
                " uncover a specification violation, provide one of the following parameters:"
                " --execution, --witness-validation, --klee-replay (KLEE only)")

        self.convert_to_int = args.write_integers
        self.naive_verification = args.naive_verification

        self.measure_coverage = args.report_coverage


class TestValidator(object):

    __metaclass__ = ABCMeta

    def __init__(self, validation_config, input_generator):
        self._nondet_var_map = None
        self.machine_model = validation_config.machine_model
        self.config = validation_config
        self.witness_creator = wit_gen.WitnessCreator()
        self.harness_creator = harness_gen.HarnessCreator()
        self._input_generator = input_generator

        self.naive_verification = validation_config.naive_verification

        # If a void appears in a line, there must be something between
        # the void and the __VERIFIER_error() symbol - otherwise
        # it is a function definition/declaration.
        self.error_method_pattern = re.compile(
            '((?!void).)*(void.*\S.*)?__VERIFIER_error\(\) *;.*')

        self.statistics = utils.Statistics('Test Validator ' + self.get_name())
        self.timer_validation = utils.Stopwatch()
        self.statistics.add_value('Time for validation', self.timer_validation)
        self.timer_witness_validation = utils.Stopwatch()
        self.statistics.add_value('Time for witness validation',
                                  self.timer_witness_validation)
        self.counter_size_witnesses = utils.Counter()
        self.statistics.add_value('Total size of witnesses',
                                  self.counter_size_witnesses)
        self.timer_execution_validation = utils.Stopwatch()
        self.statistics.add_value('Time for execution validation',
                                  self.timer_execution_validation)
        self.counter_size_harnesses = utils.Counter()
        self.statistics.add_value('Total size of harnesses',
                                  self.counter_size_harnesses)

        self.timer_vector_gen = utils.Stopwatch()
        self.statistics.add_value("Time for test vector generation",
                                  self.timer_vector_gen)
        self.counter_handled_test_cases = utils.Counter()
        self.statistics.add_value('Number of looked-at test cases',
                                  self.counter_handled_test_cases)

        self.final_test_vector_size = utils.Constant()
        self.statistics.add_value("Size of successful test vector",
                                  self.final_test_vector_size)

    def get_error_lines(self, program_file):
        with open(program_file, 'r') as inp:
            content = inp.readlines()

        err_lines = list()
        for line_num, line in enumerate(content, start=1):
            # Try to differentiate definition from call
            # through the 'void' condition
            if self.error_method_pattern.match(line):
                err_lines.append(line_num)
        assert err_lines  # Asser that there is at least one error call
        return err_lines

    @abstractmethod
    def get_name(self):
        pass

    def create_all_witnesses(self, program_file, new_test_cases):
        created_content = []
        nondet_methods = utils.get_nondet_methods()
        if len(new_test_cases) > 0:
            logging.info("Looking at %s new test files.", len(new_test_cases))
        empty_case_handled = False
        for test_case in new_test_cases:
            logging.debug('Looking at test case %s .', test_case)
            test_vector = self.get_test_vector(test_case)
            if test_vector or not empty_case_handled:
                if not test_vector:
                    test_vector = utils.TestVector(test_case.name,
                                                   test_case.origin)
                    empty_case_handled = True
                new_content = self.create_witness(program_file, test_case.name,
                                                  test_vector, nondet_methods)
                new_content['vector'] = test_vector
                new_content['origin'] = test_case.origin
                created_content.append(new_content)
            else:
                logging.info("Test vector was not generated for %s", test_case)
        return created_content

    def create_witness(self, program_file, test_name, test_vector,
                       nondet_methods):
        """
        Creates a witness for the test file produced by crest.
        Test files produced by our version of crest specify one test value per
        line, without any mention of the variable the value is assigned to.
        Because of this, we have to build a fancy witness automaton of the
        following format: For each test value specified in the test file, there
        is one precessor and one successor state. These two states are
        connected by one transition for each call to a CREST_x(..) function.
        Each of these transitions has the assumption, that the variable
        specified in the corresponding CREST_x(..) function has the current
        test value.
        """
        witness = self.witness_creator.create_witness(
            producer=self.get_name(),
            program_file=program_file,
            test_vector=test_vector,
            nondet_methods=nondet_methods,
            machine_model=self.machine_model,
            error_lines=self.get_error_lines(program_file))

        witness_file = test_name + ".witness.graphml"
        witness_file = utils.get_file_path(witness_file)

        return {'name': witness_file, 'content': witness}

    def decide_final_verdict(self, final_result):
        if final_result.is_positive() or not self.naive_verification:
            return final_result
        else:
            return utils.VerdictTrue()

    def create_all_test_vectors(self, new_test_cases):
        all_vectors = list()
        if len(new_test_cases) > 0:
            logging.info("Looking at %s new test files.", len(new_test_cases))
        for test_case in new_test_cases:
            logging.debug('Looking at test case %s .', test_case)
            assert os.path.exists(test_case.origin)
            test_vector = self.get_test_vector(test_case)
            all_vectors.append(test_vector)
        return all_vectors

    def create_harness(self, test_name, test_vector, nondet_methods):
        harness = self.harness_creator.create_harness(
            nondet_methods=nondet_methods,
            error_method=utils.error_method,
            test_vector=test_vector)
        harness_file = test_name + '.harness.c'
        harness_file = utils.get_file_path(harness_file)

        return {'name': harness_file, 'content': harness}

    @abstractmethod
    def _get_test_vector(self, test_case):
        pass

    def get_test_vector(self, test_case):
        self.timer_vector_gen.start()
        try:
            return self._get_test_vector(test_case)
        finally:
            self.timer_vector_gen.stop()

    def _get_test_cases(self, visited_tests, tests_directory):
        if tests_directory is None:
            return self._input_generator.get_test_cases(visited_tests)
        else:
            return self._input_generator.get_test_cases(visited_tests,
                                                        tests_directory)

    def _perform_validation(self, program_file, validator, validator_method,
                            is_ready_func, stop_event, tests_directory):
        visited_tests = set()
        result = list()
        while not is_ready_func() and not stop_event.is_set():
            new_test_cases = self._get_test_cases(visited_tests,
                                                  tests_directory)
            try:
                result = validator_method(program_file, validator,
                                          new_test_cases)
                if result.is_positive():
                    return result
                else:
                    new_test_case_names = [t.name for t in new_test_cases]
                    visited_tests = visited_tests.union(new_test_case_names)
                sleep(0.001)  # Sleep for 1 millisecond
            except utils.InputGenerationError:
                # Just capture here and retry as long as the thread is alive
                pass

        if not stop_event.is_set():
            new_test_cases = self._get_test_cases(visited_tests,
                                                  tests_directory)
            result = validator_method(program_file, validator, new_test_cases)
        return self.decide_final_verdict(result)

    def perform_klee_replay_validation(self, program_file, is_ready_func,
                                       stop_event, tests_directory):
        validator = KleeReplayRunner(self.config.machine_model)
        return self._perform_validation(program_file, validator, self._k,
                                        is_ready_func, stop_event,
                                        tests_directory)

    def perform_execution_validation(self, program_file, is_ready_func,
                                     stop_event, tests_directory):

        if self.config.measure_coverage:
            validator = CoverageMeasuringExecutionRunner(
                self.config.machine_model, self.get_name())
        else:
            validator = ExecutionRunner(self.config.machine_model,
                                        self.get_name())

        try:
            return self._perform_validation(program_file, validator, self._hs,
                                            is_ready_func, stop_event,
                                            tests_directory)
        finally:
            if type(validator) is CoverageMeasuringExecutionRunner:
                lines_ex, branch_ex, branch_taken = validator.get_coverage(
                    program_file)
                self.statistics.add_value("Statements covered", lines_ex)
                self.statistics.add_value("Branch conditions executed",
                                          branch_ex)
                self.statistics.add_value("Branches covered", branch_taken)

    def perform_witness_validation(self, program_file, is_ready_func,
                                   stop_event, tests_directory):
        validator = ValidationRunner(self.config.witness_validators)
        return self._perform_validation(program_file, validator, self._m,
                                        is_ready_func, stop_event,
                                        tests_directory)

    def _hs(self, program_file, validator, new_test_cases):
        test_vectors = self.create_all_test_vectors(new_test_cases)

        for vector in test_vectors:
            self.timer_execution_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(program_file, vector)
            finally:
                self.timer_execution_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()

            logging.debug('Results for %s: %s', vector, str(verdicts))
            if any([v == FALSE for v in verdicts]):
                self.final_test_vector_size.value = len(vector)
                return utils.VerdictFalse(vector, vector)
        return utils.VerdictUnknown()

    def _k(self, program_file, validator, new_test_cases):

        for test in new_test_cases:
            self.timer_execution_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(program_file, test)
            finally:
                self.timer_execution_validation.stop()
                self.timer_validation.stop()
            self.counter_handled_test_cases.inc()

            logging.debug('Results for %s: %s', test, str(verdicts))
            if any([v == FALSE for v in verdicts]):
                return utils.VerdictFalse(test)
        return utils.VerdictUnknown()

    def _m(self, program_file, validator, new_test_cases):
        produced_witnesses = self.create_all_witnesses(program_file,
                                                       new_test_cases)
        for witness in produced_witnesses:
            logging.debug('Looking at witness %s .', witness['name'])
            witness_name = witness['name']
            content_to_write = witness['content']
            self.counter_size_witnesses.inc(len(content_to_write))
            with open(witness_name, 'w+') as outp:
                outp.write(witness['content'])
            self.timer_witness_validation.start()
            self.timer_validation.start()
            try:
                verdicts = validator.run(program_file, witness_name)
            finally:
                self.timer_witness_validation.stop()
                self.timer_validation.stop()

            self.counter_handled_test_cases.inc()
            logging.debug('Results for %s: %s', witness_name, str(verdicts))
            if any(['false' in v.lower() for v in verdicts]):
                self.final_test_vector_size.value = len(witness['vector'])
                return utils.VerdictFalse(witness['origin'], witness['vector'],
                                          None, witness_name)

        return utils.VerdictUnknown()

    def check_inputs(self,
                     program_file,
                     is_ready_func,
                     stop_event,
                     tests_directory=None):
        logging.debug('Checking inputs for file %s', program_file)
        logging.debug('Considering test case directory %s', tests_directory)
        result = None

        if self.config.use_klee_replay:
            result = self.perform_klee_replay_validation(
                program_file, is_ready_func, stop_event, tests_directory)
            logging.info("Klee-replay validation says: " + str(result))

        if (not result or
                not result.is_positive()) and self.config.use_execution:
            result = self.perform_execution_validation(
                program_file, is_ready_func, stop_event, tests_directory)
            logging.info("Execution validation says: " + str(result))

        if (not result or not result.is_positive()
           ) and self.config.use_witness_validation:
            result = self.perform_witness_validation(
                program_file, is_ready_func, stop_event, tests_directory)
            logging.info("Witness validation says: " + str(result))

        if result is None:
            return utils.VerdictUnknown(), None

        elif result.is_positive():
            stop_event.set()
            if result.test_vector is None:
                result.test_vector = self.get_test_vector(result.test)
            # This currently won't work with AFL due to its string-style input
            if result.witness is None and 'afl' not in self.get_name().lower():
                nondet_methods = utils.get_nondet_methods()
                witness = self.create_witness(program_file, result.test.origin,
                                              result.test_vector, nondet_methods)
                with open(witness['name'], 'w+') as outp:
                    outp.write(witness['content'])
                result.witness = witness['name']
            if result.harness is None:
                nondet_methods = utils.get_nondet_methods()
                harness = self.create_harness(result.test_vector.origin,
                                              result.test_vector, nondet_methods)
                with open(harness['name'], 'wb+') as outp:
                    outp.write(harness['content'])

                result.harness = harness['name']

        return result, self.statistics


class ExecutionRunner(object):

    def __init__(self, machine_model, producer_name):
        self.machine_model = machine_model
        self.harness = None
        self.producer = producer_name
        self.harness_generator = harness_gen.HarnessCreator()
        self.harness_file = 'harness.c'

    def _get_compile_cmd(self,
                         program_file,
                         harness_file,
                         output_file,
                         c_version='gnu11'):
        mm_arg = self.machine_model.compile_parameter
        cmd = ['gcc']
        cmd += [
            '-std={}'.format(c_version), mm_arg, '-D__alias__(x)=', '-o',
            output_file, '-include', program_file, harness_file, '-lm'
        ]

        return cmd

    def compile(self, program_file, harness_file, output_file):
        compile_cmd = self._get_compile_cmd(program_file, harness_file,
                                            output_file)
        compile_result = utils.execute(compile_cmd, quiet=True)

        if compile_result.returncode != 0:
            compile_cmd = self._get_compile_cmd(program_file, harness_file,
                                                output_file, 'gnu90')
            compile_result = utils.execute(
                compile_cmd, quiet=True, err_to_output=False)

            if compile_result.returncode != 0:
                raise utils.CompileError(
                    "Compilation failed for harness {}".format(harness_file))

        return output_file

    def _get_run_cmd(self, executable):
        return [executable]

    def get_executable_harness(self, program_file):
        if not self.harness:
            self.harness = self._create_executable_harness(program_file)
        return self.harness

    def _create_executable_harness(self, program_file):
        nondet_methods = utils.get_nondet_methods()
        harness_content = self.harness_generator.create_harness(
            nondet_methods, utils.error_method)
        with open(self.harness_file, 'wb+') as outp:
            outp.write(harness_content)
        output_file = utils.get_file_path('a.out', temp_dir=True)
        return self.compile(program_file, self.harness_file, output_file)

    def run(self, program_file, test_vector):
        executable = self.get_executable_harness(program_file)
        input_vector = utils.get_input_vector(test_vector)

        if executable:
            run_cmd = self._get_run_cmd(executable)
            run_result = utils.execute(
                run_cmd,
                quiet=True,
                err_to_output=False,
                input_str=input_vector,
                timelimit=5)

            if utils.found_err(run_result):
                return [FALSE]
            else:
                return [UNKNOWN]
        else:
            return [ERROR]


class CoverageMeasuringExecutionRunner(ExecutionRunner):

    def _get_compile_cmd(self,
                         program_file,
                         harness_file,
                         output_file,
                         c_version='gnu11'):
        cmd = super()._get_compile_cmd(program_file, harness_file, output_file,
                                       c_version)
        cmd += ['-fprofile-arcs', '-ftest-coverage']

        return cmd

    @staticmethod
    def _get_gcov_val(gcov_line):
        stat = gcov_line.split(':')[1]
        measure_end = stat.find('of ')
        return stat[:measure_end] + "(" + stat[measure_end:] + ")"

    def get_coverage(self, program_file):
        cmd = ['gcov', '-bc', self.harness_file]
        res = utils.execute(cmd, quiet=False, err_to_output=False)
        full_cov = res.stdout.splitlines()

        program_name = os.path.basename(program_file)
        lines_executed = None
        branches_executed = None
        branches_taken = None
        for number, line in enumerate(full_cov):
            if line.startswith('File') and program_name in line:
                lines_executed = self._get_gcov_val(full_cov[number + 1])
                branches_executed = self._get_gcov_val(full_cov[number + 2])
                branches_taken = self._get_gcov_val(full_cov[number + 3])
                break

        return lines_executed, branches_executed, branches_taken


class KleeReplayRunner(object):

    def __init__(self, machine_model):
        self.machine_model = machine_model
        self.executable_name = './a.out'
        self.executable = None
        if os.path.exists(self.executable_name):
            os.remove(self.executable_name)

    def run(self, program_file, test_case):
        from tbf.tools import klee

        klee_prepared_file = utils.get_prepared_name(program_file, klee.name)
        c_version = 'gnu11'
        if not self.executable:
            compile_cmd = ['gcc']
            compile_cmd += [
                '-std={}'.format(c_version), "-L", klee.lib_dir,
                '-D__alias__(x)=', '-o', self.executable_name,
                klee_prepared_file, '-lkleeRuntest', '-lm'
            ]
            result = utils.execute(compile_cmd)
            if result.returncode != 0:
                c_version = 'gnu90'
                compile_cmd = ['gcc']
                compile_cmd += [
                    '-std={}'.format(c_version), "-L", klee.lib_dir,
                    '-D__alias__(x)=', '-o', self.executable_name,
                    klee_prepared_file, '-lkleeRuntest', '-lm'
                ]
            self.executable = self.executable_name

        if not os.path.exists(self.executable_name):
            return [ERROR]

        curr_env = utils.get_env()
        curr_env['KTEST_FILE'] = test_case.origin

        result = utils.execute(
            [self.executable], env=curr_env, err_to_output=False)

        if utils.found_err(result):
            return [FALSE]
        else:
            return [UNKNOWN]


class ValidationRunner(object):

    def __init__(self, validators):
        self.validators = list()
        validators_used = set()
        for val in [v.lower() for v in validators]:
            if val == 'cpachecker' and 'cpachecker' not in validators_used:
                self.validators.append(CPAcheckerValidator())
                validators_used.add('cpachecker')
            elif val == 'uautomizer' and 'uautomizer' not in validators_used:
                self.validators.append(UAutomizerValidator())
                validators_used.add('uautomizer')
            elif val == 'cpa-w2t' and 'cpa-w2t' not in validators_used:
                self.validators.append(CpaW2t())
                validators_used.add('cpa-w2t')
            elif val == 'fshell-w2t' and 'fshell-w2t' not in validators_used:
                self.validators.append(FShellW2t())
                validators_used.add('fshell-w2t')
            else:
                raise utils.ConfigError('Invalid validator list: ' + validators)

    def run(self, program_file, witness_file):
        results = []
        for validator in self.validators:
            logging.debug("Running %s on %s", validator, witness_file)
            result = validator.validate(program_file, witness_file)
            results.append(result)

        return results


class Validator(object):

    __metaclass__ = ABCMeta

    def __init__(self, tool_name):
        self.tool = utils.import_tool(tool_name)

    def validate(self, program_file, witness_file):
        # err_to_output=True is important so that messages to stderr are in correct relation to messages to stdout!
        # This may be important for determining the run result.
        cmd_result = utils.execute(
            self._get_cmd(program_file, witness_file),
            quiet=True,
            err_to_output=True)

        returncode = cmd_result.returncode
        # Execute returns a negative returncode -N if the process was killed by signal N
        if returncode < 0:
            returnsignal = -returncode
        else:
            returnsignal = 0

        if cmd_result.stderr:
            tool_output = cmd_result.stderr.split('\n')
        else:
            tool_output = list()
        tool_output += cmd_result.stdout.split('\n')
        # Remove last line if empty. FShell expects no empty line at the end.
        if len(tool_output) >= 1 and not tool_output[-1]:
            tool_output = tool_output[:-1]
        validation_result = self.tool.determine_result(
            returncode, returnsignal, tool_output, isTimeout=False)
        return validation_result

    @abstractmethod
    def _get_cmd(self, program_file, witness_file):
        pass


class CPAcheckerValidator(Validator):

    def __init__(self):
        super().__init__('cpachecker')
        self.executable = None  # executable will compile CPAchecker when called, so only do this if we really validate
        self.cpa_directory = None

    def _get_cmd(self, program_file, witness_file):
        if not self.executable:
            import shutil
            self.executable = self.tool.executable()
            self.cpa_directory = os.path.join(
                os.path.dirname(self.executable), '..')
            config_copy_dir = utils.get_file_path('config', temp_dir=True)
            if not os.path.exists(config_copy_dir):
                copy_dir = os.path.join(self.cpa_directory, 'config')
                shutil.copytree(copy_dir, config_copy_dir)
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witnessValidation', program_file]


class UAutomizerValidator(Validator):

    def __init__(self):
        super().__init__('ultimateautomizer')
        self.executable = self.tool.executable()

    def _get_cmd(self, program_file, witness_file):
        machine_model = utils.get_machine_model(witness_file)
        if machine_model.is_32:
            machine_model = '32bit'
        elif machine_model.is_64:
            machine_model = '64bit'
        else:
            raise AssertionError("Unhandled machine model: " + machine_model)

        cmd = [
            self.executable, '--validate', witness_file, utils.spec_file,
            machine_model, program_file
        ]
        return cmd


class CpaW2t(Validator):

    def __init__(self):
        super().__init__('cpa-witness2test')
        self.executable = None  # executable will compile CPAchecker when called, so only do this if we really validate

    def _get_cmd(self, program_file, witness_file):
        if not self.executable:
            self.executable = self.tool.executable()
        return [self.executable] + \
               utils.get_cpachecker_options(witness_file) +\
               ['-witness2test', program_file]


class FShellW2t(Validator):

    def __init__(self):
        super().__init__('witness2test')
        self.executable = self.tool.executable()
        self.repo = os.path.dirname(os.path.abspath(self.executable))

    def _get_cmd(self, program_file, witness_file):
        machine_model = utils.get_machine_model(witness_file)
        machine_model = machine_model.compile_parameter

        return [
            self.executable, '--propertyfile', utils.spec_file,
            '--graphml-witness', witness_file, machine_model, program_file
        ]

    def validate(self, program_file, witness_file):
        """Overwrites Validator.validate(...)."""
        # FShell-w2t only works if it is run from its repository. Because of this,
        # we always have to change directories, first.
        old_dir = os.path.abspath('.')
        os.chdir(self.repo)
        result = super().validate(program_file, witness_file)
        os.chdir(old_dir)  # And we change directories back to the original one
        return result

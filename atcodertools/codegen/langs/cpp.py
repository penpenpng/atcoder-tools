from typing import Dict, Any

from atcodertools.codegen.code_style_config import CodeStyleConfig
from atcodertools.constprediction.models.problem_constant_set import ProblemConstantSet
from atcodertools.fmtprediction.models.format import Pattern, SingularPattern, ParallelPattern, TwoDimensionalPattern
from atcodertools.fmtprediction.models.type import Type
from atcodertools.fmtprediction.models.format_prediction_result import FormatPredictionResult
from atcodertools.fmtprediction.models.variable import Variable


def _loop_header(var: Variable, for_second_index: bool):
    if for_second_index:
        index = var.second_index
        loop_var = "j"
    else:
        index = var.first_index
        loop_var = "i"

    return "for(int {loop_var} = 0 ; {loop_var} < {length} ; {loop_var}++){{".format(
        loop_var=loop_var,
        length=index.get_length()
    )


class CppCodeGenerator:

    def __init__(self, prediction_result: FormatPredictionResult,
                 config: CodeStyleConfig):
        self._prediction_result = prediction_result
        self._config = config

    def generate_parameters(self) -> Dict[str, Any]:
        return dict(formal_arguments=self._formal_arguments(),
                    actual_arguments=self._actual_arguments(),
                    input_part=self._input_part())

    def _input_part(self):
        lines = []
        for pattern in self._prediction_result.format.sequence:
            lines += self._render_pattern(pattern)
        return "\n{indent}".format(indent=self._indent(1)).join(lines)

    def _convert_type(self, type_: Type) -> str:
        if type_ == Type.float:
            return "long double"
        elif type_ == Type.int:
            return "long long"
        elif type_ == Type.str:
            return "string"
        else:
            raise NotImplementedError

    def _get_declaration_type(self, var: Variable):
        if var.dim_num() == 0:
            template = "{type}"
        elif var.dim_num() == 1:
            template = "vector<{type}>"
        elif var.dim_num() == 2:
            template = "vector<vector<{type}>>"
        else:
            raise NotImplementedError
        return template.format(type=self._convert_type(var.type))

    def _actual_arguments(self) -> str:
        """
            :return the string form of actual arguments e.g. "N, K, a"
        """
        return ", ".join([v.name for v in self._prediction_result.format.all_vars()])

    def _formal_arguments(self):
        """
            :return the string form of formal arguments e.g. "int N, int K, vector<int> a"
        """
        return ", ".join([
            "{decl_type} {name}".format(
                decl_type=self._get_declaration_type(v),
                name=v.name)
            for v in self._prediction_result.format.all_vars()
        ])

    def _generate_declaration(self, var: Variable):
        """
        :return: Create declaration part E.g. array[1..n] → vector<int> array = vector<int>(n-1+1);
        """
        if var.dim_num() == 0:
            constructor = ""
        elif var.dim_num() == 1:
            constructor = "({size})".format(
                size=var.first_index.get_length())
        elif var.dim_num() == 2:
            constructor = "({row_size}, vector<{type}>({col_size}))".format(
                type=self._convert_type(var.type),
                row_size=var.first_index.get_length(),
                col_size=var.second_index.get_length()
            )
        else:
            raise NotImplementedError

        line = "{decl_type} {name}{constructor};".format(
            name=var.name,
            decl_type=self._get_declaration_type(var),
            constructor=constructor
        )
        return line

    def _input_code_for_var(self, var: Variable) -> str:
        name = self._get_var_name(var)
        if var.type == Type.float:
            return 'scanf("%Lf",&{name});'.format(name=name)
        elif var.type == Type.int:
            return 'scanf("%lld",&{name});'.format(name=name)
        elif var.type == Type.str:
            return 'cin >> {name};'.format(name=name)
        else:
            raise NotImplementedError

    @staticmethod
    def _get_var_name(var: Variable):
        name = var.name
        if var.dim_num() >= 1:
            name += "[i]"
        if var.dim_num() >= 2:
            name += "[j]"
        return name

    def _render_pattern(self, pattern: Pattern):
        lines = []
        for var in pattern.all_vars():
            lines.append(self._generate_declaration(var))

        representative_var = pattern.all_vars()[0]
        if isinstance(pattern, SingularPattern):
            lines.append(self._input_code_for_var(representative_var))
        elif isinstance(pattern, ParallelPattern):
            lines.append(_loop_header(representative_var, False))
            for var in pattern.all_vars():
                lines.append("{indent}{line}".format(indent=self._indent(1),
                                                     line=self._input_code_for_var(var)))
            lines.append("}")
        elif isinstance(pattern, TwoDimensionalPattern):
            lines.append(_loop_header(representative_var, False))
            lines.append(
                "{indent}{line}".format(indent=self._indent(1), line=_loop_header(representative_var, True)))
            for var in pattern.all_vars():
                lines.append("{indent}{line}".format(indent=self._indent(2),
                                                     line=self._input_code_for_var(var)))
            lines.append("{indent}}}".format(indent=self._indent(1)))
            lines.append("}")
        else:
            raise NotImplementedError

        return lines

    def _indent(self, depth):
        return self._config.indent(depth)


class NoPredictionResultGiven(Exception):
    pass


def generate_template_parameters(prediction_result: FormatPredictionResult,
                                 constants: ProblemConstantSet,
                                 config: CodeStyleConfig) -> Dict[str, Any]:
    code_parameters = CppCodeGenerator(prediction_result, config).generate_parameters()

    return {
        **code_parameters,
        "mod": constants.mod,
        "yes_str": constants.yes_str,
        "no_str": constants.no_str,
    }
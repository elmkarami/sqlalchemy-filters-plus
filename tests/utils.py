def compares_expressions(exp1, exp2) -> bool:
    def compile_exp(exp):
        return exp.compile(compile_kwargs={"literal_binds": True})

    return str(compile_exp(exp1)) == str(compile_exp(exp2))

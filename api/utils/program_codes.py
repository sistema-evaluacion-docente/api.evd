"""
The academic program a course code belongs to.

UFPS course codes are seven digits ('1155304') whose first three are the
``COD_CARRERA`` of the academic registry — exactly what ``programs.code``
stores, leading zero included. That prefix is the only link between an
asignatura and its carrera: the schema has no foreign key, and it needs none,
since the code carries the answer.

It is what lets an improvement plan say the truth about a teacher who lectures
across several careers: the same 'INTRODUCCION A LA VIDA UNIV' is '1160103' for
Ingeniería Electrónica and '1210108' for Administración de Empresas, no matter
which department the teacher belongs to.
"""

PROGRAM_CODE_LENGTH = 3


def program_code_of(course_code: str | None) -> str | None:
    """The COD_CARRERA a course code carries: '1155304' -> '115'.

    None when there is nothing to read: a row typed by hand with no code, or a
    code that doesn't start with the digits a registry code is made of. The
    caller then keeps whatever program name it already had.
    """

    if not course_code:
        return None

    prefix = course_code.strip()[:PROGRAM_CODE_LENGTH]

    if len(prefix) < PROGRAM_CODE_LENGTH or not prefix.isdigit():
        return None

    return prefix

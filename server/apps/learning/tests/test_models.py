"""Unicidad del catálogo y de los intentos. Sin API ni pantalla."""

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.learning.catalog import CONCEPTS
from apps.learning.models import (
    Challenge,
    ChallengeAttempt,
    ChallengeTestCase,
    Concept,
    ConceptMastery,
    Hint,
    HintUsage,
    LearningPath,
    LearningUnit,
    Prediction,
    Reflection,
    WorkspaceSnapshot,
)


def _user(email: str) -> User:
    return User.objects.create_user(email=email, password="Clave-segura-1")


def _challenge(name: str = "Ruta de prueba", title: str = "Total") -> Challenge:
    concept = Concept.objects.get(key="variable")
    path = LearningPath.objects.create(name=name, description="Ruta inicial", position=50)
    unit = LearningUnit.objects.create(
        path=path,
        title="Variables",
        concept=concept,
        position=1,
    )
    return Challenge.objects.create(
        unit=unit,
        title=title,
        prompt="Calcula el total.",
        activity_type=Challenge.BUILD,
        difficulty=1,
        allowed_blocks=["variable", "assign"],
        restrictions={"lock_build": True},
        position=1,
    )


def test_el_catalogo_de_conceptos_queda_cargado(db):
    stored = set(Concept.objects.values_list("key", "name"))
    assert stored == set(CONCEPTS)
    assert str(Concept.objects.get(key="while")) == "Ciclo mientras"


def test_el_nombre_y_la_posicion_de_la_ruta_son_unicos(db):
    path = LearningPath.objects.create(name="Ruta alfa", position=40)
    assert str(path) == "Ruta alfa"
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LearningPath.objects.create(name="Ruta alfa", position=41)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LearningPath.objects.create(name="Ruta beta", position=40)


def test_la_posicion_de_la_unidad_es_unica_dentro_de_la_ruta(db):
    concept = Concept.objects.get(key="io")
    path = LearningPath.objects.create(name="Ruta de unidades", position=42)
    first = LearningUnit.objects.create(path=path, title="Entrada", concept=concept, position=1)
    later = LearningUnit.objects.create(
        path=path,
        title="Salida",
        concept=concept,
        position=2,
        prerequisite=first,
    )
    assert later.prerequisite_id == first.id
    assert str(first) == "Entrada"
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LearningUnit.objects.create(path=path, title="Repetida", concept=concept, position=1)


def test_cada_alumno_conserva_su_propio_intento(db):
    challenge = _challenge()
    ana = _user("ana-lab@ejemplo.test")
    luis = _user("luis-lab@ejemplo.test")
    case = ChallengeTestCase.objects.create(
        challenge=challenge,
        name="normal",
        inputs=["2", "3"],
        expected_output="5",
        kind=ChallengeTestCase.NORMAL,
        position=1,
    )
    hint = Hint.objects.create(challenge=challenge, level=1, body="Revisa los datos.", position=1)
    ana_attempt = ChallengeAttempt.objects.create(challenge=challenge, user=ana)
    luis_attempt = ChallengeAttempt.objects.create(challenge=challenge, user=luis)
    snapshot = WorkspaceSnapshot.objects.create(attempt=ana_attempt, blockly_json={"blocks": {}})
    usage = HintUsage.objects.create(attempt=ana_attempt, hint=hint)
    prediction = Prediction.objects.create(
        attempt=ana_attempt,
        prompt_key="total",
        expected="5",
        answer="5",
        is_correct=True,
    )
    reflection = Reflection.objects.create(attempt=ana_attempt, body="Suma precio y cantidad.")
    mastery = ConceptMastery.objects.create(user=ana, concept_id="variable", level=1)

    assert list(ana.learning_attempts.values_list("id", flat=True)) == [ana_attempt.id]
    assert luis_attempt.user_id == luis.id
    assert not ana.learning_attempts.filter(pk=luis_attempt.id).exists()
    assert snapshot.attempt_id == ana_attempt.id
    assert usage.hint_id == hint.id
    assert str(usage) == str(hint.id)
    assert prediction.is_correct is True
    assert reflection.attempt_id == ana_attempt.id
    assert mastery.concept_id == "variable"
    assert str(challenge) == "Total"
    assert str(case) == "normal"
    assert str(hint).startswith("1:")
    assert str(ana_attempt).startswith("open ")
    assert str(snapshot) == "foto 1"
    assert str(prediction) == "total"
    assert str(reflection) == "Suma precio y cantidad."
    assert str(mastery) == "variable 1"

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Reflection.objects.create(attempt=ana_attempt, body="Otra explicación.")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ConceptMastery.objects.create(user=ana, concept_id="variable", level=2)


def test_un_reto_rechaza_tipo_dificultad_o_pista_fuera_de_rango(db):
    challenge = _challenge()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Challenge.objects.create(
                unit=challenge.unit,
                title="Raro",
                prompt="No aplica.",
                activity_type="dibujo",
                difficulty=1,
                position=2,
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Challenge.objects.create(
                unit=challenge.unit,
                title="Difícil de más",
                prompt="No aplica.",
                activity_type=Challenge.CLASSIFY,
                difficulty=6,
                position=3,
            )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Hint.objects.create(challenge=challenge, level=0, body="No existe.", position=1)

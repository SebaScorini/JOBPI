from app.schemas.job import AIResponseLanguage


def normalize_language(language: str | None) -> AIResponseLanguage:
    if isinstance(language, str) and language.strip().lower() == "spanish":
        return "spanish"
    return "english"


def language_instruction(language: AIResponseLanguage) -> str:
    if language == "spanish":
        return (
            "Respond entirely in Spanish. Keep names of technologies as-is, "
            "but write explanations, summaries, bullet points, and recommendations in Spanish."
        )
    return (
        "Respond entirely in English. Keep names of technologies as-is, "
        "and write explanations, summaries, bullet points, and recommendations in English."
    )


def localized_match_prefix(language: AIResponseLanguage) -> str:
    if language == "spanish":
        return "Fortalezas principales"
    return "Key strengths"


def localized_match_fallback(language: AIResponseLanguage) -> str:
    if language == "spanish":
        return "Este CV se alinea con los requisitos mas relevantes del puesto."
    return "This CV aligns with the strongest matching requirements."


def localized_add_evidence(language: AIResponseLanguage, keyword: str) -> str:
    if language == "spanish":
        return f"Agrega evidencia clara de {keyword}"
    return f"Add clear evidence of {keyword}"


def localized_add_metric(language: AIResponseLanguage, topic: str) -> str:
    if language == "spanish":
        return f"Convierte {topic} en un logro con metricas, alcance e impacto concreto"
    return f"Turn {topic} into an achievement with metrics, scope, and concrete impact"


def localized_add_project_example(language: AIResponseLanguage, topic: str) -> str:
    if language == "spanish":
        return f"Agrega un proyecto o bullet especifico que demuestre {topic}"
    return f"Add a specific project or bullet that proves {topic}"


def localized_surface_keyword(language: AIResponseLanguage, keyword: str) -> str:
    if language == "spanish":
        return f"Incluye {keyword} en el resumen profesional y en una experiencia relevante"
    return f"Surface {keyword} in the professional summary and one relevant experience entry"


def localized_tailor_summary(language: AIResponseLanguage, strength: str) -> str:
    if language == "spanish":
        return f"Abre el CV destacando {strength} como argumento principal de encaje"
    return f"Open the CV by positioning {strength} as a primary fit signal"


def localized_add_exact_keyword_match(language: AIResponseLanguage, keyword: str) -> str:
    if language == "spanish":
        return f"Usa la formulacion exacta de {keyword} en skills, resumen o experiencia si realmente aplica"
    return f"Use the exact wording of {keyword} in skills, summary, or experience if it truthfully applies"


def localized_quantify_strength(language: AIResponseLanguage, strength: str) -> str:
    if language == "spanish":
        return f"Cuantifica {strength} con resultados, escala o contexto de negocio"
    return f"Quantify {strength} with results, scale, or business context"


def localized_move_strength_earlier(language: AIResponseLanguage, strength: str) -> str:
    if language == "spanish":
        return f"Mueve {strength} mas arriba para que aparezca antes en el CV"
    return f"Move {strength} higher so it appears earlier in the CV"


def localized_reorder_strength(language: AIResponseLanguage, strength: str) -> str:
    if language == "spanish":
        return f"Mueve {strength} al resumen principal o a la primera seccion de experiencia"
    return f"Move {strength} into the top summary or first experience section"


def localized_reorder_keyword(language: AIResponseLanguage, keyword: str) -> str:
    if language == "spanish":
        return f"Coloca la experiencia o proyectos que mencionan {keyword} antes del contenido menos relevante"
    return f"Place experience or projects that mention {keyword} before less relevant content"


def localized_comparison_explanation(
    language: AIResponseLanguage,
    winner_label: str,
    loser_label: str,
    winner_strength: str,
    loser_gap: str,
) -> str:
    if language == "spanish":
        return (
            f"{winner_label} es el CV con mejor encaje porque muestra {winner_strength.lower()} "
            f"y obtiene una mejor alineacion con los requisitos del puesto que {loser_label}, "
            f"que presenta mas brechas en {loser_gap.lower()}."
        )
    return (
        f"{winner_label} is the stronger fit because it shows {winner_strength.lower()} "
        f"and scores better against the job requirements than {loser_label}, "
        f"which shows more gaps around {loser_gap.lower()}."
    )

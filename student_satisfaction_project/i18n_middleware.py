from __future__ import annotations

from .i18n_final_artifact_middleware import (
    FinalEnglishArtifactWarningMiddleware,
)
from .i18n_residual_middleware import (
    EnglishResidualTranslationMiddleware,
)
from .i18n_statistics_lastmile import (
    StatisticsEnglishLastMileMiddleware,
)
from .i18n_training_lastmile import (
    TrainingEnglishLastMileMiddleware,
)


class UnifiedEnglishI18nMiddleware:
    """
    Single active i18n response pipeline.

    The legacy translation engines remain separate and directly tested,
    but Django now registers only this orchestrator.

    Response transformation order intentionally matches the pre-V15B
    effective order:
        residual -> training -> artifact warning -> statistics
    """

    def __init__(self, get_response):
        chain = get_response
        chain = EnglishResidualTranslationMiddleware(chain)
        chain = TrainingEnglishLastMileMiddleware(chain)
        chain = FinalEnglishArtifactWarningMiddleware(chain)
        chain = StatisticsEnglishLastMileMiddleware(chain)

        self._chain = chain

    def __call__(self, request):
        return self._chain(request)
